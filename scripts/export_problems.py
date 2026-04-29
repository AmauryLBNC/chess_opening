from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT = ROOT / "legacy_python"
if str(LEGACY_ROOT) not in sys.path:
    sys.path.insert(0, str(LEGACY_ROOT))

from app.models import Orientation  # noqa: E402
from app.problem_loader import LoadedProblem, ProblemLoader  # noqa: E402

PROBLEMS_DIR = ROOT / "problemes"


# Coordinate convention exported for the web app:
# every square is [row, col], zero-based, with row 0 = rank 8 and col 0 = file a.
# Black problem boards are loaded through ProblemLoader, so their matrices are
# rotated exactly like the Pygame training mode while moves stay algebraic-normal.


def category_for_ply_count(ply_count: int) -> str:
    suffix = "demi-coup" if ply_count == 1 else "demi-coups"
    return f"{ply_count} {suffix}"


def problem_to_json(problem: LoadedProblem) -> dict[str, Any]:
    ply_count = len(problem.moves)
    return {
        "id": problem.number,
        "board": problem.board.matrix.astype(int).tolist(),
        "moves": [
            {
                "from": [move.from_square.row, move.from_square.col],
                "to": [move.to_square.row, move.to_square.col],
                "piece": move.piece,
                "captured": move.captured,
            }
            for move in problem.moves
        ],
        "plyCount": ply_count,
        "category": category_for_ply_count(ply_count),
    }


def export_side(loader: ProblemLoader, orientation: Orientation) -> dict[str, list[dict[str, Any]]]:
    side: dict[str, list[dict[str, Any]]] = {}
    for variant in loader.list_variants(orientation):
        problems: list[dict[str, Any]] = []
        for number in variant.existing_numbers:
            problem = loader.load_problem(variant.name, number, orientation)
            problems.append(problem_to_json(problem))
        if problems:
            side[variant.name] = problems
    return side


def main() -> None:
    loader = ProblemLoader(PROBLEMS_DIR)
    payload = {
        "white": export_side(loader, Orientation.WHITE_VIEW),
        "black": export_side(loader, Orientation.BLACK_VIEW),
    }

    output_path = ROOT / "data" / "problems.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    white_count = sum(len(problems) for problems in payload["white"].values())
    black_count = sum(len(problems) for problems in payload["black"].values())
    print(f"Exported {white_count} white problems and {black_count} black problems to {output_path}")


if __name__ == "__main__":
    main()
