import { KING, PAWN, QUEEN, pieceColor, pieceType } from "@/lib/pieces";
import type { AppliedMove, BoardMatrix, Coord, ProblemMove } from "@/lib/types";

export function cloneBoard(board: BoardMatrix): number[][] {
  return board.map((row) => [...row]);
}

export function coordEquals(a: Coord | null, b: Coord | null): boolean {
  return a !== null && b !== null && a[0] === b[0] && a[1] === b[1];
}

export function isOnBoard(coord: Coord): boolean {
  return coord[0] >= 0 && coord[0] < 8 && coord[1] >= 0 && coord[1] < 8;
}

export function pieceAt(board: BoardMatrix, coord: Coord): number {
  if (!isOnBoard(coord)) {
    throw new Error(`coordonnees hors echiquier: ${coord[0]},${coord[1]}`);
  }
  return board[coord[0]][coord[1]];
}

export function applyMove(board: BoardMatrix, move: ProblemMove): {
  readonly board: BoardMatrix;
  readonly applied: AppliedMove;
} {
  const next = cloneBoard(board);
  const piece = pieceAt(next, move.from);
  if (piece === 0) {
    throw new Error(`aucune piece sur ${coordToAlgebraic(move.from)}`);
  }

  let capturedSquare: Coord = move.to;
  let capturedPiece = pieceAt(next, move.to);
  let rookFrom: Coord | null = null;
  let rookTo: Coord | null = null;
  let rookPiece = 0;

  if (pieceType(piece) === PAWN && move.from[1] !== move.to[1] && capturedPiece === 0) {
    capturedSquare = [move.from[0], move.to[1]];
    capturedPiece = pieceAt(next, capturedSquare);
    next[capturedSquare[0]][capturedSquare[1]] = 0;
  }

  next[move.to[0]][move.to[1]] = piece;
  next[move.from[0]][move.from[1]] = 0;

  if (pieceType(piece) === KING && move.from[0] === move.to[0]) {
    if (move.from[1] === 4 && move.to[1] === 2) {
      rookFrom = [move.from[0], 0];
      rookTo = [move.from[0], 3];
    } else if (move.from[1] === 4 && move.to[1] === 6) {
      rookFrom = [move.from[0], 7];
      rookTo = [move.from[0], 5];
    }

    if (rookFrom && rookTo) {
      rookPiece = pieceAt(next, rookFrom);
      next[rookTo[0]][rookTo[1]] = rookPiece;
      next[rookFrom[0]][rookFrom[1]] = 0;
    }
  }

  if (pieceType(piece) === PAWN) {
    const color = pieceColor(piece);
    if (color === "white" && move.to[0] === 0) {
      next[move.to[0]][move.to[1]] = QUEEN * 10 + 2;
    } else if (color === "black" && move.to[0] === 7) {
      next[move.to[0]][move.to[1]] = QUEEN * 10 + 1;
    }
  }

  return {
    board: next,
    applied: {
      move,
      movedPiece: piece,
      capturedPiece,
      capturedSquare,
      rookFrom,
      rookTo,
      rookPiece,
    },
  };
}

export function undoMove(board: BoardMatrix, applied: AppliedMove): BoardMatrix {
  const next = cloneBoard(board);
  const { move } = applied;

  next[move.from[0]][move.from[1]] = applied.movedPiece;

  if (coordEquals(applied.capturedSquare, move.to)) {
    next[move.to[0]][move.to[1]] = applied.capturedPiece;
  } else {
    next[move.to[0]][move.to[1]] = 0;
    next[applied.capturedSquare[0]][applied.capturedSquare[1]] = applied.capturedPiece;
  }

  if (applied.rookFrom && applied.rookTo) {
    next[applied.rookFrom[0]][applied.rookFrom[1]] = applied.rookPiece;
    next[applied.rookTo[0]][applied.rookTo[1]] = 0;
  }

  return next;
}

export function coordToAlgebraic(coord: Coord): string {
  return `${String.fromCharCode(coord[1] + "a".charCodeAt(0))}${8 - coord[0]}`;
}

export function moveToProblemLine(move: ProblemMove): string {
  const fromFile = String.fromCharCode(move.from[1] + "a".charCodeAt(0));
  const toFile = String.fromCharCode(move.to[1] + "a".charCodeAt(0));
  return `${fromFile} ${8 - move.from[0]} ${toFile} ${8 - move.to[0]} ${move.piece} ${move.captured}`;
}
