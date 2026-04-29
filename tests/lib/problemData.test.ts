import { describe, expect, it } from "vitest";

import { problems } from "@/lib/problemData";

function expectedCategory(plyCount: number): string {
  return `${plyCount} ${plyCount === 1 ? "demi-coup" : "demi-coups"}`;
}

describe("problem data export metadata", () => {
  it("ajoute plyCount et category a chaque probleme exporte", () => {
    const exportedProblems = Object.values(problems.white).flat();
    expect(exportedProblems.length).toBeGreaterThan(0);

    for (const problem of exportedProblems) {
      expect(problem.plyCount).toBe(problem.moves.length);
      expect(problem.category).toBe(expectedCategory(problem.plyCount));
    }
  });
});
