"""Plan or quarantine problem files reported as consistency suspects.

Default behavior is dry-run: no problem file and no Format.txt is modified.
Real mode moves suspect files to problemes/_quarantine/<side>/ while preserving
their original folder structure.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


ROOT_DIR = Path(__file__).resolve().parents[1]
PROBLEMS_DIR = ROOT_DIR / "problemes"
DATA_DIR = ROOT_DIR / "data"

Side = Literal["white", "black"]


@dataclass
class SuspectFile:
    source: Path
    destination: Path
    reasons: list[str] = field(default_factory=list)
    conflict_count: int = 0
    parse_error_count: int = 0
    move_error_count: int = 0


@dataclass(frozen=True)
class MoveRecord:
    source: str
    destination: str
    reasons: list[str]
    conflict_count: int
    parse_error_count: int
    move_error_count: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quarantine suspect Echiquier problem files from a consistency report.")
    parser.add_argument("--side", choices=["white", "black"], required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quarantine", action="store_true")
    parser.add_argument("--update-format", action="store_true")
    parser.add_argument(
        "--allow-global-cleanup",
        action="store_true",
        help="autorise une quarantaine reelle a partir d'un rapport scope=global",
    )
    return parser


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"rapport introuvable: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("le rapport JSON doit contenir un objet")
    return data


def resolve_report_file(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def quarantine_base(side: Side) -> Path:
    return PROBLEMS_DIR / "_quarantine" / side


def quarantine_destination(source: Path, side: Side) -> Path:
    source = source.resolve()
    try:
        rel = source.relative_to(PROBLEMS_DIR.resolve())
    except ValueError as exc:
        raise RuntimeError(f"fichier hors de problemes/: {source}") from exc

    parts = rel.parts
    if side == "black":
        if not parts or parts[0] != "black":
            raise RuntimeError(f"fichier noir inattendu: {source}")
        tail = Path(*parts[1:])
    else:
        if parts and parts[0] in {"black", "_quarantine"}:
            raise RuntimeError(f"fichier blanc inattendu: {source}")
        tail = Path(*parts)

    return quarantine_base(side) / tail


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}_conflict_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def add_reason(suspects: dict[str, SuspectFile], source: Path, side: Side, reason: str, kind: str) -> None:
    key = str(source.resolve()).lower()
    item = suspects.get(key)
    if item is None:
        item = SuspectFile(source=source, destination=quarantine_destination(source, side))
        suspects[key] = item
    item.reasons.append(reason)
    if kind == "conflict":
        item.conflict_count += 1
    elif kind == "parse":
        item.parse_error_count += 1
    elif kind == "move":
        item.move_error_count += 1


def build_plan(report: dict[str, Any], side: Side) -> list[SuspectFile]:
    suspects: dict[str, SuspectFile] = {}

    for conflict in report.get("conflicts", []):
        if not isinstance(conflict, dict):
            continue
        conflicting = conflict.get("conflicting")
        if not isinstance(conflicting, dict):
            continue
        file_value = conflicting.get("file")
        if isinstance(file_value, str) and file_value:
            source = resolve_report_file(file_value)
            move = conflicting.get("move", "coup inconnu")
            add_reason(suspects, source, side, f"conflicting dans un conflit ({move})", "conflict")

    for error in report.get("parse_errors", []):
        if not isinstance(error, dict):
            continue
        file_value = error.get("file")
        if isinstance(file_value, str) and file_value:
            source = resolve_report_file(file_value)
            add_reason(suspects, source, side, f"erreur de parsing: {error.get('message', '')}", "parse")

    for error in report.get("move_application_errors", []):
        if not isinstance(error, dict):
            continue
        file_value = error.get("file")
        if isinstance(file_value, str) and file_value:
            source = resolve_report_file(file_value)
            add_reason(suspects, source, side, f"erreur d'application: {error.get('message', '')}", "move")

    return sorted(suspects.values(), key=lambda item: relative(item.source))


def numeric_problem_count(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for path in folder.glob("*.txt") if path.name != "Format.txt" and path.stem.isdigit())


def update_format_file(folder: Path) -> None:
    count = numeric_problem_count(folder)
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


def write_manifest(side: Side, report_path: Path, moved: list[MoveRecord]) -> Path:
    manifest_path = DATA_DIR / f"problem_quarantine_manifest_{side}.json"
    payload = {
        "side": side,
        "date": datetime.now(timezone.utc).isoformat(),
        "report_used": relative(report_path),
        "files_moved": [asdict(item) for item in moved],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def execute_quarantine(plan: list[SuspectFile]) -> list[MoveRecord]:
    moved: list[MoveRecord] = []
    for item in plan:
        if not item.source.exists():
            item.reasons.append("source introuvable au moment du deplacement")
            continue
        destination = unique_destination(item.destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(item.source), str(destination))
        moved.append(
            MoveRecord(
                source=relative(item.source),
                destination=relative(destination),
                reasons=item.reasons,
                conflict_count=item.conflict_count,
                parse_error_count=item.parse_error_count,
                move_error_count=item.move_error_count,
            )
        )
    return moved


def print_report(
    side: Side,
    report_path: Path,
    mode: str,
    plan: list[SuspectFile],
    moved: list[MoveRecord],
    impacted_dirs: set[Path],
    format_updated: bool,
    report_scope: str = "global",
) -> None:
    print("# Nettoyage conflits problemes")
    print()
    print(f"Side : {side}")
    print(f"Rapport utilise : {relative(report_path)}")
    print(f"Scope du rapport : {report_scope}")
    print(f"Mode : {mode}")
    print()
    print(f"Fichiers suspects : {len(plan)}")
    print(f"Fichiers deplaces : {len(moved)}")
    print(f"Dossiers impactes : {len(impacted_dirs)}")
    print(f"Format.txt mis a jour : {'oui' if format_updated else 'non'}")
    print()
    print("Detail :")
    if not plan:
        print("- aucun fichier suspect")
    for item in plan:
        print(f"- source : {relative(item.source)}")
        print(f"  destination : {relative(item.destination)}")
        print(f"  conflits : {item.conflict_count}")
        print(f"  erreurs : {item.parse_error_count + item.move_error_count}")
        print(f"  raison : {'; '.join(item.reasons)}")
    print()
    print("Commandes suivantes proposees :")
    print(f"python tools/check_problem_consistency.py --side {side} --report data/{side}_consistency_report_after.json")
    print("python scripts/export_problems.py")
    print("npm run build")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.update_format and not args.quarantine:
        raise SystemExit("Erreur: --update-format requiert --quarantine")

    report = load_report(args.report)
    report_scope = report.get("scope") if isinstance(report.get("scope"), str) else "global"
    plan = build_plan(report, args.side)
    impacted_dirs = {item.source.parent for item in plan}
    dry_run = args.dry_run or not args.quarantine
    moved: list[MoveRecord] = []
    format_updated = False

    if not dry_run and report_scope == "global" and not args.allow_global_cleanup:
        raise SystemExit(
            "Le rapport est en scope global. Ce mode peut considerer comme conflictuelles des "
            "ouvertures differentes. Relancez d'abord avec --scope folder ou utilisez "
            "--allow-global-cleanup si vous savez ce que vous faites."
        )

    if not dry_run:
        moved = execute_quarantine(plan)
        if args.update_format:
            for folder in sorted(impacted_dirs):
                if folder.exists():
                    update_format_file(folder)
            format_updated = True
        manifest_path = write_manifest(args.side, args.report, moved)
        print(f"Manifeste ecrit : {relative(manifest_path)}")

    print_report(
        side=args.side,
        report_path=args.report,
        mode="dry-run" if dry_run else "quarantine",
        plan=plan,
        moved=moved,
        impacted_dirs=impacted_dirs,
        format_updated=format_updated,
        report_scope=report_scope,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
