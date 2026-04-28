import type { BoardMatrix } from "@/lib/types";

export const STANDARD_BOARD: BoardMatrix = [
  [51, 41, 31, 91, 81, 31, 41, 51],
  [11, 11, 11, 11, 11, 11, 11, 11],
  [0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0],
  [0, 0, 0, 0, 0, 0, 0, 0],
  [12, 12, 12, 12, 12, 12, 12, 12],
  [52, 42, 32, 92, 82, 32, 42, 52],
];

export function emptyBoard(): number[][] {
  return Array.from({ length: 8 }, () => Array.from({ length: 8 }, () => 0));
}

export function standardBoardCopy(): number[][] {
  return STANDARD_BOARD.map((row) => [...row]);
}
