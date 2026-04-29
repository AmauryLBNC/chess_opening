"""Generate Echiquier opening problems from data/openings.json.

The converter uses python-chess for reliable SAN/PGN and UCI handling:

    python -m pip install chess

Examples from the project root:

    python tools/generate_opening_problems.py --side white --limit 20 --dry-run
    python tools/generate_opening_problems.py --side white --limit 20
    python tools/generate_opening_problems.py --side black --limit 20 --dry-run

After a real generation, refresh the web export manually:

    python scripts/export_problems.py
    npm run dev
    npm run build
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
OPENINGS_JSON = ROOT_DIR / "data" / "openings.json"
FOLDER_MAP_JSON = ROOT_DIR / "data" / "opening_folder_map.json"
PROBLEMS_DIR = ROOT_DIR / "problemes"

Side = Literal["white", "black"]

STARTING_BOARD_ROWS = [
    [51, 41, 31, 91, 81, 31, 41, 51],
    [11, 11, 11, 11, 11, 11, 11, 11],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [12, 12, 12, 12, 12, 12, 12, 12],
    [52, 42, 32, 92, 82, 32, 42, 52],
]


@dataclass(frozen=True)
class Opening:
    id: str
    eco: str
    name: str
    label: str
    moves_pgn: str | None
    moves_uci: str | None


@dataclass(frozen=True)
class GeneratedProblem:
    opening: Opening
    folder: str
    target_dir: Path
    file_number: int
    move_lines: tuple[str, ...]
    board_rows: tuple[tuple[int, ...], ...]
    source_plies: int
    generated_plies: int
    initial_position_note: str

    @property
    def target_file(self) -> Path:
        return self.target_dir / f"{self.file_number}.txt"

    @property
    def sequence_key(self) -> tuple[str, ...]:
        return self.move_lines


@dataclass(frozen=True)
class IgnoredOpening:
    eco: str
    name: str
    label: str
    reason: str


@dataclass
class FolderState:
    path: Path
    existed_before: bool
    existing_numbers: set[int]
    sequences: set[tuple[str, ...]]
    planned_numbers: set[int] = field(default_factory=set)

    def next_number(self) -> int:
        used = self.existing_numbers | self.planned_numbers
        number = 1
        while number in used:
            number += 1
        return number

    def reserve(self, number: int, sequence: tuple[str, ...]) -> None:
        self.planned_numbers.add(number)
        self.sequences.add(sequence)

    def final_count(self) -> int:
        all_numbers = self.existing_numbers | self.planned_numbers
        return max(all_numbers) if all_numbers else 0


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"valeur booleenne invalide: {value!r}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Echiquier problem files from data/openings.json.",
    )
    parser.add_argument("--side", choices=["white", "black"], required=True, help="problem side to generate")
    parser.add_argument("--limit", type=int, default=50, help="maximum number of in-range openings to try")
    parser.add_argument("--min-plies", type=int, default=2, help="minimum source opening plies")
    parser.add_argument("--max-plies", type=int, default=12, help="maximum source opening plies")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without writing files")
    parser.add_argument(
        "--overwrite",
        nargs="?",
        const=True,
        default=False,
        type=parse_bool,
        help="allow replacing a conflicting target file; false by default",
    )
    return parser


def load_chess_module():
    try:
        import chess  # type: ignore
        import chess.pgn  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Le module python-chess est requis. Installer avec: python -m pip install chess"
        ) from exc
    return chess


def load_json(path: Path) -> Any:
    if not path.exists():
        raise RuntimeError(f"fichier introuvable: {path.relative_to(ROOT_DIR)}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_openings() -> list[Opening]:
    raw = load_json(OPENINGS_JSON)
    if not isinstance(raw, list):
        raise RuntimeError("data/openings.json doit contenir une liste")

    openings: list[Opening] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        name = str(item.get("name") or "").strip()
        if not label:
            label = slugify(name)
        openings.append(
            Opening(
                id=str(item.get("id") or ""),
                eco=str(item.get("eco") or "").strip(),
                name=name,
                label=label,
                moves_pgn=item.get("moves_pgn") if isinstance(item.get("moves_pgn"), str) else None,
                moves_uci=item.get("moves_uci") if isinstance(item.get("moves_uci"), str) else None,
            )
        )

    return sorted(openings, key=lambda opening: (opening.eco, opening.name, opening.moves_pgn or "", opening.id))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"['`]", "", ascii_value)
    ascii_value = re.sub(r"[^a-z0-9]+", "_", ascii_value)
    ascii_value = re.sub(r"_+", "_", ascii_value)
    return ascii_value.strip("_")


def side_root(side: Side) -> Path:
    return PROBLEMS_DIR if side == "white" else PROBLEMS_DIR / "black"


def load_folder_map(side: Side) -> dict[str, str]:
    if not FOLDER_MAP_JSON.exists():
        return {}

    raw = load_json(FOLDER_MAP_JSON)
    if not isinstance(raw, dict):
        return {}
    side_map = raw.get(side)
    if not isinstance(side_map, dict):
        return {}

    mapping: dict[str, str] = {}
    for raw_label, raw_entry in side_map.items():
        if not isinstance(raw_label, str) or not isinstance(raw_entry, dict):
            continue
        folder = raw_entry.get("folder")
        if isinstance(folder, str) and folder.strip():
            mapping[raw_label] = folder.strip()
    return mapping


def resolve_folder(opening: Opening, folder_map: dict[str, str]) -> str:
    mapped_label = mapped_label_for(opening.label, folder_map)
    if mapped_label:
        return folder_map[mapped_label]

    return slugify(opening.label or opening.name or opening.eco or "opening")


def mapped_label_for(label: str, folder_map: dict[str, str]) -> str | None:
    if label in folder_map:
        return label
    prefix_matches = [
        mapped_label
        for mapped_label in folder_map
        if label == mapped_label or label.startswith(f"{mapped_label}_")
    ]
    if prefix_matches:
        return max(prefix_matches, key=len)
    return None


def sort_for_generation(openings: list[Opening], folder_map: dict[str, str]) -> list[Opening]:
    return sorted(
        openings,
        key=lambda opening: (
            0 if mapped_label_for(opening.label, folder_map) else 1,
            opening.eco,
            opening.name,
            opening.moves_pgn or "",
            opening.id,
        ),
    )


def problem_file_numbers(folder: Path) -> set[int]:
    if not folder.exists():
        return set()

    numbers: set[int] = set()
    for path in folder.glob("*.txt"):
        if path.name == "Format.txt":
            continue
        if path.stem.isdigit():
            numbers.add(int(path.stem))
    return numbers


def normalize_move_sequence(lines: list[str]) -> tuple[str, ...]:
    moves: list[str] = []
    for line in lines:
        tokens = line.split()
        if len(tokens) >= 6:
            moves.append(" ".join(tokens[:6]))
    return tuple(moves)


def existing_sequences(folder: Path) -> set[tuple[str, ...]]:
    sequences: set[tuple[str, ...]] = set()
    if not folder.exists():
        return sequences

    for path in folder.glob("*.txt"):
        if path.name == "Format.txt" or not path.stem.isdigit():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) < 8:
            continue
        sequence = normalize_move_sequence(lines[8:])
        if sequence:
            sequences.add(sequence)
    return sequences


def get_folder_state(folder: Path, states: dict[Path, FolderState]) -> FolderState:
    if folder not in states:
        states[folder] = FolderState(
            path=folder,
            existed_before=folder.exists(),
            existing_numbers=problem_file_numbers(folder),
            sequences=existing_sequences(folder),
        )
    return states[folder]


def parse_opening_moves(chess: Any, opening: Opening) -> list[Any]:
    if opening.moves_uci:
        return parse_uci_moves(chess, opening.moves_uci)
    if opening.moves_pgn:
        return parse_pgn_moves(chess, opening.moves_pgn)
    raise ValueError("aucun champ moves_uci ou moves_pgn disponible")


def parse_uci_moves(chess: Any, moves_uci: str) -> list[Any]:
    board = chess.Board()
    moves: list[Any] = []
    for token in re.split(r"[\s,]+", moves_uci.strip()):
        if not token:
            continue
        move = chess.Move.from_uci(token)
        if move not in board.legal_moves:
            raise ValueError(f"coup UCI illegal: {token}")
        moves.append(move)
        board.push(move)
    return moves


def parse_pgn_moves(chess: Any, moves_pgn: str) -> list[Any]:
    game = chess.pgn.read_game(io.StringIO(moves_pgn))
    if game is None:
        raise ValueError("PGN illisible")
    if getattr(game, "errors", None):
        first_error = game.errors[0]
        raise ValueError(f"PGN invalide: {first_error}")
    return list(game.mainline_moves())


def piece_code(chess: Any, piece: Any | None) -> int:
    if piece is None:
        return 0

    type_prefix = {
        chess.PAWN: 1,
        chess.BISHOP: 3,
        chess.KNIGHT: 4,
        chess.ROOK: 5,
        chess.KING: 8,
        chess.QUEEN: 9,
    }.get(piece.piece_type)
    if type_prefix is None:
        raise ValueError(f"type de piece inconnu: {piece.piece_type}")

    color_suffix = 2 if piece.color == chess.WHITE else 1
    return type_prefix * 10 + color_suffix


def board_to_project_rows(chess: Any, board: Any) -> tuple[tuple[int, ...], ...]:
    rows: list[tuple[int, ...]] = []
    for rank in range(7, -1, -1):
        row = []
        for file_index in range(8):
            row.append(piece_code(chess, board.piece_at(chess.square(file_index, rank))))
        rows.append(tuple(row))
    return tuple(rows)


def rotate_rows_180(rows: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(reversed(row)) for row in reversed(rows))


def square_file_rank(chess: Any, square: int) -> tuple[str, int]:
    file_name = chr(chess.square_file(square) + ord("a"))
    rank = chess.square_rank(square) + 1
    return file_name, rank


def move_to_problem_line(chess: Any, board: Any, move: Any) -> str:
    moving_piece = board.piece_at(move.from_square)
    if moving_piece is None:
        raise ValueError(f"aucune piece sur {chess.square_name(move.from_square)}")
    if move.promotion is not None and move.promotion != chess.QUEEN:
        raise ValueError("sous-promotion non compatible avec le format actuel")

    captured_piece = board.piece_at(move.to_square)
    from_file, from_rank = square_file_rank(chess, move.from_square)
    to_file, to_rank = square_file_rank(chess, move.to_square)
    return (
        f"{from_file} {from_rank} {to_file} {to_rank} "
        f"{piece_code(chess, moving_piece)} {piece_code(chess, captured_piece)}"
    )


def build_problem(chess: Any, opening: Opening, side: Side, moves: list[Any]) -> GeneratedProblem:
    if not moves:
        raise ValueError("aucun coup dans la ligne")

    initial_board = chess.Board()
    selected_moves = moves
    initial_position_note = "position initiale standard"

    if side == "black":
        if len(moves) < 2:
            raise ValueError("ligne trop courte pour commencer par un coup noir")
        initial_board.push(moves[0])
        selected_moves = moves[1:]
        initial_position_note = "position apres le premier coup blanc, plateau source retourne pour la vue noire"

    board_rows = board_to_project_rows(chess, initial_board)
    if side == "black":
        board_rows = rotate_rows_180(board_rows)

    trial = initial_board.copy()
    move_lines: list[str] = []
    for move in selected_moves:
        line = move_to_problem_line(chess, trial, move)
        trial.push(move)
        move_lines.append(line)

    return GeneratedProblem(
        opening=opening,
        folder="",
        target_dir=Path(),
        file_number=0,
        move_lines=tuple(move_lines),
        board_rows=board_rows,
        source_plies=len(moves),
        generated_plies=len(move_lines),
        initial_position_note=initial_position_note,
    )


def with_target(problem: GeneratedProblem, folder: str, target_dir: Path, file_number: int) -> GeneratedProblem:
    return GeneratedProblem(
        opening=problem.opening,
        folder=folder,
        target_dir=target_dir,
        file_number=file_number,
        move_lines=problem.move_lines,
        board_rows=problem.board_rows,
        source_plies=problem.source_plies,
        generated_plies=problem.generated_plies,
        initial_position_note=problem.initial_position_note,
    )


def problem_content(problem: GeneratedProblem) -> str:
    board_text = "\n".join(" ".join(str(value) for value in row) for row in problem.board_rows)
    moves_text = "\n".join(problem.move_lines)
    return f"{board_text}\n{moves_text}\n"


def write_format_file(folder: Path, count: int) -> None:
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


def plan_generation(
    chess: Any,
    openings: list[Opening],
    side: Side,
    limit: int,
    min_plies: int,
    max_plies: int,
) -> tuple[list[GeneratedProblem], list[IgnoredOpening], list[IgnoredOpening], dict[Path, FolderState], int]:
    folder_map = load_folder_map(side)
    ordered_openings = sort_for_generation(openings, folder_map)
    states: dict[Path, FolderState] = {}
    planned: list[GeneratedProblem] = []
    ignored: list[IgnoredOpening] = []
    duplicates: list[IgnoredOpening] = []
    out_of_range_count = 0
    attempted = 0

    for opening in ordered_openings:
        if attempted >= limit:
            break

        try:
            moves = parse_opening_moves(chess, opening)
        except Exception as exc:
            ignored.append(IgnoredOpening(opening.eco, opening.name, opening.label, str(exc)))
            continue

        source_plies = len(moves)
        if source_plies < min_plies or source_plies > max_plies:
            out_of_range_count += 1
            continue

        attempted += 1
        try:
            base_problem = build_problem(chess, opening, side, moves)
        except Exception as exc:
            ignored.append(IgnoredOpening(opening.eco, opening.name, opening.label, str(exc)))
            continue

        folder = resolve_folder(opening, folder_map)
        if not folder:
            ignored.append(IgnoredOpening(opening.eco, opening.name, opening.label, "label de dossier vide"))
            continue

        target_dir = side_root(side) / folder
        state = get_folder_state(target_dir, states)
        if base_problem.sequence_key in state.sequences:
            duplicates.append(IgnoredOpening(opening.eco, opening.name, opening.label, f"doublon dans {folder}"))
            continue

        file_number = state.next_number()
        final_problem = with_target(base_problem, folder, target_dir, file_number)
        state.reserve(file_number, final_problem.sequence_key)
        planned.append(final_problem)

    return planned, ignored, duplicates, states, out_of_range_count


def write_planned_files(planned: list[GeneratedProblem], states: dict[Path, FolderState], overwrite: bool) -> list[Path]:
    written: list[Path] = []

    for problem in planned:
        problem.target_dir.mkdir(parents=True, exist_ok=True)
        target_file = problem.target_file
        if target_file.exists() and not overwrite:
            raise RuntimeError(f"refus d'ecraser un fichier existant: {target_file.relative_to(ROOT_DIR)}")
        target_file.write_text(problem_content(problem), encoding="utf-8")
        written.append(target_file)

    for folder, state in states.items():
        if state.planned_numbers:
            folder.mkdir(parents=True, exist_ok=True)
            write_format_file(folder, state.final_count())

    return written


def print_problem_details(planned: list[GeneratedProblem], dry_run: bool) -> None:
    if not planned:
        return

    print()
    print("Ouvertures selectionnees:")
    action = "serait ajoute" if dry_run else "ajoute"
    for problem in planned:
        target = problem.target_file.relative_to(ROOT_DIR).as_posix()
        print(f"- {problem.opening.eco} {problem.opening.name}")
        print(f"  cible: {target} ({action})")
        print(f"  label: {problem.opening.label}")
        print(f"  dossier: {problem.folder}")
        print(f"  plies source/generes: {problem.source_plies}/{problem.generated_plies}")
        print(f"  depart: {problem.initial_position_note}")
        print("  coups:")
        for line in problem.move_lines:
            print(f"    {line}")


def print_ignored(title: str, items: list[IgnoredOpening]) -> None:
    print()
    print(title)
    if not items:
        print("- aucun")
        return
    for item in items:
        print(f"- {item.eco} {item.name} [{item.label}]: {item.reason}")


def print_report(
    openings_count: int,
    side: Side,
    limit: int,
    min_plies: int,
    max_plies: int,
    dry_run: bool,
    planned: list[GeneratedProblem],
    ignored: list[IgnoredOpening],
    duplicates: list[IgnoredOpening],
    states: dict[Path, FolderState],
    out_of_range_count: int,
    written: list[Path],
) -> None:
    created_dirs = sorted(path for path, state in states.items() if state.planned_numbers and not state.existed_before)
    existing_dirs = sorted(path for path, state in states.items() if state.planned_numbers and state.existed_before)
    files = [problem.target_file for problem in planned]

    print("# Generation de problemes d'ouvertures")
    print()
    print("## Entrees")
    print(f"- ouvertures lues depuis data/openings.json: {openings_count}")
    print(f"- side choisi: {side}")
    print(f"- limit: {limit}")
    print(f"- min/max plies: {min_plies}/{max_plies}")
    print(f"- dry-run: {dry_run}")
    print()
    print("## Resultat")
    print(f"- problemes {'prevus' if dry_run else 'generes'}: {len(planned)}")
    print(f"- doublons ignores: {len(duplicates)}")
    print(f"- ouvertures ignorees: {len(ignored)}")
    print(f"- ouvertures hors min/max plies: {out_of_range_count}")
    print(f"- dossiers {'qui seraient crees' if dry_run else 'crees'}: {len(created_dirs)}")
    print(f"- dossiers existants utilises: {len(existing_dirs)}")
    print(f"- fichiers {'qui seraient ecrits' if dry_run else 'ecrits'}: {len(files) if dry_run else len(written)}")

    if created_dirs:
        print()
        print("Dossiers a creer:" if dry_run else "Dossiers crees:")
        for path in created_dirs:
            print(f"- {path.relative_to(ROOT_DIR).as_posix()}")

    if files:
        print()
        print("Fichiers a ecrire:" if dry_run else "Fichiers ecrits:")
        source = files if dry_run else written
        for path in source:
            print(f"- {path.relative_to(ROOT_DIR).as_posix()}")

    print_problem_details(planned, dry_run)
    print_ignored("## Doublons ignores", duplicates)
    print_ignored("## Erreurs / ignores", ignored)

    print()
    print("## Commandes suivantes")
    print("python scripts/export_problems.py")
    print("npm run dev")
    print("npm run build")


def validate_args(args: argparse.Namespace) -> None:
    if args.limit <= 0:
        raise RuntimeError("--limit doit etre superieur a 0")
    if args.min_plies < 1:
        raise RuntimeError("--min-plies doit etre superieur ou egal a 1")
    if args.max_plies < args.min_plies:
        raise RuntimeError("--max-plies doit etre superieur ou egal a --min-plies")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        validate_args(args)
        chess = load_chess_module()
        openings = load_openings()
        planned, ignored, duplicates, states, out_of_range_count = plan_generation(
            chess=chess,
            openings=openings,
            side=args.side,
            limit=args.limit,
            min_plies=args.min_plies,
            max_plies=args.max_plies,
        )
        written: list[Path] = []
        if not args.dry_run:
            written = write_planned_files(planned, states, bool(args.overwrite))

        print_report(
            openings_count=len(openings),
            side=args.side,
            limit=args.limit,
            min_plies=args.min_plies,
            max_plies=args.max_plies,
            dry_run=args.dry_run,
            planned=planned,
            ignored=ignored,
            duplicates=duplicates,
            states=states,
            out_of_range_count=out_of_range_count,
            written=written,
        )
    except RuntimeError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
