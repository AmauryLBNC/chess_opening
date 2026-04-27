"use client";

import Link from "next/link";

import { Board } from "@/components/Board";
import { SidePanel } from "@/components/SidePanel";
import { useProblemSession } from "@/hooks/useProblemSession";
import { sideLabel } from "@/lib/pieces";
import type { Problem, Side } from "@/lib/types";

type TrainingScreenProps = {
  readonly side: Side;
  readonly variant: string;
  readonly problems: readonly Problem[];
};

export function TrainingScreen({ side, variant, problems }: TrainingScreenProps) {
  const session = useProblemSession(side, variant, problems);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#58b383]">Entrainement {sideLabel(side)}</p>
          <h1 className="mt-1 text-2xl font-semibold text-[#f6f1e8] sm:text-3xl">{variant}</h1>
        </div>
        <Link
          href="/"
          className="rounded-md border border-[#39352e] px-4 py-2 text-sm font-semibold text-[#d5cbbd] transition-colors hover:bg-[#24221e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
        >
          Menu
        </Link>
      </header>

      <div className="flex flex-1 flex-col items-center gap-5 lg:flex-row lg:items-start lg:justify-center">
        <Board
          board={session.state.board}
          orientation={side}
          selected={session.state.selected}
          legalTargets={session.state.legalTargets}
          lastMove={session.state.lastMove}
          flashSquare={session.state.flashSquare}
          onSquareClick={session.selectSquare}
        />
        <SidePanel
          state={session.state}
          onNewProblem={session.newProblem}
          onPrevious={session.previous}
          onSolution={session.solution}
          onRedo={session.redo}
        />
      </div>
    </main>
  );
}
