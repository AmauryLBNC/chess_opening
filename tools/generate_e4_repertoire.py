"""Generate a structured white 1.e4 repertoire in four fixed folders.

The generator reads data/openings.json, keeps only lines starting with e2e4,
chooses one white reply per white-to-move position, allows many black replies,
then exports exact-length historical problem files.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generate_opening_problems import (
    GeneratedProblem,
    Opening,
    build_problem,
    load_chess_module,
    load_openings,
    problem_content,
    side_root,
)
from problem_consistency_lib import (
    MoveApplicationError,
    ProblemMove,
    ProblemParseError,
    apply_move,
    clone_board,
    iter_problem_files,
    move_to_key,
    parse_move_line,
    parse_problem_file,
    piece_color,
    position_key,
    problem_sequence,
    relative,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


TARGET_FIRST_UCI = "e2e4"


@dataclass(frozen=True)
class ParsedLine:
    opening: Opening
    moves: tuple[Any, ...]

    @property
    def uci(self) -> tuple[str, ...]:
        return tuple(move.uci() for move in self.moves)


@dataclass(frozen=True)
class CandidateSource:
    opening: Opening
    moves: tuple[Any, ...]
    uci: tuple[str, ...]


@dataclass(frozen=True)
class PlannedProblem:
    problem: GeneratedProblem
    moves: tuple[ProblemMove, ...]
    uci: tuple[str, ...]


@dataclass
class RepertoireRegistry:
    white_moves_by_position: dict[str, str] = field(default_factory=dict)
    black_moves_by_position: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def check(self, board: list[list[int]], moves: tuple[ProblemMove, ...]) -> tuple[bool, str | None]:
        trial = clone_board(board)
        for index, move in enumerate(moves, start=1):
            turn = piece_color(move.piece)
            key = position_key(trial, turn)
            move_key = move_to_key(move)
            if turn == "white":
                existing = self.white_moves_by_position.get(key)
                if existing is not None and existing != move_key:
                    return False, f"white conflict at move {index}: {existing} vs {move_key}"
            try:
                trial = apply_move(trial, move)
            except MoveApplicationError as exc:
                return False, str(exc)
        return True, None

    def register(self, board: list[list[int]], moves: tuple[ProblemMove, ...]) -> None:
        trial = clone_board(board)
        for move in moves:
            turn = piece_color(move.piece)
            key = position_key(trial, turn)
            move_key = move_to_key(move)
            if turn == "white":
                self.white_moves_by_position.setdefault(key, move_key)
            elif turn == "black":
                self.black_moves_by_position[key].add(move_key)
            trial = apply_move(trial, move)


@dataclass
class PlanResult:
    total_openings: int
    invalid_lines: int
    e4_lines: int
    too_short_by_plies: dict[int, int]
    white_nodes_analyzed: int
    chosen_white_responses: int
    black_branches_kept: int
    duplicates_refused: int
    white_conflicts_refused: int
    parse_refused: int
    planned_by_plies: dict[int, list[PlannedProblem]]
    target_dirs: dict[int, Path]
    existing_dirs: set[Path]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a fixed-folder white 1.e4 repertoire.")
    parser.add_argument("--side", choices=["white"], required=True)
    parser.add_argument("--plan", required=True, type=parse_plan, help='example: "6:250,8:250,10:250,12:250"')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-partial", action="store_true", help="allow real writes even if the requested plan is incomplete")
    parser.add_argument(
        "--max-black-branches-per-position",
        type=int,
        default=0,
        help="0 means unlimited; otherwise keep the most frequent black replies per position",
    )
    return parser


def parse_plan(value: str) -> dict[int, int]:
    plan: dict[int, int] = {}
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if ":" not in part:
            raise argparse.ArgumentTypeError(f"plan entry must be plies:count, got {part!r}")
        raw_plies, raw_count = part.split(":", 1)
        try:
            plies = int(raw_plies)
            count = int(raw_count)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"non numeric plan entry: {part!r}") from exc
        if plies not in {6, 8, 10, 12}:
            raise argparse.ArgumentTypeError("supported plies are 6, 8, 10, 12")
        if count <= 0:
            raise argparse.ArgumentTypeError("plan counts must be positive")
        if plies in plan:
            raise argparse.ArgumentTypeError(f"duplicate plies in plan: {plies}")
        plan[plies] = count
    if not plan:
        raise argparse.ArgumentTypeError("plan must not be empty")
    return plan


def target_folder_name(plies: int) -> str:
    return f"repertoire_e4_{plies}_demicoups"


def parse_generated_moves(problem: GeneratedProblem) -> tuple[ProblemMove, ...]:
    return tuple(parse_move_line(line, index) for index, line in enumerate(problem.move_lines, start=9))


def board_rows_to_list(problem: GeneratedProblem) -> list[list[int]]:
    return [list(row) for row in problem.board_rows]


def count_numeric_after_write(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for path in folder.glob("*.txt") if path.name != "Format.txt" and path.stem.isdigit())


def next_number(folder: Path, planned_count: int) -> int:
    numbers = [int(path.stem) for path in folder.glob("*.txt") if path.name != "Format.txt" and path.stem.isdigit()]
    base = max(numbers) if numbers else 0
    return base + planned_count + 1


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


def collect_e4_lines(chess: Any, openings: list[Opening]) -> tuple[list[ParsedLine], int]:
    parsed: list[ParsedLine] = []
    invalid = 0
    for opening in openings:
        try:
            from generate_opening_problems import parse_opening_moves

            moves = tuple(parse_opening_moves(chess, opening))
        except Exception:
            invalid += 1
            continue
        if moves and moves[0].uci() == TARGET_FIRST_UCI:
            parsed.append(ParsedLine(opening, moves))
    return parsed, invalid


def chess_position_key(chess: Any, board: Any) -> str:
    from generate_opening_problems import board_to_project_rows

    rows = [list(row) for row in board_to_project_rows(chess, board)]
    turn = "white" if board.turn == chess.WHITE else "black"
    return position_key(rows, turn)


def choose_white_policy(chess: Any, lines: list[ParsedLine]) -> tuple[dict[str, str], int]:
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for line in lines:
        board = chess.Board()
        for move in line.moves:
            if board.turn == chess.WHITE:
                votes[chess_position_key(chess, board)][move.uci()] += 1
            board.push(move)

    policy: dict[str, str] = {}
    for key, counts in votes.items():
        policy[key] = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return policy, len(votes)


def black_move_allowed(
    key: str,
    move_uci: str,
    black_votes: dict[str, Counter[str]],
    max_black_branches_per_position: int,
) -> bool:
    if max_black_branches_per_position <= 0:
        return True
    ranked = sorted(black_votes[key].items(), key=lambda item: (-item[1], item[0]))
    allowed = {uci for uci, _count in ranked[:max_black_branches_per_position]}
    return move_uci in allowed


def collect_policy_candidates(
    chess: Any,
    lines: list[ParsedLine],
    policy: dict[str, str],
    requested_plies: set[int],
    max_black_branches_per_position: int,
) -> tuple[dict[int, list[CandidateSource]], dict[str, set[str]], dict[int, int]]:
    max_plies = max(requested_plies)
    candidates: dict[int, list[CandidateSource]] = {plies: [] for plies in requested_plies}
    black_votes: dict[str, Counter[str]] = defaultdict(Counter)
    for line in lines:
        board = chess.Board()
        for move in line.moves[:max_plies]:
            if board.turn == chess.BLACK:
                black_votes[chess_position_key(chess, board)][move.uci()] += 1
            board.push(move)

    black_branches: dict[str, set[str]] = defaultdict(set)
    too_short_by_plies = {
        plies: sum(1 for line in lines if len(line.moves) < plies)
        for plies in requested_plies
    }

    for line in lines:
        board = chess.Board()
        prefix: list[Any] = []
        for move in line.moves[:max_plies]:
            key = chess_position_key(chess, board)
            if board.turn == chess.WHITE:
                chosen = policy.get(key)
                if chosen is None or move.uci() != chosen:
                    break
            else:
                if not black_move_allowed(key, move.uci(), black_votes, max_black_branches_per_position):
                    break
                black_branches[key].add(move.uci())

            prefix.append(move)
            board.push(move)
            if len(prefix) in requested_plies:
                candidates[len(prefix)].append(
                    CandidateSource(
                        opening=line.opening,
                        moves=tuple(prefix),
                        uci=tuple(item.uci() for item in prefix),
                    )
                )

    return candidates, black_branches, too_short_by_plies


def balanced_order(candidates: list[CandidateSource]) -> list[CandidateSource]:
    buckets: dict[str, list[CandidateSource]] = defaultdict(list)
    for candidate in candidates:
        key = candidate.uci[1] if len(candidate.uci) > 1 else ""
        buckets[key].append(candidate)
    for key in buckets:
        buckets[key].sort(key=lambda candidate: candidate.uci)

    ordered: list[CandidateSource] = []
    keys = sorted(buckets)
    while True:
        progressed = False
        for key in keys:
            if buckets[key]:
                ordered.append(buckets[key].pop(0))
                progressed = True
        if not progressed:
            return ordered


def load_existing_folder_state(
    folder: Path,
    registry: RepertoireRegistry,
) -> set[tuple[str, ...]]:
    sequences: set[tuple[str, ...]] = set()
    if not folder.exists():
        return sequences
    for path in iter_problem_files(folder):
        try:
            problem = parse_problem_file(path, folder.name, "white")
        except ProblemParseError:
            continue
        moves = tuple(problem.moves)
        sequences.add(problem_sequence(list(moves)))
        ok, _reason = registry.check(problem.board, moves)
        if ok:
            registry.register(problem.board, moves)
    return sequences


def build_plan(args: argparse.Namespace) -> PlanResult:
    chess = load_chess_module()
    openings = load_openings()
    lines, invalid_lines = collect_e4_lines(chess, openings)
    requested_plies = set(args.plan)
    policy, white_nodes = choose_white_policy(chess, lines)
    candidates_by_plies, black_branches, too_short_by_plies = collect_policy_candidates(
        chess,
        lines,
        policy,
        requested_plies,
        args.max_black_branches_per_position,
    )

    target_dirs = {plies: side_root("white") / target_folder_name(plies) for plies in requested_plies}
    existing_dirs = {path for path in target_dirs.values() if path.exists()}
    planned_by_plies: dict[int, list[PlannedProblem]] = {plies: [] for plies in requested_plies}
    sequences_by_folder: dict[Path, set[tuple[str, ...]]] = {}
    registries_by_folder: dict[Path, RepertoireRegistry] = {}

    for folder in target_dirs.values():
        registry = RepertoireRegistry()
        registries_by_folder[folder] = registry
        sequences_by_folder[folder] = load_existing_folder_state(folder, registry)

    duplicates_refused = 0
    white_conflicts_refused = 0
    parse_refused = 0

    for plies in sorted(requested_plies):
        folder = target_dirs[plies]
        registry = registries_by_folder[folder]
        planned_count = 0
        for source in balanced_order(candidates_by_plies[plies]):
            if len(planned_by_plies[plies]) >= args.plan[plies]:
                break
            try:
                base = build_problem(chess, source.opening, "white", list(source.moves))
                moves = parse_generated_moves(base)
            except Exception:
                parse_refused += 1
                continue
            if base.generated_plies != plies or not source.uci or source.uci[0] != TARGET_FIRST_UCI:
                parse_refused += 1
                continue
            sequence = problem_sequence(list(moves))
            if sequence in sequences_by_folder[folder]:
                duplicates_refused += 1
                continue
            board = board_rows_to_list(base)
            ok, _reason = registry.check(board, moves)
            if not ok:
                white_conflicts_refused += 1
                continue
            file_number = next_number(folder, planned_count)
            planned_count += 1
            problem = GeneratedProblem(
                opening=base.opening,
                folder=folder.name,
                target_dir=folder,
                file_number=file_number,
                move_lines=base.move_lines,
                board_rows=base.board_rows,
                source_plies=base.source_plies,
                generated_plies=base.generated_plies,
                initial_position_note=base.initial_position_note,
            )
            sequences_by_folder[folder].add(sequence)
            registry.register(board, moves)
            planned_by_plies[plies].append(PlannedProblem(problem, moves, source.uci))

    return PlanResult(
        total_openings=len(openings),
        invalid_lines=invalid_lines,
        e4_lines=len(lines),
        too_short_by_plies=too_short_by_plies,
        white_nodes_analyzed=white_nodes,
        chosen_white_responses=len(policy),
        black_branches_kept=sum(len(moves) for moves in black_branches.values()),
        duplicates_refused=duplicates_refused,
        white_conflicts_refused=white_conflicts_refused,
        parse_refused=parse_refused,
        planned_by_plies=planned_by_plies,
        target_dirs=target_dirs,
        existing_dirs=existing_dirs,
    )


def write_plan(result: PlanResult) -> list[Path]:
    written: list[Path] = []
    for plies, plans in result.planned_by_plies.items():
        folder = result.target_dirs[plies]
        if not plans:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        for plan in plans:
            if plan.problem.target_file.exists():
                raise RuntimeError(f"refus d'ecraser {relative(plan.problem.target_file)}")
            plan.problem.target_file.write_text(problem_content(plan.problem), encoding="utf-8")
            written.append(plan.problem.target_file)
        write_format_count(folder)
    return written


def incomplete_lengths(args: argparse.Namespace, result: PlanResult) -> list[str]:
    missing: list[str] = []
    for plies, target in sorted(args.plan.items()):
        count = len(result.planned_by_plies[plies])
        if count < target:
            missing.append(f"{plies}: {count}/{target}")
    return missing


def print_report(args: argparse.Namespace, result: PlanResult, written: list[Path]) -> None:
    print("# Generation repertoire blanc 1.e4")
    print()
    print(f"Side : {args.side}")
    print(f"Mode : {'dry-run' if args.dry_run else 'ecriture reelle'}")
    print(f"Lignes Lichess lues : {result.total_openings}")
    print(f"Lignes commencant par e4 : {result.e4_lines}")
    print(f"Lignes invalides : {result.invalid_lines}")
    print(f"Lignes rejetees car trop courtes : {sum(result.too_short_by_plies.values())}")
    for plies in sorted(result.too_short_by_plies):
        print(f"- trop courtes pour {plies} demi-coups : {result.too_short_by_plies[plies]}")
    print(f"Noeuds blancs analyses : {result.white_nodes_analyzed}")
    print(f"Reponses blanches choisies : {result.chosen_white_responses}")
    print(f"Branches noires conservees : {result.black_branches_kept}")
    print(f"Doublons refuses : {result.duplicates_refused}")
    print(f"Conflits blancs refuses : {result.white_conflicts_refused}")
    print(f"Lignes refusees pour parsing/export : {result.parse_refused}")
    print(f"Fichiers ecrits : {len(written)}")
    print()
    print("Problemes generes par longueur :")
    for plies in sorted(args.plan):
        count = len(result.planned_by_plies[plies])
        target = args.plan[plies]
        folder = result.target_dirs[plies]
        status = "OK" if count >= target else "incomplet"
        reused = "reutilise" if folder in result.existing_dirs else "cree"
        print(f"- {plies} demi-coups : {count}/{target} ({status}) -> {relative(folder)} ({reused})")
    missing = incomplete_lengths(args, result)
    if missing:
        print()
        print("Plan incomplet : " + ", ".join(missing))
        if not args.allow_partial:
            print("En generation reelle, le script refusera d'ecrire sans --allow-partial.")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.max_black_branches_per_position < 0:
            raise RuntimeError("--max-black-branches-per-position doit etre positif")
        result = build_plan(args)
        written: list[Path] = []
        if not args.dry_run:
            missing = incomplete_lengths(args, result)
            if missing and not args.allow_partial:
                raise RuntimeError("plan incomplet; dry-run d'abord, ou relancer avec --allow-partial: " + ", ".join(missing))
            written = write_plan(result)
        print_report(args, result, written)
    except RuntimeError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
