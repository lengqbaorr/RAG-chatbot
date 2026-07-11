export function stripInlineCitations(text: string): string {
  return text
    .replace(/\s*\[\s*Source\s+\d+\s*\]/gi, "")
    .replace(/\s+([.,;:!?])/g, "$1")
    .trim();
}
