"""Safely generate opening problems without introducing consistency conflicts.

The script builds the current consistency index first, creates candidates from
data/openings.json, rejects any candidate that would contradict an existing
position, and only then plans or writes files.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from generate_opening_problems import (
    FolderState,
    GeneratedProblem,
    IgnoredOpening,
    Opening,
    build_problem,
    get_folder_state,
    load_chess_module,
    load_folder_map,
    load_openings,
    parse_bool,
    parse_opening_moves,
    problem_content,
    problem_file_numbers,
    resolve_folder,
    side_root,
    sort_for_generation,
)
from problem_consistency_lib import (
    CandidateConflict,
    CandidateProblem,
    ConsistencyIndex,
    ProblemMove,
    ProblemParseError,
    build_consistency_index,
    check_candidate_problem,
    iter_problem_files,
    parse_move_line,
    parse_problem_file,
    problem_sequence,
    register_candidate_problem,
    relative,
    rotate_board_180,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class RejectedConflict:
    opening: Opening
    folder: str
    conflict: CandidateConflict


@dataclass(frozen=True)
class CreatedPlan:
    problem: GeneratedProblem
    moves: list[ProblemMove]


DuplicateKey = tuple[tuple[tuple[int, ...], ...], tuple[str, ...]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely generate Echiquier opening problems from data/openings.json.")
    parser.add_argument("--side", choices=["white", "black"], required=True)
    parser.add_argument(
        "--mode",
        choices=["catalogue", "repertoire"],
        default="catalogue",
        help=(
            "catalogue: cohérence par dossier (defaut, autorise plusieurs ouvertures depuis la "
            "meme position si elles vivent dans des dossiers differents). "
            "repertoire: cohérence globale stricte sur toute la couleur."
        ),
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--plies",
        type=int,
        choices=[6, 8, 10, 12],
        help="nombre exact de demi-coups a ecrire dans chaque fichier genere",
    )
    parser.add_argument("--min-plies", type=int, default=2)
    parser.add_argument("--max-plies", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", nargs="?", const=True, default=False, type=parse_bool)
    parser.add_argument("--skip-existing", nargs="?", const=True, default=True, type=parse_bool)
    parser.add_argument("--prefer-uncovered", nargs="?", const=True, default=True, type=parse_bool)
    return parser


def scope_for_mode(mode: str) -> str:
    return "global" if mode == "repertoire" else "folder"


def validate_args(args: argparse.Namespace) -> None:
    if args.limit <= 0:
        raise RuntimeError("--limit doit etre superieur a 0")
    if args.plies is not None and args.plies < 1:
        raise RuntimeError("--plies doit etre superieur ou egal a 1")
    if args.min_plies < 1:
        raise RuntimeError("--min-plies doit etre superieur ou egal a 1")
    if args.max_plies < args.min_plies:
        raise RuntimeError("--max-plies doit etre superieur ou egal a --min-plies")


def numeric_count(folder: Path) -> int:
    return len(problem_file_numbers(folder))


def order_openings(openings: list[Opening], folder_map: dict[str, str], side: str, prefer_uncovered: bool) -> list[Opening]:
    if not prefer_uncovered:
        return sort_for_generation(openings, folder_map)

    def key(opening: Opening) -> tuple[int, int, str, str, str, str]:
        folder = resolve_folder(opening, folder_map)
        target_dir = side_root(side) / folder
        exists_rank = 1 if target_dir.exists() else 0
        return (
            exists_rank,
            numeric_count(target_dir),
            opening.eco,
            opening.name,
            opening.moves_pgn or "",
            opening.id,
        )

    return sorted(openings, key=key)


def parse_generated_moves(problem: GeneratedProblem) -> list[ProblemMove]:
    moves: list[ProblemMove] = []
    for index, line in enumerate(problem.move_lines, start=9):
        moves.append(parse_move_line(line, index))
    return moves


def required_source_plies(side: str, generated_plies: int) -> int:
    return generated_plies + 1 if side == "black" else generated_plies


def select_source_moves(source_moves: list[object], side: str, plies: int | None) -> list[object]:
    if plies is None:
        return source_moves
    return source_moves[: required_source_plies(side, plies)]


def normalized_board_for_candidate(problem: GeneratedProblem, side: str) -> list[list[int]]:
    rows = [list(row) for row in problem.board_rows]
    return rotate_board_180(rows) if side == "black" else rows


def candidate_from_problem(problem: GeneratedProblem, side: str, planned_file: Path, moves: list[ProblemMove]) -> CandidateProblem:
    return CandidateProblem(
        side=side,
        folder=problem.folder,
        board=normalized_board_for_candidate(problem, side),
        moves=moves,
        source_name=f"{problem.opening.eco} {problem.opening.name}",
        planned_file=relative(planned_file),
    )


def board_key(board: list[list[int]] | tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(value) for value in row) for row in board)


def duplicate_key(board: list[list[int]] | tuple[tuple[int, ...], ...], moves: list[ProblemMove]) -> DuplicateKey:
    return (board_key(board), problem_sequence(moves))


def build_existing_duplicate_keys(side: str) -> dict[str, set[DuplicateKey]]:
    keys: dict[str, set[DuplicateKey]] = {}
    base = side_root(side)
    if not base.exists():
        return keys

    for folder in sorted(base.iterdir(), key=lambda path: path.name.lower()):
        if not folder.is_dir():
            continue
        if folder.name.startswith(".") or folder.name == "__pycache__":
            continue
        if side == "white" and folder.name in {"black", "_quarantine"}:
            continue

        for path in iter_problem_files(folder):
            try:
                problem = parse_problem_file(path, folder.name, side)  # normalise les plateaux noirs comme l'index
            except ProblemParseError:
                continue
            keys.setdefault(folder.name, set()).add(duplicate_key(problem.board, problem.moves))

    return keys


def count_numeric_after_write(folder: Path) -> int:
    return sum(1 for path in folder.glob("*.txt") if path.name != "Format.txt" and path.stem.isdigit())


def write_format_count(folder: Path) -> None:
    count = count_numeric_after_write(folder)
    format_path = folder / "Format.txt"
    if format_path.exists():
        lines = format_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            lines[0] = str(count)
        else:
            lines = [str(count)]
        format_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        format_path.write_text(f"{count}\n", encoding="utf-8")


def write_created(plans: list[CreatedPlan], states: dict[Path, FolderState], overwrite: bool) -> list[Path]:
    written: list[Path] = []
    for plan in plans:
        problem = plan.problem
        target_file = problem.target_file
        if target_file.exists():
            raise RuntimeError(f"refus d'ecraser un fichier existant: {relative(target_file)}")
        if overwrite:
            raise RuntimeError("--overwrite n'est pas autorise par le mode safe")
        problem.target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(problem_content(problem), encoding="utf-8")
        written.append(target_file)

    for folder, state in states.items():
        if state.planned_numbers:
            folder.mkdir(parents=True, exist_ok=True)
            write_format_count(folder)

    return written


def plan_safe_generation(args: argparse.Namespace) -> tuple[
    list[CreatedPlan],
    list[IgnoredOpening],
    list[IgnoredOpening],
    list[RejectedConflict],
    int,
    int,
    dict[Path, FolderState],
    ConsistencyIndex,
    dict[str, set[DuplicateKey]],
]:
    return plan_safe_generation_with_state(args)


def plan_safe_generation_with_state(
    args: argparse.Namespace,
    states: dict[Path, FolderState] | None = None,
    index: ConsistencyIndex | None = None,
    duplicate_keys_by_folder: dict[str, set[DuplicateKey]] | None = None,
) -> tuple[
    list[CreatedPlan],
    list[IgnoredOpening],
    list[IgnoredOpening],
    list[RejectedConflict],
    int,
    int,
    dict[Path, FolderState],
    ConsistencyIndex,
    dict[str, set[DuplicateKey]],
]:
    chess = load_chess_module()
    openings = load_openings()
    folder_map = load_folder_map(args.side)
    ordered_openings = order_openings(openings, folder_map, args.side, bool(args.prefer_uncovered))
    scope = scope_for_mode(args.mode)
    if index is None:
        index, index_result = build_consistency_index(args.side, scope=scope)
    else:
        index_result = None
    if index_result is not None and (index_result.parse_errors or index_result.move_application_errors):
        print(
            "Attention: la base existante contient des erreurs de parsing/application; "
            "les candidats restent verifies sur l'index partiel.",
            file=sys.stderr,
        )

    if states is None:
        states = {}
    if duplicate_keys_by_folder is None:
        duplicate_keys_by_folder = build_existing_duplicate_keys(args.side)

    plans: list[CreatedPlan] = []
    duplicates: list[IgnoredOpening] = []
    parse_rejections: list[IgnoredOpening] = []
    conflict_rejections: list[RejectedConflict] = []
    too_short = 0
    candidates_analyzed = 0

    for opening in ordered_openings:
        if len(plans) >= args.limit:
            break

        try:
            source_moves = parse_opening_moves(chess, opening)
        except Exception as exc:
            parse_rejections.append(IgnoredOpening(opening.eco, opening.name, opening.label, str(exc)))
            continue

        candidates_analyzed += 1
        source_plies = len(source_moves)
        if args.plies is not None:
            required = required_source_plies(args.side, args.plies)
            if source_plies < required:
                too_short += 1
                continue
            selected_moves = select_source_moves(source_moves, args.side, args.plies)
        elif source_plies < args.min_plies or source_plies > args.max_plies:
            too_short += 1
            continue
        else:
            selected_moves = source_moves

        try:
            base_problem = build_problem(chess, opening, args.side, selected_moves)
            generated_moves = parse_generated_moves(base_problem)
        except Exception as exc:
            parse_rejections.append(IgnoredOpening(opening.eco, opening.name, opening.label, str(exc)))
            continue

        if args.plies is not None and base_problem.generated_plies != args.plies:
            parse_rejections.append(
                IgnoredOpening(
                    opening.eco,
                    opening.name,
                    opening.label,
                    f"{base_problem.generated_plies} demi-coups generes au lieu de {args.plies}",
                )
            )
            continue

        folder = resolve_folder(opening, folder_map)
        target_dir = side_root(args.side) / folder
        state = get_folder_state(target_dir, states)
        normalized_board = normalized_board_for_candidate(base_problem, args.side)
        exact_key = duplicate_key(normalized_board, generated_moves)

        if args.skip_existing and exact_key in duplicate_keys_by_folder.setdefault(folder, set()):
            duplicates.append(
                IgnoredOpening(
                    opening.eco,
                    opening.name,
                    opening.label,
                    f"doublon exact plateau+suite dans {folder}",
                )
            )
            continue

        file_number = state.next_number()
        problem = GeneratedProblem(
            opening=base_problem.opening,
            folder=folder,
            target_dir=target_dir,
            file_number=file_number,
            move_lines=base_problem.move_lines,
            board_rows=base_problem.board_rows,
            source_plies=base_problem.source_plies,
            generated_plies=base_problem.generated_plies,
            initial_position_note=base_problem.initial_position_note,
        )
        candidate = candidate_from_problem(problem, args.side, problem.target_file, generated_moves)
        try:
            conflicts = check_candidate_problem(candidate, index)
        except Exception as exc:
            parse_rejections.append(IgnoredOpening(opening.eco, opening.name, opening.label, str(exc)))
            continue

        if conflicts:
            conflict_rejections.append(RejectedConflict(opening, folder, conflicts[0]))
            continue

        state.reserve(file_number, problem.sequence_key)
        duplicate_keys_by_folder.setdefault(folder, set()).add(exact_key)
        register_candidate_problem(candidate, index)
        plans.append(CreatedPlan(problem, generated_moves))

    return (
        plans,
        duplicates,
        parse_rejections,
        conflict_rejections,
        too_short,
        candidates_analyzed,
        states,
        index,
        duplicate_keys_by_folder,
    )


def print_creation_details(plans: list[CreatedPlan], dry_run: bool) -> None:
    print()
    print("Detail des creations :")
    if not plans:
        print("- aucun")
        return
    action = "prevu" if dry_run else "ecrit"
    for plan in plans:
        problem = plan.problem
        print(f"- {problem.opening.eco} {problem.opening.name}")
        print(f"  label : {problem.opening.label}")
        print(f"  dossier : {problem.folder}")
        print(f"  fichier {action} : {relative(problem.target_file)}")
        print(f"  coups : {problem.generated_plies}")


def print_conflict_details(conflicts: list[RejectedConflict], max_items: int = 50) -> None:
    print()
    print("Detail des conflits :")
    if not conflicts:
        print("- aucun")
        return
    for item in conflicts[:max_items]:
        conflict = item.conflict
        print(f"- {item.opening.eco} {item.opening.name} [{item.opening.label}]")
        print(f"  dossier : {item.folder}")
        print(f"  raison : {conflict.reason}")
        print(f"  coup candidat : {conflict.candidate.move}")
        print(f"  coup existant attendu : {conflict.existing.move}")
        print(f"  fichier existant : {conflict.existing.file}")
        print(f"  index du coup existant : {conflict.existing.move_index}")
        print(f"  position : {conflict.position_key}")
    if len(conflicts) > max_items:
        print(f"- ... {len(conflicts) - max_items} conflit(s) supplementaire(s)")


def print_ignored(title: str, items: list[IgnoredOpening]) -> None:
    print()
    print(title)
    if not items:
        print("- aucun")
        return
    for item in items[:50]:
        print(f"- {item.eco} {item.name} [{item.label}]: {item.reason}")
    if len(items) > 50:
        print(f"- ... {len(items) - 50} entree(s) supplementaire(s)")


def print_report(
    args: argparse.Namespace,
    openings_read: int,
    candidates_analyzed: int,
    plans: list[CreatedPlan],
    written: list[Path],
    duplicates: list[IgnoredOpening],
    parse_rejections: list[IgnoredOpening],
    conflict_rejections: list[RejectedConflict],
    too_short: int,
    states: dict[Path, FolderState],
) -> None:
    created_dirs = sorted(path for path, state in states.items() if state.planned_numbers and not state.existed_before)

    print("# Generation safe de problemes")
    print()
    print(f"Side : {args.side}")
    print(f"Mode catalogue/repertoire : {args.mode}")
    print(f"Scope de conflit utilise : {scope_for_mode(args.mode)}")
    print(f"Demi-coups exacts : {args.plies if args.plies is not None else 'filtre min/max'}")
    print(f"Mode ecriture : {'dry-run' if args.dry_run else 'ecriture reelle'}")
    print(f"Lignes Lichess lues : {openings_read}")
    print(f"Candidats analyses : {candidates_analyzed}")
    print(f"Candidats acceptes : {len(plans)}")
    print(f"Candidats refuses pour ligne trop courte : {too_short}")
    print(f"Candidats refuses pour conflit : {len(conflict_rejections)}")
    print(f"Candidats refuses pour doublon : {len(duplicates)}")
    print(f"Candidats refuses pour parsing : {len(parse_rejections)}")
    print(f"Fichiers ecrits : {len(written)}")
    print(f"Dossiers {'a creer' if args.dry_run else 'crees'} : {len(created_dirs)}")
    if created_dirs:
        for path in created_dirs:
            print(f"- {relative(path)}")
    print_creation_details(plans, bool(args.dry_run))
    print_conflict_details(conflict_rejections)
    print_ignored("Doublons ignores", duplicates)
    print_ignored("Refus parsing", parse_rejections)
    print()
    print("Commandes suivantes proposees :")
    print(f"python tools/check_problem_consistency.py --side {args.side} --report data/{args.side}_consistency_report_after_generation.json")
    print("python scripts/export_problems.py")
    print("npm run build")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
        openings_read = len(load_openings())
        (
            plans,
            duplicates,
            parse_rejections,
            conflict_rejections,
            too_short,
            candidates_analyzed,
            states,
            _index,
            _duplicate_keys_by_folder,
        ) = plan_safe_generation(args)
        written: list[Path] = []
        if not args.dry_run:
            written = write_created(plans, states, bool(args.overwrite))
        print_report(
            args=args,
            openings_read=openings_read,
            candidates_analyzed=candidates_analyzed,
            plans=plans,
            written=written,
            duplicates=duplicates,
            parse_rejections=parse_rejections,
            conflict_rejections=conflict_rejections,
            too_short=too_short,
            states=states,
        )
    except RuntimeError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
