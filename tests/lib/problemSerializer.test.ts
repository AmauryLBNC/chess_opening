import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { serializeProblem } from "@/lib/problemSerializer";
import { STANDARD_BOARD } from "@/lib/initialBoard";
import type { ProblemMove } from "@/lib/types";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = resolve(HERE, "../../lib/__fixtures__/open_e4_e5.txt");

describe("serializeProblem", () => {
  it("produit un fichier strictement identique a la reference (e4 e5)", () => {
    const moves: readonly ProblemMove[] = [
      { from: [6, 4], to: [4, 4], piece: 12, captured: 0 },
      { from: [1, 4], to: [3, 4], piece: 11, captured: 0 },
    ];

    const expected = readFileSync(FIXTURE_PATH, "utf-8");
    const actual = serializeProblem(STANDARD_BOARD, moves);

    expect(actual).toBe(expected);
  });

  it("conserve le caractere espace en fin de chaque ligne plateau et termine par un saut de ligne", () => {
    const out = serializeProblem(STANDARD_BOARD, []);
    const lines = out.split("\n");
    expect(lines).toHaveLength(9);
    for (let i = 0; i < 8; i++) {
      expect(lines[i].endsWith(" ")).toBe(true);
    }
    expect(lines[8]).toBe("");
  });

  it("rejette un echiquier qui n'a pas exactement 8 lignes", () => {
    const bad = STANDARD_BOARD.slice(0, 7);
    expect(() => serializeProblem(bad, [])).toThrow(/8 lignes/);
  });
});
