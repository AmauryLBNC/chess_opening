"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Board } from "@/components/Board";
import { SidePanel } from "@/components/SidePanel";
import { formatOpeningDetails } from "@/lib/openings";
import { useProblemSession } from "@/hooks/useProblemSession";
import { sideLabel } from "@/lib/pieces";
import type { OpeningMetadata } from "@/lib/openings";
import type { Problem, Side } from "@/lib/types";

type TrainingScreenProps = {
  readonly side: Side;
  readonly variant: string;
  readonly problems: readonly Problem[];
  readonly opening: OpeningMetadata;
};

const ALL_CATEGORIES = "Tous";
const LENGTH_CATEGORIES = [ALL_CATEGORIES, "6 demi-coups", "8 demi-coups", "10 demi-coups", "12 demi-coups"] as const;
type LengthCategory = (typeof LENGTH_CATEGORIES)[number];

function categoryButtonClasses(active: boolean, disabled: boolean): string {
  const base =
    "inline-flex h-10 items-center justify-center rounded-md border px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]";
  const state = active
    ? "border-[#58b383] bg-[#58b383] text-[#101312]"
    : "border-[#39352e] bg-[#1b1b18] text-[#d5cbbd] hover:bg-[#24221e]";
  return `${base} ${state} ${disabled ? "pointer-events-none opacity-45" : ""}`;
}

export function TrainingScreen({ side, variant, problems, opening }: TrainingScreenProps) {
  const [selectedCategory, setSelectedCategory] = useState<LengthCategory>(ALL_CATEGORIES);
  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const problem of problems) {
      counts.set(problem.category, (counts.get(problem.category) ?? 0) + 1);
    }
    return counts;
  }, [problems]);
  const filteredProblems = useMemo(() => {
    if (selectedCategory === ALL_CATEGORIES) {
      return problems;
    }
    return problems.filter((problem) => problem.category === selectedCategory);
  }, [problems, selectedCategory]);
  useEffect(() => {
    if (selectedCategory !== ALL_CATEGORIES && !categoryCounts.has(selectedCategory)) {
      setSelectedCategory(ALL_CATEGORIES);
    }
  }, [categoryCounts, selectedCategory]);
  const session = useProblemSession(side, variant, filteredProblems.length > 0 ? filteredProblems : problems);
  const openingDetails = formatOpeningDetails(opening);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-4 py-5 sm:px-6 lg:px-8">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#58b383]">Entrainement {sideLabel(side)}</p>
          <h1 className="mt-1 text-2xl font-semibold text-[#f6f1e8] sm:text-3xl">{opening.displayName}</h1>
          <p className="mt-2 font-mono text-xs text-[#8f877a]">
            {openingDetails ? `${openingDetails} | dossier: ${variant}` : `dossier: ${variant}`}
          </p>
        </div>
        <Link
          href="/"
          className="rounded-md border border-[#39352e] px-4 py-2 text-sm font-semibold text-[#d5cbbd] transition-colors hover:bg-[#24221e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7bd99d]"
        >
          Menu
        </Link>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-lg border border-[#333029] bg-[#151512]/80 p-3">
        <span className="mr-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#8f877a]">Longueur</span>
        {LENGTH_CATEGORIES.map((category) => {
          const count = category === ALL_CATEGORIES ? problems.length : (categoryCounts.get(category) ?? 0);
          const disabled = count === 0;
          return (
            <button
              key={category}
              type="button"
              disabled={disabled}
              className={categoryButtonClasses(selectedCategory === category, disabled)}
              onClick={() => setSelectedCategory(category)}
            >
              <span>{category}</span>
              <span className="ml-2 font-mono text-xs opacity-75">{count}</span>
            </button>
          );
        })}
      </div>

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
          opening={opening}
          onNewProblem={session.newProblem}
          onPrevious={session.previous}
          onSolution={session.solution}
          onRedo={session.redo}
        />
      </div>
    </main>
  );
}
