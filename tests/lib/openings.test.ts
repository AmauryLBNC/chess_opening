import { describe, expect, it } from "vitest";

import {
  getOpeningDisplayName,
  getOpeningEco,
  getOpeningLabel,
  getOpeningMetadata,
  getOpeningsWithProblems,
  normalizeFolderDisplayName,
} from "@/lib/openings";

describe("openings metadata", () => {
  it("enrichit un dossier blanc avec le mapping Lichess sans changer le dossier technique", () => {
    const opening = getOpeningMetadata("defense_francaise", "white");

    expect(opening.folder).toBe("defense_francaise");
    expect(opening.displayName).toBe("French Defense");
    expect(opening.eco).toBe("C00");
    expect(opening.label).toBe("french_defense");
    expect(opening.hasMapping).toBe(true);
    expect(opening.problemCount ?? 0).toBeGreaterThan(0);
  });

  it("enrichit aussi les dossiers noirs", () => {
    const opening = getOpeningMetadata("two_knights_defence", "black");

    expect(opening.folder).toBe("two_knights_defence");
    expect(opening.displayName).toBe("Italian Game: Two Knights Defense");
    expect(opening.eco).toBe("C55");
    expect(opening.hasMapping).toBe(true);
  });

  it("retombe sur un affichage lisible quand aucun mapping n'existe", () => {
    const opening = getOpeningMetadata("nouvelle_ouverture_test", "white");

    expect(opening.folder).toBe("nouvelle_ouverture_test");
    expect(opening.displayName).toBe("Nouvelle Ouverture Test");
    expect(opening.label).toBeNull();
    expect(opening.eco).toBeNull();
    expect(opening.problemCount).toBeNull();
    expect(opening.hasMapping).toBe(false);
  });

  it("expose des helpers simples pour les metadonnees principales", () => {
    expect(getOpeningDisplayName("sicilienne", "white")).toBe("Sicilian Defense");
    expect(getOpeningEco("sicilienne", "white")).toBe("B20");
    expect(getOpeningLabel("sicilienne", "white")).toBe("sicilian_defense");
  });

  it("liste seulement les ouvertures qui ont des problemes en conservant les dossiers", () => {
    const openings = getOpeningsWithProblems("white");
    const folders = openings.map((opening) => opening.folder);

    expect(folders).toContain("defense_francaise");
    expect(openings.every((opening) => opening.problemCount !== null)).toBe(true);
  });
});

describe("normalizeFolderDisplayName", () => {
  it("genere un nom lisible depuis un dossier", () => {
    expect(normalizeFolderDisplayName("defense_francaise")).toBe("Defense Francaise");
    expect(normalizeFolderDisplayName("trois-cavaliers")).toBe("Trois Cavaliers");
  });
});
