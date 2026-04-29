"""Move likely generated opening folders to a quarantine directory.

The tool never deletes files. In dry-run mode it only reports what would move.
Real quarantine requires a keep-list unless --allow-without-keep-list is passed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
PROBLEMS_DIR = ROOT_DIR / "problemes"
OPENINGS_JSON = ROOT_DIR / "data" / "openings.json"
DEFAULT_WHITE_KEEP_LIST = ROOT_DIR / "data" / "white_repertoire_keep_list.txt"

Side = Literal["white", "black"]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class FolderReport:
    folder: Path
    problem_count: int
    reasons: tuple[str, ...]
    destination: Path
    files: tuple[Path, ...]
    tracked_files: tuple[str, ...]
    ambiguous: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quarantine likely generated Echiquier opening folders.")
    parser.add_argument("--side", choices=["white", "black"], required=True)
    parser.add_argument("--dry-run", action="store_true", help="print the rollback plan without moving files")
    parser.add_argument("--quarantine", action="store_true", help="move detected folders to quarantine")
    parser.add_argument("--update-format", action="store_true", help="report Format.txt handling; whole-folder moves need no rewrite")
    parser.add_argument("--keep-list", type=Path, default=DEFAULT_WHITE_KEEP_LIST)
    parser.add_argument("--allow-without-keep-list", action="store_true")
    parser.add_argument("--max-problems", type=int, default=3, help="small-folder heuristic threshold")
    parser.add_argument("--timestamp", default=None, help="override quarantine timestamp for tests/reproducibility")
    return parser


def side_root(side: Side) -> Path:
    return PROBLEMS_DIR / "black" if side == "black" else PROBLEMS_DIR


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def load_keep_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keep: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = line.split("#", 1)[0].strip()
        if value:
            keep.add(value)
    return keep


def load_opening_labels() -> set[str]:
    if not OPENINGS_JSON.exists():
        return set()
    raw = json.loads(OPENINGS_JSON.read_text(encoding="utf-8"))
    labels: set[str] = set()
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("label"), str):
                labels.add(item["label"])
    return labels


def collect_tracked_files() -> set[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "problemes"],
            cwd=ROOT_DIR,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except Exception:
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def numeric_problem_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    if not folder.exists():
        return files
    for path in folder.glob("*.txt"):
        if path.name == "Format.txt":
            continue
        if path.stem.isdigit():
            files.append(path)
    return sorted(files, key=lambda path: (int(path.stem), path.name))


def all_files(folder: Path) -> tuple[Path, ...]:
    return tuple(sorted((path for path in folder.rglob("*") if path.is_file()), key=lambda path: relative(path)))


def tracked_under(folder: Path, tracked_files: set[str]) -> tuple[str, ...]:
    folder_rel = relative(folder)
    prefix = f"{folder_rel}/"
    return tuple(sorted(path for path in tracked_files if path == folder_rel or path.startswith(prefix)))


def unique_destination(base: Path, name: str) -> Path:
    candidate = base / name
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = base / f"{name}-{index}"
        if not candidate.exists():
            return candidate
        index += 1


def detect_candidates(
    side: Side,
    keep: set[str],
    tracked_files: set[str],
    opening_labels: set[str],
    quarantine_root: Path,
    max_problems: int,
) -> tuple[list[FolderReport], list[FolderReport]]:
    candidates: list[FolderReport] = []
    ambiguous: list[FolderReport] = []
    base = side_root(side)
    if not base.exists():
        return candidates, ambiguous

    for folder in sorted(base.iterdir(), key=lambda path: path.name.lower()):
        if not folder.is_dir():
            continue
        if folder.name.startswith(".") or folder.name == "__pycache__":
            continue
        if side == "white" and folder.name == "black":
            continue
        if folder.name.startswith("_quarantine"):
            continue
        if folder.name in keep:
            continue

        problem_count = len(numeric_problem_files(folder))
        tracked = tracked_under(folder, tracked_files)
        reasons: list[str] = ["absent_keep_list"]
        if not tracked:
            reasons.append("untracked_by_git")
        if problem_count <= max_problems:
            reasons.append(f"small_folder_{problem_count}")
        if folder.name in opening_labels:
            reasons.append("lichess_label")

        destination = unique_destination(quarantine_root, folder.name)
        report = FolderReport(
            folder=folder,
            problem_count=problem_count,
            reasons=tuple(reasons),
            destination=destination,
            files=all_files(folder),
            tracked_files=tracked,
            ambiguous=bool(tracked),
        )

        if tracked:
            if problem_count <= max_problems or folder.name in opening_labels:
                ambiguous.append(report)
            continue
        if problem_count > 0 or (folder / "Format.txt").exists():
            candidates.append(report)

    return candidates, ambiguous


def print_report(
    args: argparse.Namespace,
    keep_path_exists: bool,
    quarantine_root: Path,
    candidates: list[FolderReport],
    ambiguous: list[FolderReport],
    moved: list[FolderReport],
) -> None:
    mode = "dry-run" if args.dry_run or not args.quarantine else "quarantaine"
    print("# Rollback des dossiers generes")
    print()
    print(f"Side : {args.side}")
    print(f"Mode : {mode}")
    print(f"Keep-list : {relative(args.keep_list) if args.keep_list.is_absolute() else args.keep_list.as_posix()}")
    print(f"Keep-list presente : {keep_path_exists}")
    print(f"Quarantaine cible : {relative(quarantine_root)}")
    print(f"Dossiers candidats : {len(candidates)}")
    print(f"Dossiers ambigus non deplaces : {len(ambiguous)}")
    print(f"Dossiers deplaces : {len(moved)}")
    print(f"Update Format.txt : {'demande' if args.update_format else 'non demande'}")
    print("Format.txt : pas de reecriture pour les dossiers entierement deplaces.")

    print()
    print("Candidats a la quarantaine :")
    if not candidates:
        print("- aucun")
    for report in candidates:
        print(f"- {relative(report.folder)}")
        print(f"  problemes : {report.problem_count}")
        print(f"  raisons : {', '.join(report.reasons)}")
        print(f"  destination : {relative(report.destination)}")
        print(f"  fichiers : {len(report.files)}")
        for path in report.files[:8]:
            print(f"    - {relative(path)}")
        if len(report.files) > 8:
            print(f"    - ... {len(report.files) - 8} fichier(s) supplementaire(s)")

    print()
    print("Ambigus conserves :")
    if not ambiguous:
        print("- aucun")
    for report in ambiguous[:50]:
        print(f"- {relative(report.folder)}")
        print(f"  problemes : {report.problem_count}")
        print(f"  raisons : {', '.join(report.reasons)}")
        print(f"  fichiers suivis git : {len(report.tracked_files)}")
    if len(ambiguous) > 50:
        print(f"- ... {len(ambiguous) - 50} dossier(s) supplementaire(s)")


def move_to_quarantine(candidates: list[FolderReport], quarantine_root: Path) -> list[FolderReport]:
    moved: list[FolderReport] = []
    quarantine_root.mkdir(parents=True, exist_ok=True)
    for report in candidates:
        if not report.folder.exists():
            continue
        report.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(report.folder), str(report.destination))
        moved.append(report)
    return moved


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.side == "black":
        print("Erreur: rollback noir refuse par securite pour cette operation.", file=sys.stderr)
        return 1
    if args.max_problems < 0:
        print("Erreur: --max-problems doit etre positif.", file=sys.stderr)
        return 1
    if not args.dry_run and not args.quarantine:
        args.dry_run = True

    keep_path = args.keep_list if args.keep_list.is_absolute() else ROOT_DIR / args.keep_list
    args.keep_list = keep_path
    keep_path_exists = keep_path.exists()
    if args.quarantine and not keep_path_exists and not args.allow_without_keep_list:
        print(
            "Erreur: keep-list absente. Relancer en dry-run ou utiliser --allow-without-keep-list explicitement.",
            file=sys.stderr,
        )
        return 1

    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    quarantine_root = side_root(args.side) / "_quarantine_generated" / timestamp
    keep = load_keep_list(keep_path)
    opening_labels = load_opening_labels()
    tracked_files = collect_tracked_files()
    candidates, ambiguous = detect_candidates(
        args.side,
        keep,
        tracked_files,
        opening_labels,
        quarantine_root,
        args.max_problems,
    )
    moved: list[FolderReport] = []
    if args.quarantine and not args.dry_run:
        moved = move_to_quarantine(candidates, quarantine_root)

    print_report(args, keep_path_exists, quarantine_root, candidates, ambiguous, moved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
