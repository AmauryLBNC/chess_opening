"use client";

import { Board } from "@/components/Board";
import type { BoardMatrix, Coord, ProblemMove, Side } from "@/lib/types";

type MoveRecorderProps = {
  readonly board: BoardMatrix;
  readonly orientation: Side;
  readonly selected: Coord | null;
  readonly lastMove: ProblemMove | null;
  readonly flashSquare: Coord | null;
  readonly onSquareClick: (coord: Coord) => void;
};

export function MoveRecorder({
  board,
  orientation,
  selected,
  lastMove,
  flashSquare,
  onSquareClick,
}: MoveRecorderProps) {
  return (
    <Board
      board={board}
      orientation={orientation}
      selected={selected}
      legalTargets={[]}
      lastMove={lastMove}
      flashSquare={flashSquare}
      onSquareClick={onSquareClick}
    />
  );
}
