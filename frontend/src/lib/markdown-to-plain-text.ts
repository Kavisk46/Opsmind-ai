// A small, pragmatic markdown stripper — not a full parser. This app
// already renders markdown through react-markdown (see components/
// Markdown/MarkdownRenderer.tsx) for DISPLAY; this is a separate,
// narrower job — producing a plausible plain-text version of the SAME
// source good enough to paste into an email or a plain-text field.
// Pulling in a second full markdown AST parser just to strip formatting
// back out isn't justified by that job; regex substitutions covering the
// syntax this app's own AI responses actually produce (headings, bold/
// italic, links, inline/fenced code, blockquotes, lists) are.
export function markdownToPlainText(markdown: string): string {
  return (
    markdown
      // Fenced code blocks: keep the code itself, drop the ``` fence
      // lines and the language tag.
      .replace(/```[\w-]*\n([\s\S]*?)```/g, "$1")
      // Inline code
      .replace(/`([^`]+)`/g, "$1")
      // Images: alt text alone rarely stands in usefully for the image,
      // but is better than leaving raw ![...](...)  syntax behind.
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
      // Links: keep the visible label, drop the URL
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      // Headings
      .replace(/^#{1,6}\s+/gm, "")
      // Bold+italic, bold, italic — longest marker first so "**bold**"
      // isn't partially consumed by the single-asterisk rule first
      .replace(/(\*\*\*|___)(.*?)\1/g, "$2")
      .replace(/(\*\*|__)(.*?)\1/g, "$2")
      .replace(/(\*|_)(.*?)\1/g, "$2")
      // Blockquotes
      .replace(/^>\s?/gm, "")
      // List markers (unordered and ordered)
      .replace(/^(\s*)[-*+]\s+/gm, "$1")
      .replace(/^(\s*)\d+\.\s+/gm, "$1")
      // Horizontal rules
      .replace(/^-{3,}$/gm, "")
      // Table pipes — not a real table layout in plain text, but leaves
      // readable cell text behind instead of a wall of "|"
      .replace(/^\|/gm, "")
      .replace(/\|$/gm, "")
      .replace(/\|/g, "  ")
      // Collapse 3+ blank lines left behind by the substitutions above
      .replace(/\n{3,}/g, "\n\n")
      .trim()
  );
}
