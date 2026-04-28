import type { BoardMatrix, ProblemMove } from "@/lib/types";

function serializeBoard(board: BoardMatrix): string {
  if (board.length !== 8) {
    throw new Error(`echiquier invalide: ${board.length} lignes (8 attendues)`);
  }
  let out = "";
  for (let row = 0; row < 8; row++) {
    if (board[row].length !== 8) {
      throw new Error(`ligne ${row} invalide: ${board[row].length} colonnes`);
    }
    for (let col = 0; col < 8; col++) {
      out += `${board[row][col]} `;
    }
    out += "\n";
  }
  return out;
}

function serializeMove(move: ProblemMove): string {
  const fromFile = String.fromCharCode(move.from[1] + "a".charCodeAt(0));
  const toFile = String.fromCharCode(move.to[1] + "a".charCodeAt(0));
  return `${fromFile} ${8 - move.from[0]} ${toFile} ${8 - move.to[0]} ${move.piece} ${move.captured}\n`;
}

export function serializeProblem(board: BoardMatrix, moves: readonly ProblemMove[]): string {
  let out = serializeBoard(board);
  for (const move of moves) {
    out += serializeMove(move);
  }
  return out;
}
