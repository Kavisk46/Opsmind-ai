import { describe, expect, it } from "vitest";

import { markdownToPlainText } from "./markdown-to-plain-text";

describe("markdownToPlainText", () => {
  it("strips headings", () => {
    expect(markdownToPlainText("# Title\n\n## Subtitle")).toBe("Title\n\nSubtitle");
  });

  it("strips bold and italic emphasis", () => {
    expect(markdownToPlainText("This is **bold** and *italic* text.")).toBe(
      "This is bold and italic text."
    );
  });

  it("strips bold+italic combined emphasis", () => {
    expect(markdownToPlainText("This is ***very important***.")).toBe(
      "This is very important."
    );
  });

  it("keeps a link's label and drops the URL", () => {
    expect(markdownToPlainText("See [the docs](https://example.com) for details.")).toBe(
      "See the docs for details."
    );
  });

  it("drops images but keeps alt text", () => {
    expect(markdownToPlainText("![a diagram](https://example.com/diagram.png)")).toBe(
      "a diagram"
    );
  });

  it("unwraps inline code", () => {
    expect(markdownToPlainText("Run `npm install` first.")).toBe("Run npm install first.");
  });

  it("unwraps fenced code blocks, keeping the code", () => {
    const markdown = "```python\nprint('hi')\n```";
    expect(markdownToPlainText(markdown)).toBe("print('hi')");
  });

  it("strips blockquote markers", () => {
    expect(markdownToPlainText("> This is quoted.")).toBe("This is quoted.");
  });

  it("strips unordered list markers", () => {
    expect(markdownToPlainText("- first\n- second\n- third")).toBe(
      "first\nsecond\nthird"
    );
  });

  it("strips ordered list markers", () => {
    expect(markdownToPlainText("1. first\n2. second")).toBe("first\nsecond");
  });

  it("collapses excess blank lines left behind by substitutions", () => {
    const markdown = "# Title\n\n\n\nBody text.";
    expect(markdownToPlainText(markdown)).toBe("Title\n\nBody text.");
  });

  it("leaves plain text with no markdown syntax unchanged", () => {
    expect(markdownToPlainText("Just a plain sentence.")).toBe("Just a plain sentence.");
  });

  it("handles a realistic multi-feature AI response", () => {
    const markdown =
      "## Summary\n\nThe **deployment pipeline** stalled. See [the postmortem](https://example.com) for context.\n\n- Root cause identified\n- Fix deployed\n\n> Incident resolved within 2 hours.";

    const result = markdownToPlainText(markdown);

    expect(result).toContain("Summary");
    expect(result).toContain("deployment pipeline");
    expect(result).toContain("the postmortem");
    expect(result).not.toContain("https://example.com");
    expect(result).not.toContain("**");
    expect(result).not.toContain("##");
    expect(result).not.toContain(">");
  });
});
