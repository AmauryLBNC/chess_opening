"""Generate several exact-length opening problem batches safely.

Example:
    python tools/generate_opening_problem_batches.py --side white --mode catalogue --plan "6:400,8:300,10:200,12:100" --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generate_opening_problems import FolderState, IgnoredOpening, load_openings, parse_bool
from generate_opening_problems_safe import (
    CreatedPlan,
    DuplicateKey,
    RejectedConflict,
    build_existing_duplicate_keys,
    plan_safe_generation_with_state,
    scope_for_mode,
    validate_args as validate_safe_args,
    write_created,
)
from problem_consistency_lib import build_consistency_index, relative


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


PlanEntry = tuple[int, int]


def parse_plan(value: str) -> list[PlanEntry]:
    entries: list[PlanEntry] = []
    seen: set[int] = set()
    for raw_part in value.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if ":" not in part:
            raise argparse.ArgumentTypeError(f"entree de plan invalide: {part!r}")
        raw_plies, raw_count = part.split(":", 1)
        try:
            plies = int(raw_plies)
            count = int(raw_count)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"entree de plan non numerique: {part!r}") from exc
        if plies not in {6, 8, 10, 12}:
            raise argparse.ArgumentTypeError("--plan accepte seulement les plies 6, 8, 10 et 12")
        if count <= 0:
            raise argparse.ArgumentTypeError("chaque quantite du plan doit etre superieure a 0")
        if plies in seen:
            raise argparse.ArgumentTypeError(f"plies en double dans le plan: {plies}")
        seen.add(plies)
        entries.append((plies, count))

    if not entries:
        raise argparse.ArgumentTypeError("--plan ne doit pas etre vide")
    return entries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate exact-length Echiquier problem batches safely.")
    parser.add_argument("--side", choices=["white", "black"], required=True)
    parser.add_argument(
        "--mode",
        choices=["catalogue", "repertoire"],
        default="catalogue",
        help="catalogue: coherence par dossier (defaut). repertoire: coherence globale stricte.",
    )
    parser.add_argument("--plan", required=True, type=parse_plan, help='exemple: "6:400,8:300,10:200,12:100"')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", nargs="?", const=True, default=True, type=parse_bool)
    parser.add_argument("--prefer-uncovered", nargs="?", const=True, default=True, type=parse_bool)
    return parser


def safe_args_for_batch(args: argparse.Namespace, plies: int, limit: int) -> argparse.Namespace:
    batch_args = argparse.Namespace(
        side=args.side,
        mode=args.mode,
        limit=limit,
        plies=plies,
        min_plies=2,
        max_plies=12,
        dry_run=args.dry_run,
        overwrite=False,
        skip_existing=args.skip_existing,
        prefer_uncovered=args.prefer_uncovered,
    )
    validate_safe_args(batch_args)
    return batch_args


def print_report(
    args: argparse.Namespace,
    openings_read: int,
    plans_by_plies: dict[int, list[CreatedPlan]],
    duplicates: list[IgnoredOpening],
    parse_rejections: list[IgnoredOpening],
    conflict_rejections: list[RejectedConflict],
    too_short: int,
    candidates_analyzed: int,
    states: dict[Path, FolderState],
    written: list[Path],
) -> None:
    all_plans = [plan for plans in plans_by_plies.values() for plan in plans]
    created_dirs = sorted(path for path, state in states.items() if state.planned_numbers and not state.existed_before)

    print("# Generation batch safe de problemes")
    print()
    print(f"Side : {args.side}")
    print(f"Mode catalogue/repertoire : {args.mode}")
    print(f"Scope de conflit utilise : {scope_for_mode(args.mode)}")
    print(f"Mode ecriture : {'dry-run' if args.dry_run else 'ecriture reelle'}")
    print(f"Lignes Lichess lues : {openings_read}")
    print(f"Candidats analyses : {candidates_analyzed}")
    print(f"Candidats acceptes : {len(all_plans)}")
    print(f"Candidats refuses pour ligne trop courte : {too_short}")
    print(f"Candidats refuses pour conflit : {len(conflict_rejections)}")
    print(f"Candidats refuses pour doublon : {len(duplicates)}")
    print(f"Candidats refuses pour parsing : {len(parse_rejections)}")
    print(f"Fichiers ecrits : {len(written)}")
    print(f"Dossiers {'a creer' if args.dry_run else 'crees'} : {len(created_dirs)}")

    print()
    print("Detail par longueur :")
    for plies, requested in args.plan:
        accepted = len(plans_by_plies.get(plies, []))
        status = "OK" if accepted >= requested else "incomplet"
        print(f"- {plies} demi-coups : {accepted}/{requested} ({status})")

    if created_dirs:
        print()
        print("Dossiers a creer :" if args.dry_run else "Dossiers crees :")
        for path in created_dirs:
            print(f"- {relative(path)}")

    print()
    print("Commandes suivantes proposees :")
    print(f"python tools/check_problem_consistency.py --side {args.side} --report data/{args.side}_consistency_report_after_generation.json")
    print("python scripts/export_problems.py")
    print("npm run build")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        openings_read = len(load_openings())
        scope = scope_for_mode(args.mode)
        index, index_result = build_consistency_index(args.side, scope=scope)
        if index_result.parse_errors or index_result.move_application_errors:
            print(
                "Attention: la base existante contient des erreurs de parsing/application; "
                "les candidats restent verifies sur l'index partiel.",
                file=sys.stderr,
            )

        states: dict[Path, FolderState] = {}
        duplicate_keys_by_folder: dict[str, set[DuplicateKey]] = build_existing_duplicate_keys(args.side)
        plans_by_plies: dict[int, list[CreatedPlan]] = {}
        duplicates: list[IgnoredOpening] = []
        parse_rejections: list[IgnoredOpening] = []
        conflict_rejections: list[RejectedConflict] = []
        too_short = 0
        candidates_analyzed = 0

        for plies, limit in args.plan:
            batch_args = safe_args_for_batch(args, plies, limit)
            (
                plans,
                batch_duplicates,
                batch_parse_rejections,
                batch_conflict_rejections,
                batch_too_short,
                batch_candidates_analyzed,
                states,
                index,
                duplicate_keys_by_folder,
            ) = plan_safe_generation_with_state(
                batch_args,
                states=states,
                index=index,
                duplicate_keys_by_folder=duplicate_keys_by_folder,
            )
            plans_by_plies[plies] = plans
            duplicates.extend(batch_duplicates)
            parse_rejections.extend(batch_parse_rejections)
            conflict_rejections.extend(batch_conflict_rejections)
            too_short += batch_too_short
            candidates_analyzed += batch_candidates_analyzed

        all_plans = [plan for plans in plans_by_plies.values() for plan in plans]
        written: list[Path] = []
        if not args.dry_run:
            written = write_created(all_plans, states, overwrite=False)

        print_report(
            args=args,
            openings_read=openings_read,
            plans_by_plies=plans_by_plies,
            duplicates=duplicates,
            parse_rejections=parse_rejections,
            conflict_rejections=conflict_rejections,
            too_short=too_short,
            candidates_analyzed=candidates_analyzed,
            states=states,
            written=written,
        )
    except RuntimeError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
