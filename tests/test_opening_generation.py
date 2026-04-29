from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import generate_opening_problems as generator  # noqa: E402
import generate_e4_repertoire as e4_generator  # noqa: E402
import generate_opening_problems_safe as safe_generator  # noqa: E402
import problem_consistency_lib as consistency  # noqa: E402
import rollback_generated_openings as rollback  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_fixture_project(root: Path) -> None:
    openings = [
        {
            "id": "A00_a",
            "eco": "A00",
            "name": "Fixture A",
            "label": "fixture_a",
            "moves_pgn": "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6",
            "moves_uci": None,
        },
        {
            "id": "B20_b",
            "eco": "B20",
            "name": "Fixture Sicilian",
            "label": "fixture_sicilian",
            "moves_pgn": "1. e4 c5 2. Nf3 d6 3. d4 cxd4",
            "moves_uci": None,
        },
        {
            "id": "C00_c",
            "eco": "C00",
            "name": "Fixture French",
            "label": "fixture_french",
            "moves_pgn": "1. e4 e6 2. d4 d5 3. Nc3 Nf6",
            "moves_uci": None,
        },
        {
            "id": "B12_d",
            "eco": "B12",
            "name": "Fixture Caro",
            "label": "fixture_caro",
            "moves_pgn": "1. e4 c6 2. d4 d5 3. Nc3 dxe4",
            "moves_uci": None,
        },
    ]
    folder_map = {
        "white": {
            "fixture_a": {"folder": "folder_a", "display_name": "Fixture A", "eco": "A00"},
            "fixture_sicilian": {"folder": "folder_b", "display_name": "Fixture Sicilian", "eco": "B20"},
        },
        "black": {},
    }
    write_json(root / "data" / "openings.json", openings)
    write_json(root / "data" / "opening_folder_map.json", folder_map)


@contextlib.contextmanager
def patched_project(root: Path):
    old_generator = (
        generator.ROOT_DIR,
        generator.OPENINGS_JSON,
        generator.FOLDER_MAP_JSON,
        generator.PROBLEMS_DIR,
    )
    old_consistency = (consistency.ROOT_DIR, consistency.PROBLEMS_DIR)
    old_rollback = (
        rollback.ROOT_DIR,
        rollback.PROBLEMS_DIR,
        rollback.OPENINGS_JSON,
        rollback.DEFAULT_WHITE_KEEP_LIST,
    )
    generator.ROOT_DIR = root
    generator.OPENINGS_JSON = root / "data" / "openings.json"
    generator.FOLDER_MAP_JSON = root / "data" / "opening_folder_map.json"
    generator.PROBLEMS_DIR = root / "problemes"
    consistency.ROOT_DIR = root
    consistency.PROBLEMS_DIR = root / "problemes"
    rollback.ROOT_DIR = root
    rollback.PROBLEMS_DIR = root / "problemes"
    rollback.OPENINGS_JSON = root / "data" / "openings.json"
    rollback.DEFAULT_WHITE_KEEP_LIST = root / "data" / "white_repertoire_keep_list.txt"
    try:
        yield
    finally:
        (
            generator.ROOT_DIR,
            generator.OPENINGS_JSON,
            generator.FOLDER_MAP_JSON,
            generator.PROBLEMS_DIR,
        ) = old_generator
        consistency.ROOT_DIR, consistency.PROBLEMS_DIR = old_consistency
        (
            rollback.ROOT_DIR,
            rollback.PROBLEMS_DIR,
            rollback.OPENINGS_JSON,
            rollback.DEFAULT_WHITE_KEEP_LIST,
        ) = old_rollback


