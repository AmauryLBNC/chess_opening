import { applyMove, cloneBoard, coordEquals, coordToAlgebraic, moveToProblemLine, pieceAt, undoMove } from "@/lib/board";
import type { Coord, Problem, ProblemMove, SelectSquareResult, SessionState, Side } from "@/lib/types";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "erreur inconnue";
}

export function isFinished(state: SessionState): boolean {
  return state.turnIndex >= state.problem.moves.length;
}

export function startProblem(side: Side, variant: string, problem: Problem): SessionState {
  return {
    side,
    variant,
    problem,
    board: cloneBoard(problem.board),
    turnIndex: 0,
    selected: null,
    legalTargets: [],
    lastMove: null,
    history: [],
    statusText: `${variant} - probleme ${problem.id}`,
    statusKind: "neutral",
    flashSquare: null,
  };
}

export function selectSquare(state: SessionState, coord: Coord): SelectSquareResult {
  if (isFinished(state)) {
    return { state, autoReply: false };
  }

  const expected = state.problem.moves[state.turnIndex];
  if (!expected) {
    return { state, autoReply: false };
  }

  if (state.selected === null) {
    const piece = pieceAt(state.board, coord);
    if (piece === 0) {
      return { state: { ...state, flashSquare: null }, autoReply: false };
    }

    const isExpectedStart = coordEquals(expected.from, coord);
    const isExpectedPiece = expected.piece === 0 || piece === expected.piece;
    return {
      state: {
        ...state,
        selected: coord,
        legalTargets: isExpectedStart && isExpectedPiece ? [expected.to] : [],
        flashSquare: null,
      },
      autoReply: false,
    };
  }

  const isExpectedMove = coordEquals(state.selected, expected.from) && coordEquals(coord, expected.to);
  if (!isExpectedMove) {
    return {
      state: {
        ...state,
        selected: null,
        legalTargets: [],
        statusText: "False move",
        statusKind: "danger",
        flashSquare: coord,
      },
      autoReply: false,
    };
  }

  const nextState = applyExpectedMove(state, expected);
  return {
    state: nextState,
    autoReply: !isFinished(nextState),
  };
}

export function applyNextExpectedMove(state: SessionState): SessionState {
  if (isFinished(state)) {
    return state;
  }
  const expected = state.problem.moves[state.turnIndex];
  return expected ? applyExpectedMove(state, expected) : state;
}

export function applyExpectedMove(state: SessionState, move: ProblemMove): SessionState {
  try {
    const actualPiece = pieceAt(state.board, move.from);
    if (move.piece !== 0 && actualPiece !== move.piece) {
      throw new Error(`piece attendue ${move.piece} sur ${coordToAlgebraic(move.from)}, trouve ${actualPiece}`);
    }

    const applied = applyMove(state.board, move);
    const turnIndex = state.turnIndex + 1;
    const finished = turnIndex >= state.problem.moves.length;
    return {
      ...state,
      board: applied.board,
      turnIndex,
      selected: null,
      legalTargets: [],
      lastMove: move,
      history: [...state.history, applied.applied],
      statusText: finished ? "GOOD" : moveToProblemLine(move),
      statusKind: finished ? "success" : "neutral",
      flashSquare: null,
    };
  } catch (error) {
    return {
      ...state,
      selected: null,
      legalTargets: [],
      statusText: errorMessage(error),
      statusKind: "danger",
      flashSquare: null,
    };
  }
}

export function previousMove(state: SessionState): SessionState {
  const last = state.history.at(-1);
  if (!last) {
    return state;
  }

  const history = state.history.slice(0, -1);
  return {
    ...state,
    board: undoMove(state.board, last),
    turnIndex: Math.max(0, state.turnIndex - 1),
    selected: null,
    legalTargets: [],
    history,
    lastMove: history.at(-1)?.move ?? null,
    statusText: "coup annule",
    statusKind: "neutral",
    flashSquare: null,
  };
}

export function clearFlash(state: SessionState): SessionState {
  if (state.flashSquare === null) {
    return state;
  }
  return { ...state, flashSquare: null };
}
