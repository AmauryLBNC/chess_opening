"""Download and adapt the Lichess chess-openings database.

Usage from the project root:

    python tools/download_and_adapt_lichess_openings.py

Then refresh the web problem export and run the web app if needed:

    python scripts/export_problems.py
    npm run dev
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT_DIR / "tools" / "lichess_openings_raw"
DATA_DIR = ROOT_DIR / "data"
OPENINGS_JSON = DATA_DIR / "openings.json"
FOLDER_MAP_JSON = DATA_DIR / "opening_folder_map.json"

SOURCE_BASE_URL = "https://raw.githubusercontent.com/lichess-org/chess-openings/master"
SOURCE_FILES = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]

KNOWN_FIELDS = {"eco", "name", "pgn", "uci", "epd", "fen"}
DEFAULT_COLUMNS = ["eco", "name", "pgn", "uci", "epd", "fen"]
FIELD_ALIASES = {
    "eco": "eco",
    "code": "eco",
    "name": "name",
    "opening": "name",
    "opening_name": "name",
    "pgn": "pgn",
    "moves": "pgn",
    "moves_pgn": "pgn",
    "uci": "uci",
    "moves_uci": "uci",
    "epd": "epd",
    "fen": "fen",
}

PROJECT_OPENING_SYNONYMS = {
    "sicilienne": "sicilian_defense",
    "defense_francaise": "french_defense",
    "francaise": "french_defense",
    "italienne": "italian_game",
    "espagnole": "ruy_lopez",
    "ruy_lopez": "ruy_lopez",
    "caro_kann": "caro_kann_defense",
    "scandinave": "scandinavian_defense",
    "london": "london_system",
    "london_system": "london_system",
    "gambit_dame": "queens_gambit",
    "anglaise": "english_opening",
    "reti": "reti_opening",
    "pirc": "pirc_defense",
    "moderne": "modern_defense",
    "slave": "slav_defense",
    "nimzo_indienne": "nimzo_indian_defense",
    "est_indienne": "kings_indian_defense",
    "indienne_du_roi": "kings_indian_defense",
    # Project-specific folder names already present in this repository.
    "quatre_cavaliers": "four_knights_game",
    "trois_cavaliers": "three_knights_opening",
}

IGNORED_FOLDER_NAMES = {
    "__pycache__",
    "black",
    "tmp",
    "temp",
    "temporary",
}


class ImportErrorWithContext(RuntimeError):
    """Raised when the importer cannot complete its main operation."""


def slugify(value: str) -> str:
    """Return the stable label format used by the local opening database."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_value = ascii_value.lower()
    ascii_value = re.sub(r"['`´]", "", ascii_value)
    ascii_value = re.sub(r"[^a-z0-9]+", "_", ascii_value)
    ascii_value = re.sub(r"_+", "_", ascii_value)
    return ascii_value.strip("_")


def canonicalize_slug(value: str) -> str:
    """Normalize spelling variants after slugification."""
    parts = slugify(value).split("_")
    parts = ["defense" if part == "defence" else part for part in parts]
    return "_".join(part for part in parts if part)


