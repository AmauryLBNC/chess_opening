"""Shared consistency helpers for Echiquier problem tools.

The functions here intentionally mirror the legacy loader behavior:
black-side source boards are rotated 180 degrees before moves are applied,
while move coordinates remain algebraic-normal.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
PROBLEMS_DIR = ROOT_DIR / "problemes"

Side = Literal["white", "black"]
Scope = Literal["global", "folder", "opening"]

PAWN = 1
KING = 8
QUEEN = 9


@dataclass(frozen=True)
class Coord:
    row: int
    col: int

    def to_algebraic(self) -> str:
        return f"{chr(self.col + ord('a'))}{8 - self.row}"


@dataclass(frozen=True)
class ProblemMove:
    from_square: Coord
    to_square: Coord
    piece: int
    captured: int
    raw_line: str
    source_line: int

    def key(self) -> str:
        return (
            f"{self.from_square.to_algebraic()}{self.to_square.to_algebraic()}"
            f"_{self.piece}_{self.captured}"
        )

    def display(self) -> str:
        return (
            f"{self.from_square.to_algebraic()} {self.to_square.to_algebraic()} "
            f"{self.piece} {self.captured}"
        )


@dataclass(frozen=True)
class ProblemFile:
    folder: str
    path: Path
    board: list[list[int]]
    moves: list[ProblemMove]


@dataclass(frozen=True)
class CandidateProblem:
    side: Side
    folder: str
    board: list[list[int]]
    moves: list[ProblemMove]
    source_name: str
    planned_file: str


@dataclass(frozen=True)
class Observation:
    move: str
    move_display: str
    file: str
    folder: str
    move_index: int
    source_line: int


@dataclass(frozen=True)
class Conflict:
    position_key: str
    existing: Observation
    conflicting: Observation


@dataclass(frozen=True)
class CandidateConflict:
    position_key: str
    candidate: Observation
    existing: Observation
    reason: str


@dataclass(frozen=True)
class ProblemError:
    file: str
    folder: str
    message: str
    line: int | None = None
    move_index: int | None = None


@dataclass(frozen=True)
class AnalysisResult:
    side: Side
    scope: Scope
    folders_analyzed: int
    problems_found: int
    problems_analyzed: int
    positions_seen: int
    position_observations: int
    coherent_reuses: int
    conflicts: list[Conflict]
    parse_errors: list[ProblemError]
    move_application_errors: list[ProblemError]


@dataclass
class ConsistencyIndex:
    side: Side
    scope: Scope = "folder"
    # bucket_key -> position_key -> move_key -> first observation for that move
    position_moves_by_bucket: dict[str, dict[str, dict[str, Observation]]] = field(default_factory=dict)
    sequences_by_folder: dict[str, set[tuple[str, ...]]] = field(default_factory=dict)

    def bucket_for(self, folder: str) -> str:
        if self.scope == "global":
            return "__global__"
        return folder

    def position_moves(self, folder: str) -> dict[str, dict[str, Observation]]:
        return self.position_moves_by_bucket.setdefault(self.bucket_for(folder), {})

    def first_observation(self, folder: str, position_key: str) -> Observation | None:
        moves = self.position_moves(folder).get(position_key)
        if not moves:
            return None
        return next(iter(moves.values()))

    def add_observation(self, folder: str, position_key: str, observation: Observation) -> None:
        self.position_moves(folder).setdefault(position_key, {}).setdefault(observation.move, observation)


class ProblemParseError(ValueError):
    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.line = line


class MoveApplicationError(ValueError):
    pass


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def side_root(side: Side) -> Path:
    return PROBLEMS_DIR / "black" if side == "black" else PROBLEMS_DIR


def numeric_sort_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (sys.maxsize, path.name)


def iter_variant_dirs(side: Side) -> list[Path]:
    base = side_root(side)
    if not base.exists():
        return []

    dirs: list[Path] = []
    for path in base.iterdir():
        if not path.is_dir():
            continue
        if path.name.startswith(".") or path.name == "__pycache__":
            continue
        if side == "white" and path.name in {"black", "_quarantine"}:
            continue
        dirs.append(path)
    return sorted(dirs, key=lambda path: path.name.lower())


def iter_problem_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in folder.glob("*.txt"):
        if path.name == "Format.txt":
            continue
        if not path.stem.isdigit():
            continue
        files.append(path)
    return sorted(files, key=numeric_sort_key)


def parse_coord(file_text: str, rank_text: str, line_number: int) -> Coord:
    file_name = file_text.lower()
    if len(file_name) != 1 or file_name < "a" or file_name > "h":
        raise ProblemParseError(f"colonne invalide: {file_text!r}", line_number)
    try:
        rank = int(rank_text)
    except ValueError as exc:
        raise ProblemParseError(f"ligne invalide: {rank_text!r}", line_number) from exc
    if rank < 1 or rank > 8:
        raise ProblemParseError(f"ligne hors echiquier: {rank_text!r}", line_number)
    return Coord(row=8 - rank, col=ord(file_name) - ord("a"))


def parse_move_line(line: str, line_number: int) -> ProblemMove:
    tokens = line.split()
    if len(tokens) < 6:
        raise ProblemParseError("coup incomplet", line_number)
    try:
        from_square = parse_coord(tokens[0], tokens[1], line_number)
        to_square = parse_coord(tokens[2], tokens[3], line_number)
        piece = int(tokens[4])
        captured = int(tokens[5])
    except ValueError as exc:
        if isinstance(exc, ProblemParseError):
            raise
        raise ProblemParseError(f"coup invalide: {line}", line_number) from exc
    return ProblemMove(from_square, to_square, piece, captured, line, line_number)


def parse_board(lines: list[str]) -> list[list[int]]:
    if len(lines) < 8:
        raise ProblemParseError("il faut au moins 8 lignes pour le plateau")

    board: list[list[int]] = []
    for index, line in enumerate(lines[:8], start=1):
        tokens = line.split()
        if len(tokens) != 8:
            raise ProblemParseError(f"8 nombres attendus pour le plateau, trouve {len(tokens)}", index)
        try:
            row = [int(token) for token in tokens]
        except ValueError as exc:
            raise ProblemParseError("valeur non numerique dans le plateau", index) from exc
        board.append(row)
    return board


def parse_moves(lines: list[str]) -> list[ProblemMove]:
    moves: list[ProblemMove] = []
    for raw_index, line in enumerate(lines[8:], start=9):
        if not line.strip():
            continue
        moves.append(parse_move_line(line, raw_index))
    return moves


def parse_problem_file(path: Path, folder: str, side: Side) -> ProblemFile:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    board = parse_board(lines)
    if side == "black":
        board = rotate_board_180(board)
    return ProblemFile(folder=folder, path=path, board=board, moves=parse_moves(lines))


def rotate_board_180(board: list[list[int]]) -> list[list[int]]:
    return [list(reversed(row)) for row in reversed(board)]


def clone_board(board: list[list[int]]) -> list[list[int]]:
    return [row[:] for row in board]


def piece_type(piece: int) -> int:
    return abs(piece) // 10


def piece_color(piece: int) -> str:
    if piece == 0:
        return "unknown"
    return "white" if piece % 2 == 0 else "black"


def board_to_key(board: list[list[int]]) -> str:
    return "/".join(".".join(str(value) for value in row) for row in board)


def position_key(board: list[list[int]], turn: str) -> str:
    return f"turn={turn}|board={board_to_key(board)}"


def move_to_key(move: ProblemMove) -> str:
    return move.key()


def piece_at(board: list[list[int]], coord: Coord) -> int:
    if coord.row < 0 or coord.row >= 8 or coord.col < 0 or coord.col >= 8:
        raise MoveApplicationError(f"coordonnees hors echiquier: {coord}")
    return board[coord.row][coord.col]


def set_piece(board: list[list[int]], coord: Coord, piece: int) -> None:
    if coord.row < 0 or coord.row >= 8 or coord.col < 0 or coord.col >= 8:
        raise MoveApplicationError(f"coordonnees hors echiquier: {coord}")
    board[coord.row][coord.col] = piece


def validate_before_move(board: list[list[int]], move: ProblemMove) -> None:
    actual_piece = piece_at(board, move.from_square)
    if actual_piece != move.piece:
        raise MoveApplicationError(
            f"{move.from_square.to_algebraic()} contient {actual_piece}, attendu {move.piece}"
        )

    destination_piece = piece_at(board, move.to_square)
    if destination_piece != move.captured:
        raise MoveApplicationError(
            f"{move.to_square.to_algebraic()} contient {destination_piece}, capture attendue {move.captured}"
        )


def apply_move(board: list[list[int]], move: ProblemMove) -> list[list[int]]:
    validate_before_move(board, move)

    next_board = clone_board(board)
    piece = piece_at(next_board, move.from_square)
    destination_piece = piece_at(next_board, move.to_square)

    if piece_type(piece) == PAWN and move.from_square.col != move.to_square.col and destination_piece == 0:
        captured_square = Coord(move.from_square.row, move.to_square.col)
        set_piece(next_board, captured_square, 0)

    set_piece(next_board, move.to_square, piece)
    set_piece(next_board, move.from_square, 0)

    if piece_type(piece) == KING and move.from_square.row == move.to_square.row:
        rook_from: Coord | None = None
        rook_to: Coord | None = None
        if move.from_square.col == 4 and move.to_square.col == 2:
            rook_from = Coord(move.from_square.row, 0)
            rook_to = Coord(move.from_square.row, 3)
        elif move.from_square.col == 4 and move.to_square.col == 6:
            rook_from = Coord(move.from_square.row, 7)
            rook_to = Coord(move.from_square.row, 5)
        if rook_from is not None and rook_to is not None:
            rook_piece = piece_at(next_board, rook_from)
            if rook_piece == 0:
                raise MoveApplicationError(f"roque invalide: aucune tour sur {rook_from.to_algebraic()}")
            set_piece(next_board, rook_to, rook_piece)
            set_piece(next_board, rook_from, 0)

    if piece_type(piece) == PAWN:
        if piece_color(piece) == "white" and move.to_square.row == 0:
            set_piece(next_board, move.to_square, QUEEN * 10 + 2)
        elif piece_color(piece) == "black" and move.to_square.row == 7:
            set_piece(next_board, move.to_square, QUEEN * 10 + 1)

    return next_board


def problem_sequence(moves: list[ProblemMove]) -> tuple[str, ...]:
    return tuple(move.key() for move in moves)


def make_observation(file_name: str, folder: str, move: ProblemMove, move_index: int) -> Observation:
    return Observation(
        move=move.key(),
        move_display=move.display(),
        file=file_name,
        folder=folder,
        move_index=move_index,
        source_line=move.source_line,
    )


def build_consistency_index(
    side: Side, verbose: bool = False, scope: Scope = "folder"
) -> tuple[ConsistencyIndex, AnalysisResult]:
    folders = iter_variant_dirs(side)
    index = ConsistencyIndex(side=side, scope=scope)
    conflicts: list[Conflict] = []
    parse_errors: list[ProblemError] = []
    move_errors: list[ProblemError] = []
    problems_found = 0
    problems_analyzed = 0
    position_observations = 0
    coherent_reuses = 0

    for folder in folders:
        problem_files = iter_problem_files(folder)
        if verbose:
            print(f"[dossier] {relative(folder)} ({len(problem_files)} fichier(s))")
        for path in problem_files:
            problems_found += 1
            if verbose:
                print(f"  [lecture] {relative(path)}")
            try:
                problem = parse_problem_file(path, folder.name, side)
            except ProblemParseError as exc:
                error = ProblemError(relative(path), folder.name, str(exc), line=exc.line)
                parse_errors.append(error)
                if verbose:
                    print(f"  [parse-error] ligne {exc.line}: {exc}")
                continue

            problems_analyzed += 1
            index.sequences_by_folder.setdefault(folder.name, set()).add(problem_sequence(problem.moves))
            board = clone_board(problem.board)
            for move_index, move in enumerate(problem.moves, start=1):
                try:
                    validate_before_move(board, move)
                except MoveApplicationError as exc:
                    error = ProblemError(
                        relative(path),
                        folder.name,
                        str(exc),
                        line=move.source_line,
                        move_index=move_index,
                    )
                    move_errors.append(error)
                    if verbose:
                        print(f"  [move-error] coup {move_index}, ligne {move.source_line}: {exc}")
                    break

                key = position_key(board, piece_color(move.piece))
                observation = make_observation(relative(path), folder.name, move, move_index)
                position_observations += 1
                moves_for_position = index.position_moves(folder.name).setdefault(key, {})
                first_observation = next(iter(moves_for_position.values()), None)
                if not moves_for_position:
                    moves_for_position[observation.move] = observation
                elif first_observation is not None and observation.move == first_observation.move:
                    coherent_reuses += 1
                else:
                    assert first_observation is not None
                    moves_for_position.setdefault(observation.move, observation)
                    conflict = Conflict(key, first_observation, observation)
                    conflicts.append(conflict)
                    if verbose:
                        print(
                            "  [conflit] "
                            f"{first_observation.file} coup {first_observation.move_index} ({first_observation.move}) "
                            f"vs {observation.file} coup {observation.move_index} ({observation.move})"
                        )

                try:
                    board = apply_move(board, move)
                except MoveApplicationError as exc:
                    error = ProblemError(
                        relative(path),
                        folder.name,
                        str(exc),
                        line=move.source_line,
                        move_index=move_index,
                    )
                    move_errors.append(error)
                    if verbose:
                        print(f"  [move-error] coup {move_index}, ligne {move.source_line}: {exc}")
                    break

    positions_seen = sum(len(bucket) for bucket in index.position_moves_by_bucket.values())
    result = AnalysisResult(
        side=side,
        scope=scope,
        folders_analyzed=len(folders),
        problems_found=problems_found,
        problems_analyzed=problems_analyzed,
        positions_seen=positions_seen,
        position_observations=position_observations,
        coherent_reuses=coherent_reuses,
        conflicts=conflicts,
        parse_errors=parse_errors,
        move_application_errors=move_errors,
    )
    return index, result


def analyze(side: Side, verbose: bool = False, scope: Scope = "folder") -> AnalysisResult:
    return build_consistency_index(side, verbose, scope)[1]


def check_candidate_problem(candidate: CandidateProblem, index: ConsistencyIndex) -> list[CandidateConflict]:
    conflicts: list[CandidateConflict] = []
    board = clone_board(candidate.board)
    for move_index, move in enumerate(candidate.moves, start=1):
        validate_before_move(board, move)
        key = position_key(board, piece_color(move.piece))
        observation = make_observation(candidate.planned_file, candidate.folder, move, move_index)
        existing_moves = index.position_moves(candidate.folder).get(key)
        if existing_moves:
            if len(existing_moves) > 1:
                conflicts.append(
                    CandidateConflict(
                        key,
                        observation,
                        next(iter(existing_moves.values())),
                        "position deja ambigue dans la base existante",
                    )
                )
            elif observation.move not in existing_moves:
                conflicts.append(
                    CandidateConflict(
                        key,
                        observation,
                        next(iter(existing_moves.values())),
                        "prochain coup different pour une position deja connue",
                    )
                )
        board = apply_move(board, move)
    return conflicts


def register_candidate_problem(candidate: CandidateProblem, index: ConsistencyIndex) -> None:
    board = clone_board(candidate.board)
    index.sequences_by_folder.setdefault(candidate.folder, set()).add(problem_sequence(candidate.moves))
    for move_index, move in enumerate(candidate.moves, start=1):
        validate_before_move(board, move)
        key = position_key(board, piece_color(move.piece))
        observation = make_observation(candidate.planned_file, candidate.folder, move, move_index)
        index.add_observation(candidate.folder, key, observation)
        board = apply_move(board, move)