def write_simple_problem(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "Format.txt").write_text("1\n", encoding="utf-8")
    (folder / "1.txt").write_text(
        "\n".join(
            [
                "51 41 31 91 81 31 41 51",
                "11 11 11 11 11 11 11 11",
                "0 0 0 0 0 0 0 0",
                "0 0 0 0 0 0 0 0",
                "0 0 0 0 0 0 0 0",
                "0 0 0 0 0 0 0 0",
                "12 12 12 12 12 12 12 12",
                "52 42 32 92 82 32 42 52",
                "e 2 e 4 12 0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def make_args(**overrides: object) -> argparse.Namespace:
    values = {
        "side": "white",
        "mode": "catalogue",
        "limit": 2,
        "plies": 6,
        "min_plies": 2,
        "max_plies": 12,
        "dry_run": True,
        "overwrite": False,
        "skip_existing": True,
        "prefer_uncovered": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class SafeOpeningGenerationTests(unittest.TestCase):
    def test_dry_run_writes_no_problem_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)
            with patched_project(root), patch.object(
                sys,
                "argv",
                [
                    "generate_opening_problems_safe.py",
                    "--side",
                    "white",
                    "--mode",
                    "catalogue",
                    "--plies",
                    "6",
                    "--limit",
                    "1",
                    "--dry-run",
                ],
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(safe_generator.main(), 0)

            self.assertFalse((root / "problemes").exists())

    def test_catalogue_scope_allows_different_folders_from_initial_position(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)
            with patched_project(root):
                (
                    plans,
                    duplicates,
                    parse_rejections,
                    conflict_rejections,
                    too_short,
                    _candidates_analyzed,
                    _states,
                    _index,
                    _duplicate_keys,
                ) = safe_generator.plan_safe_generation(make_args())

            self.assertEqual(len(plans), 2)
            self.assertEqual(len({plan.problem.folder for plan in plans}), 2)
            self.assertTrue(all(plan.problem.generated_plies == 6 for plan in plans))
            self.assertEqual(duplicates, [])
            self.assertEqual(parse_rejections, [])
            self.assertEqual(conflict_rejections, [])
            self.assertEqual(too_short, 0)


class RollbackGeneratedOpeningsTests(unittest.TestCase):
    def test_rollback_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)
            write_simple_problem(root / "problemes" / "generated_label")
            keep_list = root / "data" / "white_repertoire_keep_list.txt"
            keep_list.write_text("kept_folder\n", encoding="utf-8")

            with patched_project(root), patch.object(rollback, "collect_tracked_files", return_value=set()), patch.object(
                sys,
                "argv",
                ["rollback_generated_openings.py", "--side", "white", "--dry-run", "--timestamp", "test"],
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rollback.main(), 0)

            self.assertTrue((root / "problemes" / "generated_label" / "1.txt").exists())
            self.assertFalse((root / "problemes" / "_quarantine_generated").exists())

    def test_rollback_quarantine_moves_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)
            write_simple_problem(root / "problemes" / "generated_label")
            keep_list = root / "data" / "white_repertoire_keep_list.txt"
            keep_list.write_text("kept_folder\n", encoding="utf-8")

            with patched_project(root), patch.object(rollback, "collect_tracked_files", return_value=set()), patch.object(
                sys,
                "argv",
                [
                    "rollback_generated_openings.py",
                    "--side",
                    "white",
                    "--quarantine",
                    "--update-format",
                    "--timestamp",
                    "test",
                ],
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rollback.main(), 0)

            self.assertFalse((root / "problemes" / "generated_label").exists())
            self.assertTrue((root / "problemes" / "_quarantine_generated" / "test" / "generated_label" / "1.txt").exists())


class E4RepertoireGenerationTests(unittest.TestCase):
    def test_e4_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)

            with patched_project(root), patch.object(
                sys,
                "argv",
                ["generate_e4_repertoire.py", "--side", "white", "--plan", "6:2", "--dry-run"],
            ), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(e4_generator.main(), 0)

            self.assertFalse((root / "problemes").exists())

    def test_e4_plan_lengths_and_repertoire_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture_project(root)

            with patched_project(root):
                result = e4_generator.build_plan(make_args(plan={6: 4}, max_black_branches_per_position=0))

            plans = result.planned_by_plies[6]
            self.assertEqual(len(plans), 4)
            self.assertTrue(all(plan.uci[0] == "e2e4" for plan in plans))
            self.assertTrue(all(plan.problem.generated_plies == 6 for plan in plans))
            self.assertGreater(len({plan.uci[1] for plan in plans}), 1)
            self.assertEqual(result.white_conflicts_refused, 0)

            registry = e4_generator.RepertoireRegistry()
            for plan in plans:
                board = e4_generator.board_rows_to_list(plan.problem)
                ok, reason = registry.check(board, plan.moves)
                self.assertTrue(ok, reason)
                registry.register(board, plan.moves)

            self.assertGreaterEqual(sum(len(moves) for moves in registry.black_moves_by_position.values()), 2)


if __name__ == "__main__":
    unittest.main()
