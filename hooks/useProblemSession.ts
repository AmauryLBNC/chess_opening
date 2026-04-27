"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  applyNextExpectedMove,
  clearFlash,
  isFinished,
  previousMove,
  selectSquare as selectSquareTransition,
  startProblem,
} from "@/lib/problemSession";
import type { Coord, Problem, SessionState, Side } from "@/lib/types";

const AUTO_REPLY_DELAY_MS = 350;
const FALSE_MOVE_FLASH_MS = 400;

type Timer = ReturnType<typeof setTimeout>;

function chooseProblem(problems: readonly Problem[], currentId?: number): Problem {
  if (problems.length === 0) {
    throw new Error("aucun probleme disponible");
  }
  if (problems.length === 1) {
    return problems[0];
  }

  const pool = currentId === undefined ? problems : problems.filter((problem) => problem.id !== currentId);
  return pool[Math.floor(Math.random() * pool.length)];
}

export function useProblemSession(side: Side, variant: string, problems: readonly Problem[]) {
  const [state, setState] = useState<SessionState>(() => startProblem(side, variant, problems[0]));
  const stateRef = useRef(state);
  const timersRef = useRef<Timer[]>([]);
  const autoReplyPendingRef = useRef(false);

  stateRef.current = state;

  const clearTimers = useCallback(() => {
    for (const timer of timersRef.current) {
      clearTimeout(timer);
    }
    timersRef.current = [];
    autoReplyPendingRef.current = false;
  }, []);

  const applyState = useCallback((nextState: SessionState) => {
    stateRef.current = nextState;
    setState(nextState);
  }, []);

  const scheduleFlashClear = useCallback(() => {
    const timer = setTimeout(() => {
      applyState(clearFlash(stateRef.current));
    }, FALSE_MOVE_FLASH_MS);
    timersRef.current.push(timer);
  }, [applyState]);

  const scheduleAutoReply = useCallback(() => {
    autoReplyPendingRef.current = true;
    const timer = setTimeout(() => {
      autoReplyPendingRef.current = false;
      applyState(applyNextExpectedMove(stateRef.current));
    }, AUTO_REPLY_DELAY_MS);
    timersRef.current.push(timer);
  }, [applyState]);

  const selectSquare = useCallback(
    (coord: Coord) => {
      if (autoReplyPendingRef.current) {
        return;
      }

      const result = selectSquareTransition(stateRef.current, coord);
      applyState(result.state);

      if (result.state.flashSquare) {
        scheduleFlashClear();
      }
      if (result.autoReply) {
        scheduleAutoReply();
      }
    },
    [applyState, scheduleAutoReply, scheduleFlashClear],
  );

  const newProblem = useCallback(() => {
    clearTimers();
    const problem = chooseProblem(problems, stateRef.current.problem.id);
    applyState(startProblem(side, variant, problem));
  }, [applyState, clearTimers, problems, side, variant]);

  const previous = useCallback(() => {
    clearTimers();
    applyState(previousMove(stateRef.current));
  }, [applyState, clearTimers]);

  const redo = useCallback(() => {
    clearTimers();
    applyState(startProblem(side, variant, stateRef.current.problem));
  }, [applyState, clearTimers, side, variant]);

  const solution = useCallback(() => {
    clearTimers();

    const playNext = () => {
      const nextState = applyNextExpectedMove(stateRef.current);
      applyState(nextState);

      if (!isFinished(nextState)) {
        const timer = setTimeout(playNext, AUTO_REPLY_DELAY_MS);
        timersRef.current.push(timer);
      }
    };

    if (!isFinished(stateRef.current)) {
      playNext();
    }
  }, [applyState, clearTimers]);

  useEffect(() => clearTimers, [clearTimers]);

  return {
    state,
    selectSquare,
    newProblem,
    previous,
    solution,
    redo,
  };
}