def normalize_column_name(value: str) -> str:
    value = value.strip().lstrip("\ufeff").lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def make_eco_id_part(eco: str | None) -> str:
    clean = (eco or "NA").strip().upper()
    clean = re.sub(r"[^A-Z0-9]+", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "NA"


def download_source_files() -> list[dict[str, Any]]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    downloaded: list[dict[str, Any]] = []

    for filename in SOURCE_FILES:
        url = f"{SOURCE_BASE_URL}/{filename}"
        target = RAW_DIR / filename
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Echiquier-Lichess-Openings-Importer/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
        except urllib.error.HTTPError as exc:
            raise ImportErrorWithContext(
                f"Impossible de telecharger {filename} depuis {url}: "
                f"HTTP {exc.code} {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ImportErrorWithContext(
                f"Impossible de telecharger {filename} depuis {url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise ImportErrorWithContext(
                f"Impossible de telecharger {filename} depuis {url}: timeout"
            ) from exc

        if not content.strip():
            raise ImportErrorWithContext(
                f"Le fichier telecharge est vide: {filename} ({url})"
            )

        target.write_bytes(content)
        downloaded.append(
            {
                "file": filename,
                "url": url,
                "path": str(target.relative_to(ROOT_DIR)),
                "bytes": len(content),
            }
        )

    return downloaded


def detect_columns(first_row: list[str]) -> tuple[bool, list[str]]:
    normalized = [normalize_column_name(cell) for cell in first_row]
    known_column_count = sum(1 for cell in normalized if cell in FIELD_ALIASES)
    has_header = known_column_count >= 2

    if has_header:
        columns: list[str] = []
        seen: defaultdict[str, int] = defaultdict(int)
        for column in normalized:
            mapped = FIELD_ALIASES.get(column, column or "column")
            seen[mapped] += 1
            if seen[mapped] > 1:
                mapped = f"{mapped}_{seen[mapped]}"
            columns.append(mapped)
        return True, columns

    columns = []
    for index in range(len(first_row)):
        if index < len(DEFAULT_COLUMNS):
            columns.append(DEFAULT_COLUMNS[index])
        else:
            columns.append(f"extra_{index + 1 - len(DEFAULT_COLUMNS)}")
    return False, columns


def row_to_record(columns: list[str], row: list[str]) -> dict[str, str]:
    record: dict[str, str] = {}
    for index, column in enumerate(columns):
        record[column] = row[index].strip() if index < len(row) else ""
    return record


def parse_tsv_file(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    physical_lines = text.splitlines()
    if not physical_lines:
        return [], {
            "file": path.name,
            "has_header": False,
            "columns": [],
            "line_count": 0,
            "data_rows": 0,
            "skipped_rows": 0,
        }

    rows = list(csv.reader(physical_lines, delimiter="\t"))
    first_row = rows[0] if rows else []
    has_header, columns = detect_columns(first_row)

    records: list[dict[str, Any]] = []
    skipped_rows = 0
    data_rows = 0
    start_index = 1 if has_header else 0

    for row_index in range(start_index, len(rows)):
        row = rows[row_index]
        if not row or not any(cell.strip() for cell in row):
            continue
        data_rows += 1
        if len(row) > len(columns):
            effective_columns = columns + [
                f"extra_{extra_index + 1}"
                for extra_index in range(len(row) - len(columns))
            ]
        else:
            effective_columns = columns
        record = row_to_record(effective_columns, row)
        if not any(record.get(field, "") for field in ("eco", "name", "pgn", "uci")):
            skipped_rows += 1
            continue
        record["source_file"] = path.name
        record["source_line"] = row_index + 1
        records.append(record)

    info = {
        "file": path.name,
        "has_header": has_header,
        "columns": columns,
        "line_count": len(physical_lines),
        "data_rows": data_rows,
        "skipped_rows": skipped_rows,
        "preview": physical_lines[:3],
    }
    return records, info


def parse_all_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_records: list[dict[str, Any]] = []
    format_info: list[dict[str, Any]] = []

    for filename in SOURCE_FILES:
        path = RAW_DIR / filename
        if not path.exists():
            raise ImportErrorWithContext(
                f"Fichier brut introuvable: {path.relative_to(ROOT_DIR)}"
            )
        records, info = parse_tsv_file(path)
        all_records.extend(records)
        format_info.append(info)

    return all_records, format_info


def pgn_move_count(moves_pgn: str | None) -> int:
    if not moves_pgn:
        return 10_000
    count = 0
    for token in moves_pgn.replace("\n", " ").split():
        clean = token.strip()
        if not clean:
            continue
        if clean in {"*", "1-0", "0-1", "1/2-1/2"}:
            continue
        if re.fullmatch(r"\d+\.(\.\.)?", clean):
            continue
        if re.fullmatch(r"\d+\.", clean):
            continue
        count += 1
    return count


def build_openings(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    openings: list[dict[str, Any]] = []

    for record in records:
        eco = record.get("eco", "").strip()
        name = record.get("name", "").strip()
        moves_pgn = record.get("pgn", "").strip() or None
        moves_uci = record.get("uci", "").strip() or None

        label_source = name or eco or "opening"
        label = slugify(label_source) or "opening"
        openings.append(
            {
                "eco": eco,
                "name": name,
                "label": label,
                "moves_pgn": moves_pgn,
                "moves_uci": moves_uci,
                "source": "lichess",
                "source_file": record["source_file"],
                "source_line": record["source_line"],
            }
        )

    openings.sort(
        key=lambda item: (
            item["eco"],
            item["name"],
            item["moves_pgn"] or "",
            item["source_file"],
            item["source_line"],
        )
    )

    base_counts: defaultdict[str, int] = defaultdict(int)
    duplicate_ids_fixed = 0
    for opening in openings:
        base_id = f"{make_eco_id_part(opening['eco'])}_{opening['label']}"
        base_counts[base_id] += 1
        if base_counts[base_id] == 1:
            opening["id"] = base_id
        else:
            duplicate_ids_fixed += 1
            opening["id"] = f"{base_id}_{base_counts[base_id]}"

    ordered_openings = [
        {
            "id": opening["id"],
            "eco": opening["eco"],
            "name": opening["name"],
            "label": opening["label"],
            "moves_pgn": opening["moves_pgn"],
            "moves_uci": opening["moves_uci"],
            "source": opening["source"],
            "source_file": opening["source_file"],
            "source_line": opening["source_line"],
        }
        for opening in openings
    ]

    return ordered_openings, duplicate_ids_fixed


def opening_sort_key(opening: dict[str, Any]) -> tuple[int, int, str, str, str]:
    return (
        pgn_move_count(opening.get("moves_pgn")),
        len(opening.get("name") or ""),
        opening.get("eco") or "",
        opening.get("name") or "",
        opening.get("moves_pgn") or "",
    )


def collect_project_folders(root: Path, *, exclude_black: bool = False) -> list[str]:
    if not root.exists():
        return []

    folders = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        lower_name = name.lower()
        if name.startswith(".") or lower_name in IGNORED_FOLDER_NAMES:
            continue
        if exclude_black and lower_name == "black":
            continue
        if lower_name.endswith((".tmp", ".temp")):
            continue
        folders.append(name)
    return sorted(folders, key=lambda value: value.lower())


def find_best_opening(
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not candidates:
        return None
    return sorted(candidates, key=opening_sort_key)[0]


def match_folder(
    folder: str,
    openings: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    folder_slug = canonicalize_slug(folder)
    synonym_target = PROJECT_OPENING_SYNONYMS.get(folder_slug)

    if synonym_target:
        target_slug = canonicalize_slug(synonym_target)
        exact_synonym_matches = [
            opening for opening in openings if canonicalize_slug(opening["label"]) == target_slug
        ]
        best = find_best_opening(exact_synonym_matches)
        if best:
            return best, "auto_synonym"

        contained_synonym_matches = [
            opening
            for opening in openings
            if target_slug in canonicalize_slug(opening["label"])
        ]
        best = find_best_opening(contained_synonym_matches)
        if best:
            return best, "auto_synonym_contains"

    exact_label_matches = [
        opening for opening in openings if canonicalize_slug(opening["label"]) == folder_slug
    ]
    best = find_best_opening(exact_label_matches)
    if best:
        return best, "auto_exact_label"

    label_contains_matches = [
        opening for opening in openings if folder_slug in canonicalize_slug(opening["label"])
    ]
    best = find_best_opening(label_contains_matches)
    if best:
        return best, "auto_label_contains_folder"

    name_contains_matches = [
        opening for opening in openings if folder_slug in canonicalize_slug(opening["name"])
    ]
    best = find_best_opening(name_contains_matches)
    if best:
        return best, "auto_name_contains_folder"

    return None, None


def build_folder_side_map(
    folders: list[str],
    openings: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str], int]:
    side_map: dict[str, Any] = {}
    unmatched: list[str] = []
    matched_count = 0

    for folder in folders:
        opening, match_type = match_folder(folder, openings)
        if opening is None or match_type is None:
            unmatched.append(folder)
            continue

        matched_count += 1
        key = opening["label"]
        if key in side_map:
            key = f"{key}__{canonicalize_slug(folder)}"
        side_map[key] = {
            "folder": folder,
            "match_type": match_type,
            "display_name": opening["name"],
            "eco": opening["eco"],
        }

    return side_map, unmatched, matched_count


def build_folder_map(openings: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    white_folders = collect_project_folders(ROOT_DIR / "problemes", exclude_black=True)
    black_folders = collect_project_folders(ROOT_DIR / "problemes" / "black")

    white_map, unmatched_white, matched_white = build_folder_side_map(
        white_folders, openings
    )
    black_map, unmatched_black, matched_black = build_folder_side_map(
        black_folders, openings
    )

    matched_labels = set(white_map) | set(black_map)
    unmatched_openings_sample = [
        {
            "eco": opening["eco"],
            "name": opening["name"],
            "label": opening["label"],
            "moves_pgn": opening["moves_pgn"],
        }
        for opening in openings
        if opening["label"] not in matched_labels
    ][:20]

    folder_map = {
        "white": white_map,
        "black": black_map,
        "unmatched_project_folders": {
            "white": unmatched_white,
            "black": unmatched_black,
        },
        "unmatched_openings_sample": unmatched_openings_sample,
    }

    stats = {
        "white_folder_count": len(white_folders),
        "black_folder_count": len(black_folders),
        "matched_folder_count": matched_white + matched_black,
        "unmatched_folder_count": len(unmatched_white) + len(unmatched_black),
        "unmatched_white": unmatched_white,
        "unmatched_black": unmatched_black,
    }
    return folder_map, stats


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_report(
    downloaded: list[dict[str, Any]],
    format_info: list[dict[str, Any]],
    openings: list[dict[str, Any]],
    duplicate_ids_fixed: int,
    folder_stats: dict[str, Any],
) -> None:
    total_lines = sum(info["line_count"] for info in format_info)
    total_data_rows = sum(info["data_rows"] for info in format_info)
    unique_labels = len({opening["label"] for opening in openings})
    generated_files = [
        OPENINGS_JSON.relative_to(ROOT_DIR),
        FOLDER_MAP_JSON.relative_to(ROOT_DIR),
    ]

    print("# Rapport import ouvertures Lichess")
    print()
    print("- fichiers telecharges:")
    for item in downloaded:
        print(f"  - {item['file']} ({item['bytes']} octets)")
    print("- colonnes detectees:")
    for info in format_info:
        header = "header" if info["has_header"] else "sans header"
        columns = ", ".join(info["columns"]) if info["columns"] else "(aucune)"
        print(f"  - {info['file']}: {columns} ({header})")
    print(f"- nombre total de lignes lues: {total_lines}")
    print(f"- nombre total de lignes de donnees: {total_data_rows}")
    print(f"- nombre d'ouvertures exportees: {len(openings)}")
    print(f"- nombre de labels uniques: {unique_labels}")
    print(f"- nombre d'IDs dupliques corriges: {duplicate_ids_fixed}")
    print(f"- nombre de dossiers white detectes: {folder_stats['white_folder_count']}")
    print(f"- nombre de dossiers black detectes: {folder_stats['black_folder_count']}")
    print(
        "- nombre de dossiers matches automatiquement: "
        f"{folder_stats['matched_folder_count']}"
    )
    print(
        "- nombre de dossiers non matches: "
        f"{folder_stats['unmatched_folder_count']}"
    )
    print("- fichiers generes:")
    for path in generated_files:
        print(f"  - {path.as_posix()}")

    print()
    print("Dossiers non matches:")
    print(f"- white: {folder_stats['unmatched_white'] or []}")
    print(f"- black: {folder_stats['unmatched_black'] or []}")

    print()
    print("Exemples d'ouvertures exportees:")
    for opening in openings[:5]:
        print(
            "  - "
            f"{opening['id']} | {opening['eco']} | {opening['name']} | "
            f"{opening['moves_pgn']}"
        )

    print()
    print("Commandes a lancer ensuite:")
    print("  python scripts/export_problems.py")
    print("  npm run dev")


def main() -> int:
    try:
        downloaded = download_source_files()
        records, format_info = parse_all_sources()
        openings, duplicate_ids_fixed = build_openings(records)
        folder_map, folder_stats = build_folder_map(openings)

        write_json(OPENINGS_JSON, openings)
        write_json(FOLDER_MAP_JSON, folder_map)

        print_report(
            downloaded=downloaded,
            format_info=format_info,
            openings=openings,
            duplicate_ids_fixed=duplicate_ids_fixed,
            folder_stats=folder_stats,
        )
    except ImportErrorWithContext as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Erreur fichier: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
