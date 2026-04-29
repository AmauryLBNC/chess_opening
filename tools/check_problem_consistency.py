"""Check internal consistency of Echiquier opening problems.

Rule checked by this script:
for one training side, the same position must always have the same next
expected move.

Usage from the project root:

    python tools/check_problem_consistency.py --side black
    python tools/check_problem_consistency.py --side white
    python tools/check_problem_consistency.py --side black --verbose
    python tools/check_problem_consistency.py --side black --report data/black_consistency_report.json

This script only reads problem files and optionally writes a JSON report.
It never deletes, moves, or rewrites problem files.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from problem_consistency_lib import AnalysisResult, Conflict, ProblemError, analyze, relative


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect positions with contradictory next moves in Echiquier problem files.",
    )
    parser.add_argument("--side", choices=["white", "black"], required=True)
    parser.add_argument(
        "--scope",
        choices=["global", "folder", "opening"],
        default="folder",
        help=(
            "global: une seule reponse autorisee dans toute la couleur (mode repertoire strict). "
            "folder: une seule reponse autorisee par dossier (defaut, recommande). "
            "opening: alias de folder (mapping label/dossier deja appliquant cette equivalence)."
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--report", type=Path, help="optional JSON report path")
    return parser


def print_conflicts(conflicts: list[Conflict]) -> None:
    if not conflicts:
        print("Aucun conflit detecte.")
        return

    print("Conflits:")
    for index, conflict in enumerate(conflicts, start=1):
        print()
        print(f"Conflit {index}")
        print(f"Position key : {conflict.position_key}")
        print("Premier coup enregistre :")
        print(f"- coup : {conflict.existing.move}")
        print(f"- fichier : {conflict.existing.file}")
        print(f"- index du coup : {conflict.existing.move_index}")
        print("Coup contradictoire :")
        print(f"- coup : {conflict.conflicting.move}")
        print(f"- fichier : {conflict.conflicting.file}")
        print(f"- index du coup : {conflict.conflicting.move_index}")


def print_errors(title: str, errors: list[ProblemError]) -> None:
    if not errors:
        return
    print()
    print(title)
    for error in errors:
        location = error.file
        if error.line is not None:
            location += f":{error.line}"
        if error.move_index is not None:
            location += f" (coup {error.move_index})"
        print(f"- {location}: {error.message}")


def print_report(result: AnalysisResult) -> None:
    print("# Rapport coherence problemes")
    print()
    print(f"Side analyse : {result.side}")
    print(f"Scope : {result.scope}")
    print()
    print(f"Dossiers analyses : {result.folders_analyzed}")
    print(f"Problemes trouves : {result.problems_found}")
    print(f"Problemes analyses : {result.problems_analyzed}")
    print(f"Positions rencontrees : {result.positions_seen}")
    print(f"Observations de position : {result.position_observations}")
    print(f"Positions coherentes reutilisees : {result.coherent_reuses}")
    print(f"Conflits detectes : {len(result.conflicts)}")
    print(f"Erreurs de parsing : {len(result.parse_errors)}")
    print(f"Erreurs d'application de coup : {len(result.move_application_errors)}")
    print()
    print_conflicts(result.conflicts)
    print_errors("Erreurs de parsing", result.parse_errors)
    print_errors("Erreurs d'application de coup", result.move_application_errors)
    print()
    print("Suite possible : ce script pourra servir a refuser automatiquement un nouveau probleme conflictuel,")
    print("nettoyer les problemes noirs, lister les fichiers suspects, ou ajouter un mode --fix plus tard.")
    print("Cette version ne supprime, ne deplace et ne modifie aucun probleme.")


def write_json_report(path: Path, result: AnalysisResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    scope = "folder" if args.scope == "opening" else args.scope
    result = analyze(args.side, args.verbose, scope)
    print_report(result)

    if args.report:
        write_json_report(args.report, result)
        print()
        print(f"Rapport JSON ecrit : {relative(args.report)}")

    return 1 if result.parse_errors or result.move_application_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
