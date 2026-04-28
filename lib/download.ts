export function downloadTextFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function copyTextToClipboard(content: string): Promise<boolean> {
  if (!navigator.clipboard) {
    return false;
  }
  try {
    await navigator.clipboard.writeText(content);
    return true;
  } catch {
    return false;
  }
}
