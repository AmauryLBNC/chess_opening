"use client";

import { Board } from "@/components/Board";
import type { BoardMatrix, Coord, Side } from "@/lib/types";

type PositionEditorProps = {
  readonly board: BoardMatrix;
  readonly orientation: Side;
  readonly flashSquare: Coord | null;
  readonly onSquareClick: (coord: Coord) => void;
};

export function PositionEditor({ board, orientation, flashSquare, onSquareClick }: PositionEditorProps) {
  return (
    <Board
      board={board}
      orientation={orientation}
      selected={null}
      legalTargets={[]}
      lastMove={null}
      flashSquare={flashSquare}
      onSquareClick={onSquareClick}
    />
  );
}
