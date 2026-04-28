import { describe, expect, it } from "vitest";

import { isValidVariantName, normalizeVariantName } from "@/lib/variantName";

describe("normalizeVariantName", () => {
  it("convertit en minuscules et retire les accents", () => {
    expect(normalizeVariantName("Defense Francaise")).toBe("defense_francaise");
    expect(normalizeVariantName("Défense Française")).toBe("defense_francaise");
  });

  it("compresse les espaces et caracteres non alphanumeriques en underscores", () => {
    expect(normalizeVariantName("  partie    italienne ")).toBe("partie_italienne");
    expect(normalizeVariantName("trois-cavaliers!!")).toBe("trois_cavaliers");
  });

  it("ne laisse pas d'underscore en debut ni en fin", () => {
    expect(normalizeVariantName("___Sicilienne___")).toBe("sicilienne");
    expect(normalizeVariantName("!?,sicilienne!")).toBe("sicilienne");
  });

  it("renvoie une chaine vide si l'entree ne contient aucun caractere valide", () => {
    expect(normalizeVariantName("")).toBe("");
    expect(normalizeVariantName("   ")).toBe("");
    expect(normalizeVariantName("!!??")).toBe("");
  });
});

describe("isValidVariantName", () => {
  it("est vrai pour une entree normalisable", () => {
    expect(isValidVariantName("Sicilienne")).toBe(true);
  });

  it("est faux pour une entree vide ou non normalisable", () => {
    expect(isValidVariantName("")).toBe(false);
    expect(isValidVariantName("!!")).toBe(false);
  });
});
