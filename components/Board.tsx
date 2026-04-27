"use client";

import { coordEquals } from "@/lib/board";
import type { BoardMatrix, Coord, ProblemMove, Side } from "@/lib/types";
import { Piece } from "@/components/Piece";
import { Square } from "@/components/Square";

type BoardProps = {
  readonly board: BoardMatrix;
  readonly orientation: Side;
  readonly selected: Coord | null;
  readonly legalTargets: readonly Coord[];
  readonly lastMove: ProblemMove | null;
  readonly flashSquare: Coord | null;
  readonly onSquareClick: (coord: Coord) => void;
};

const DISPLAY_INDEXES = [0, 1, 2, 3, 4, 5, 6, 7] as const;

function displayToBoardCoord(displayRow: number, displayCol: number, orientation: Side): Coord {
  return orientation === "black" ? [7 - displayRow, 7 - displayCol] : [displayRow, displayCol];
}

export function Board({
  board,
  orientation,
  selected,
  legalTargets,
  lastMove,
  flashSquare,
  onSquareClick,
}: BoardProps) {
  return (
    <div className="w-full max-w-[min(86vh,720px)]">
      <div className="board-grid aspect-square overflow-hidden rounded-lg border border-[#3a332b] bg-[#1b1b18] shadow-2xl shadow-black/35">
        {DISPLAY_INDEXES.flatMap((displayRow) =>
          DISPLAY_INDEXES.map((displayCol) => {
            const coord = displayToBoardCoord(displayRow, displayCol, orientation);
            const piece = board[coord[0]][coord[1]];
            const isLastMove =
              lastMove !== null && (coordEquals(coord, lastMove.from) || coordEquals(coord, lastMove.to));

            return (
              <Square
                key={`${coord[0]}-${coord[1]}`}
                coord={coord}
                isLight={(displayRow + displayCol) % 2 === 0}
                isSelected={coordEquals(selected, coord)}
                isLegalTarget={legalTargets.some((target) => coordEquals(target, coord))}
                isLastMove={isLastMove}
                isFlash={coordEquals(flashSquare, coord)}
                onSelect={onSquareClick}
              >
                <Piece piece={piece} />
              </Square>
            );
          }),
        )}
      </div>
    </div>
  );
}
