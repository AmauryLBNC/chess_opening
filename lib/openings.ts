import rawFolderMap from "@/data/opening_folder_map.json";
import rawOpenings from "@/data/openings.json";
import rawProblems from "@/data/problems.json";
import type { Side } from "@/lib/types";

export type LichessOpening = {
  readonly id: string;
  readonly eco: string;
  readonly name: string;
  readonly label: string;
  readonly moves_pgn: string | null;
  readonly moves_uci: string | null;
  readonly source: string;
  readonly source_file: string;
  readonly source_line: number;
};

export type OpeningFolderMapEntry = {
  readonly folder?: string;
  readonly match_type?: string;
  readonly display_name?: string;
  readonly eco?: string;
};

export type OpeningFolderMap = {
  readonly white?: Record<string, OpeningFolderMapEntry>;
  readonly black?: Record<string, OpeningFolderMapEntry>;
  readonly unmatched_project_folders?: {
    readonly white?: readonly string[];
    readonly black?: readonly string[];
  };
  readonly unmatched_openings_sample?: readonly unknown[];
};

export type OpeningMetadata = {
  readonly side: Side;
  readonly folder: string;
  readonly label: string | null;
  readonly name: string;
  readonly displayName: string;
  readonly eco: string | null;
  readonly problemCount: number | null;
  readonly hasMapping: boolean;
};

export type OpeningWithProblems = OpeningMetadata;

const openings = rawOpenings as readonly LichessOpening[];
const folderMap = rawFolderMap as OpeningFolderMap;
const problemsBySide = rawProblems as Partial<Record<Side, Record<string, readonly unknown[]>>>;

function stripAccents(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function normalizeForCompare(value: string): string {
  return stripAccents(value)
    .toLowerCase()
    .replace(/['`]/g, "")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function getSideProblems(side: Side): Record<string, readonly unknown[]> {
  return problemsBySide[side] ?? {};
}

function getProblemCount(side: Side, folderName: string): number | null {
  const entries = getSideProblems(side)[folderName];
  return Array.isArray(entries) ? entries.length : null;
}

function countPgnMoves(movesPgn: string | null): number {
  if (!movesPgn) {
    return Number.MAX_SAFE_INTEGER;
  }

  return movesPgn
    .split(/\s+/)
    .filter((token) => token.length > 0)
    .filter((token) => !/^\d+\.(\.\.)?$/.test(token))
    .filter((token) => !["*", "1-0", "0-1", "1/2-1/2"].includes(token)).length;
}

function findOpeningByLabel(label: string | null, eco: string | null): LichessOpening | null {
  if (!label) {
    return null;
  }

  const labelKey = normalizeForCompare(label);
  const matches = openings.filter((opening) => {
    if (normalizeForCompare(opening.label) !== labelKey) {
      return false;
    }
    return eco ? opening.eco === eco : true;
  });

  return (
    matches.sort((a, b) => {
      const moveDiff = countPgnMoves(a.moves_pgn) - countPgnMoves(b.moves_pgn);
      if (moveDiff !== 0) {
        return moveDiff;
      }
      return a.name.localeCompare(b.name);
    })[0] ?? null
  );
}

function findFolderMapping(
  folderName: string,
  side: Side,
): { readonly label: string; readonly entry: OpeningFolderMapEntry } | null {
  const sideMap = folderMap[side] ?? {};
  const folderKey = normalizeForCompare(folderName);

  for (const [label, entry] of Object.entries(sideMap)) {
    if (!entry.folder) {
      continue;
    }
    if (entry.folder === folderName || normalizeForCompare(entry.folder) === folderKey) {
      return { label, entry };
    }
  }

  return null;
}

export function normalizeFolderDisplayName(folderName: string): string {
  const words = folderName
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter((word) => word.length > 0);

  if (words.length === 0) {
    return folderName;
  }

  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function getOpeningMetadata(folderName: string, side: Side): OpeningMetadata {
  const mapping = findFolderMapping(folderName, side);
  const mappedOpening = mapping ? findOpeningByLabel(mapping.label, mapping.entry.eco ?? null) : null;
  const fallbackDisplayName = normalizeFolderDisplayName(folderName);
  const name = mapping?.entry.display_name ?? mappedOpening?.name ?? fallbackDisplayName;
  const eco = mapping?.entry.eco ?? mappedOpening?.eco ?? null;

  return {
    side,
    folder: folderName,
    label: mapping?.label ?? null,
    name,
    displayName: name,
    eco,
    problemCount: getProblemCount(side, folderName),
    hasMapping: mapping !== null,
  };
}

export function getOpeningDisplayName(folderName: string, side: Side): string {
  return getOpeningMetadata(folderName, side).displayName;
}

export function getOpeningEco(folderName: string, side: Side): string | null {
  return getOpeningMetadata(folderName, side).eco;
}

export function getOpeningLabel(folderName: string, side: Side): string | null {
  return getOpeningMetadata(folderName, side).label;
}

export function getOpeningsWithProblems(side: Side): OpeningWithProblems[] {
  return Object.keys(getSideProblems(side))
    .map((folder) => getOpeningMetadata(folder, side))
    .sort((a, b) => {
      const displayDiff = a.displayName.localeCompare(b.displayName);
      if (displayDiff !== 0) {
        return displayDiff;
      }
      return a.folder.localeCompare(b.folder);
    });
}

export function formatOpeningDetails(opening: OpeningMetadata): string {
  const parts: string[] = [];
  if (opening.eco) {
    parts.push(`ECO ${opening.eco}`);
  }
  if (opening.problemCount !== null) {
    parts.push(`${opening.problemCount} probleme${opening.problemCount > 1 ? "s" : ""}`);
  }
  return parts.join(" | ");
}

export function openingMatchesQuery(opening: OpeningMetadata, query: string): boolean {
  const queryKey = normalizeForCompare(query);
  if (queryKey.length === 0) {
    return true;
  }

  const searchable = [
    opening.folder,
    opening.label ?? "",
    opening.name,
    opening.displayName,
    opening.eco ?? "",
    normalizeFolderDisplayName(opening.folder),
  ]
    .map(normalizeForCompare)
    .join(" ");

  return searchable.includes(queryKey);
}
