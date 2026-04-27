import type { Side } from "@/lib/types";

export const PAWN = 1;
export const BISHOP = 3;
export const KNIGHT = 4;
export const ROOK = 5;
export const KING = 8;
export const QUEEN = 9;

const PIECE_IMAGE_FILES: Record<number, string> = {
  11: "bP.png",
  12: "wp.png",
  31: "bB.png",
  32: "wB.png",
  41: "bKN.png",
  42: "wKN.png",
  51: "bR.png",
  52: "wR.png",
  81: "bQ.png",
  82: "wQ.png",
  91: "bk.png",
  92: "wK.png",
};

const PIECE_LABELS: Record<number, string> = {
  11: "pion noir",
  12: "pion blanc",
  31: "fou noir",
  32: "fou blanc",
  41: "cavalier noir",
  42: "cavalier blanc",
  51: "tour noire",
  52: "tour blanche",
  81: "roi noir",
  82: "roi blanc",
  91: "dame noire",
  92: "dame blanche",
};

export function pieceType(piece: number): number {
  return Math.trunc(Math.abs(piece) / 10);
}

export function pieceColor(piece: number): Side | null {
  if (piece === 0) {
    return null;
  }
  return piece % 2 === 0 ? "white" : "black";
}

export function pieceImagePath(piece: number): string | null {
  const filename = PIECE_IMAGE_FILES[piece];
  return filename ? `/pieces/${filename}` : null;
}

export function pieceLabel(piece: number): string {
  return PIECE_LABELS[piece] ?? `piece ${piece}`;
}

export function sideLabel(side: Side): string {
  return side === "white" ? "blanc" : "noir";
}

export function orientationLabel(side: Side): string {
  return side === "white" ? "vue blanche" : "vue noire";
}
