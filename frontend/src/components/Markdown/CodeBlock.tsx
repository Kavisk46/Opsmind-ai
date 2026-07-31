"use client";

import { useTheme } from "next-themes";
import { PrismLight as SyntaxHighlighter } from "react-syntax-highlighter";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import css from "react-syntax-highlighter/dist/esm/languages/prism/css";
import javascript from "react-syntax-highlighter/dist/esm/languages/prism/javascript";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import jsx from "react-syntax-highlighter/dist/esm/languages/prism/jsx";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import typescript from "react-syntax-highlighter/dist/esm/languages/prism/typescript";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import {
  oneDark,
  oneLight,
} from "react-syntax-highlighter/dist/esm/styles/prism";

import { ClipboardButton } from "@/components/Clipboard";

// A curated set rather than the full ~200-language `Prism` bundle, which
// pulls in every refractor grammar and produces a ~800KB chunk. Anything
// outside this list still renders — just as plain, unhighlighted code
// (verified: PrismLight degrades gracefully for unregistered languages
// instead of throwing).
SyntaxHighlighter.registerLanguage("bash", bash);
SyntaxHighlighter.registerLanguage("css", css);
SyntaxHighlighter.registerLanguage("javascript", javascript);
SyntaxHighlighter.registerLanguage("json", json);
SyntaxHighlighter.registerLanguage("jsx", jsx);
SyntaxHighlighter.registerLanguage("markdown", markdown);
SyntaxHighlighter.registerLanguage("python", python);
SyntaxHighlighter.registerLanguage("sql", sql);
SyntaxHighlighter.registerLanguage("tsx", tsx);
SyntaxHighlighter.registerLanguage("typescript", typescript);
SyntaxHighlighter.registerLanguage("yaml", yaml);

interface CodeBlockProps {
  language: string;
  code: string;
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const { resolvedTheme } = useTheme();

  return (
    <div className="my-2 overflow-hidden rounded-md border border-border text-left">
      <div className="flex items-center justify-between bg-muted px-3 py-1.5 text-xs text-muted-foreground">
        <span className="font-mono">{language || "text"}</span>
        <ClipboardButton
          text={code}
          ariaLabel="Copy code"
          label="Copy"
          variant="inline"
          successMessage="Code copied to clipboard"
        />
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={resolvedTheme === "dark" ? oneDark : oneLight}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          fontSize: "0.8125rem",
          padding: "0.75rem",
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
