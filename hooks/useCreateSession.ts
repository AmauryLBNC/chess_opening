"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { applyMove, cloneBoard, undoMove } from "@/lib/board";
import { emptyBoard, standardBoardCopy } from "@/lib/initialBoard";
import { pieceColor } from "@/lib/pieces";
import type { AppliedMove, BoardMatrix, Coord, ProblemMove, Side } from "@/lib/types";

const FALSE_MOVE_FLASH_MS = 400;

export type EditPalettePiece = 0 | 11 | 31 | 41 | 51 | 81 | 91 | 12 | 32 | 42 | 52 | 82 | 92;

const BLACK_CYCLE: EditPalettePiece[] = [0, 11, 41, 31, 51, 91, 81];
const WHITE_CYCLE: EditPalettePiece[] = [0, 12, 42, 32, 52, 92, 82];

function nextInCycle(current: number, color: Side): number {
  const cycle = color === "white" ? WHITE_CYCLE : BLACK_CYCLE;
  const idx = cycle.indexOf(current as EditPalettePiece);
  if (idx === -1) {
    return cycle[1] ?? 0;
  }
  return cycle[(idx + 1) % cycle.length];
}

export type CreateMode = "edit" | "record";

export type CreateState = {
  readonly side: Side;
  readonly variantInput: string;
  readonly initialBoard: BoardMatrix;
  readonly board: BoardMatrix;
  readonly mode: CreateMode;
  readonly editColor: Side;
  readonly turn: Side;
  readonly selected: Coord | null;
  readonly history: readonly AppliedMove[];
  readonly moves: readonly ProblemMove[];
  readonly flashSquare: Coord | null;
  readonly statusText: string;
};

function freshState(side: Side, variantInput: string): CreateState {
  return {
    side,
    variantInput,
    initialBoard: standardBoardCopy(),
    board: standardBoardCopy(),
    mode: "record",
    editColor: "white",
    turn: "white",
    selected: null,
    history: [],
    moves: [],
    flashSquare: null,
    statusText: "Joue le premier coup blanc.",
  };
}

export function useCreateSession() {
  const [state, setState] = useState<CreateState>(() => freshState("white", ""));
  const stateRef = useRef(state);
  stateRef.current = state;
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const apply = useCallback((next: CreateState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const flash = useCallback(
    (coord: Coord, message: string) => {
      const next: CreateState = { ...stateRef.current, flashSquare: coord, statusText: message };
      apply(next);
      if (flashTimerRef.current) {
        clearTimeout(flashTimerRef.current);
      }
      flashTimerRef.current = setTimeout(() => {
        apply({ ...stateRef.current, flashSquare: null });
      }, FALSE_MOVE_FLASH_MS);
    },
    [apply],
  );

  const setSide = useCallback(
    (side: Side) => {
      apply(freshState(side, stateRef.current.variantInput));
    },
    [apply],
  );

  const setVariantInput = useCallback(
    (variantInput: string) => {
      apply({ ...stateRef.current, variantInput });
    },
    [apply],
  );

  const toggleEditMode = useCallback(() => {
    const cur = stateRef.current;
    if (cur.mode === "record" && cur.history.length > 0) {
      flash([0, 0], "Annule les coups avant de revenir en mode edition.");
      return;
    }
    const nextMode: CreateMode = cur.mode === "edit" ? "record" : "edit";
    apply({
      ...cur,
      mode: nextMode,
      selected: null,
      statusText:
        nextMode === "edit"
          ? "Mode edition: clique sur une case pour cycler entre les pieces."
          : "Joue le premier coup blanc.",
    });
  }, [apply, flash]);

  const setEditColor = useCallback(
    (editColor: Side) => {
      apply({ ...stateRef.current, editColor });
    },
    [apply],
  );

  const resetBoardToStandard = useCallback(() => {
    apply({
      ...stateRef.current,
      initialBoard: standardBoardCopy(),
      board: standardBoardCopy(),
      history: [],
      moves: [],
      selected: null,
      turn: "white",
      statusText: "Position standard restauree.",
    });
  }, [apply]);

  const clearBoard = useCallback(() => {
    apply({
      ...stateRef.current,
      initialBoard: emptyBoard(),
      board: emptyBoard(),
      history: [],
      moves: [],
      selected: null,
      turn: "white",
      statusText: "Echiquier vide.",
    });
  }, [apply]);

  const handleSquareClick = useCallback(
    (coord: Coord) => {
      const cur = stateRef.current;
      if (cur.mode === "edit") {
        const board = cloneBoard(cur.board);
        const current = board[coord[0]][coord[1]];
        board[coord[0]][coord[1]] = nextInCycle(current, cur.editColor);
        apply({ ...cur, initialBoard: board, board });
        return;
      }

      if (cur.selected === null) {
        const piece = cur.board[coord[0]][coord[1]];
        if (piece === 0) {
          flash(coord, "Case vide.");
          return;
        }
        if (pieceColor(piece) !== cur.turn) {
          flash(coord, `C'est aux ${cur.turn === "white" ? "blancs" : "noirs"} de jouer.`);
          return;
        }
        apply({ ...cur, selected: coord, statusText: "Choisis la case d'arrivee." });
        return;
      }

      if (cur.selected[0] === coord[0] && cur.selected[1] === coord[1]) {
        apply({ ...cur, selected: null, statusText: "Selection annulee." });
        return;
      }

      const piece = cur.board[cur.selected[0]][cur.selected[1]];
      const captured = cur.board[coord[0]][coord[1]];
      if (captured !== 0 && pieceColor(captured) === cur.turn) {
        apply({ ...cur, selected: coord, statusText: "Selection changee." });
        return;
      }

      const move: ProblemMove = { from: cur.selected, to: coord, piece, captured };
      const result = applyMove(cur.board, move);
      const nextTurn: Side = cur.turn === "white" ? "black" : "white";
      apply({
        ...cur,
        board: result.board,
        history: [...cur.history, result.applied],
        moves: [...cur.moves, move],
        selected: null,
        turn: nextTurn,
        statusText: `Coup ${cur.moves.length + 1} enregistre. Aux ${nextTurn === "white" ? "blancs" : "noirs"} de jouer.`,
      });
    },
    [apply, flash],
  );

  const undoLastMove = useCallback(() => {
    const cur = stateRef.current;
    if (cur.history.length === 0) {
      flash([0, 0], "Aucun coup a annuler.");
      return;
    }
    const last = cur.history[cur.history.length - 1];
    const board = undoMove(cur.board, last);
    const nextTurn: Side = cur.turn === "white" ? "black" : "white";
    apply({
      ...cur,
      board,
      history: cur.history.slice(0, -1),
      moves: cur.moves.slice(0, -1),
      selected: null,
      turn: nextTurn,
      statusText: "Dernier coup annule.",
    });
  }, [apply, flash]);

  const lastMove = useMemo<ProblemMove | null>(() => {
    return state.moves.length === 0 ? null : state.moves[state.moves.length - 1];
  }, [state.moves]);

  return {
    state,
    lastMove,
    setSide,
    setVariantInput,
    toggleEditMode,
    setEditColor,
    resetBoardToStandard,
    clearBoard,
    handleSquareClick,
    undoLastMove,
  };
}
