import rawProblems from "@/data/problems.json";
import type { ProblemsData, Side } from "@/lib/types";

export const problems = rawProblems as unknown as ProblemsData;
export const SIDES = ["white", "black"] as const satisfies readonly Side[];

export function isSide(value: string): value is Side {
  return value === "white" || value === "black";
}

export function variantNames(side: Side): string[] {
  return Object.keys(problems[side]).sort((a, b) => a.localeCompare(b));
}

export function problemCount(side: Side, variant?: string): number {
  if (variant) {
    return problems[side][variant]?.length ?? 0;
  }

  return Object.values(problems[side]).reduce((total, entries) => total + entries.length, 0);
}
