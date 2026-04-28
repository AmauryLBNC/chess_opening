export function normalizeVariantName(raw: string): string {
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return "";
  }

  const noAccents = trimmed.normalize("NFD").replace(/[̀-ͯ]/g, "");
  const lower = noAccents.toLowerCase();
  const replaced = lower.replace(/[^a-z0-9]+/g, "_");
  const stripped = replaced.replace(/^_+|_+$/g, "");
  return stripped;
}

export function isValidVariantName(raw: string): boolean {
  return normalizeVariantName(raw).length > 0;
}
