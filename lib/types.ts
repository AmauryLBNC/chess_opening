export type Side = "white" | "black";
export type StatusKind = "neutral" | "danger" | "success" | "warning";

export type Coord = readonly [number, number];
export type BoardMatrix = readonly (readonly number[])[];

export type ProblemMove = {
  readonly from: Coord;
  readonly to: Coord;
  readonly piece: number;
  readonly captured: number;
};

export type Problem = {
  readonly id: number;
  readonly board: BoardMatrix;
  readonly moves: readonly ProblemMove[];
  readonly plyCount: number;
  readonly category: string;
};

export type ProblemsData = {
  readonly white: Record<string, readonly Problem[]>;
  readonly black: Record<string, readonly Problem[]>;
};

export type AppliedMove = {
  readonly move: ProblemMove;
  readonly movedPiece: number;
  readonly capturedPiece: number;
  readonly capturedSquare: Coord;
  readonly rookFrom: Coord | null;
  readonly rookTo: Coord | null;
  readonly rookPiece: number;
};

export type SessionState = {
  readonly side: Side;
  readonly variant: string;
  readonly problem: Problem;
  readonly board: BoardMatrix;
  readonly turnIndex: number;
  readonly selected: Coord | null;
  readonly legalTargets: readonly Coord[];
  readonly lastMove: ProblemMove | null;
  readonly history: readonly AppliedMove[];
  readonly statusText: string;
  readonly statusKind: StatusKind;
  readonly flashSquare: Coord | null;
};

export type SelectSquareResult = {
  readonly state: SessionState;
  readonly autoReply: boolean;
};
