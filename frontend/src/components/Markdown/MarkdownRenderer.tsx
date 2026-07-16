import dynamic from "next/dynamic";
import { memo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

// react-syntax-highlighter (11 language grammars + 2 themes) only loads once
// a message actually contains a fenced code block, instead of on every
// markdown render.
const CodeBlock = dynamic(() =>
  import("./CodeBlock").then((mod) => mod.CodeBlock)
);

const components: Components = {
  p({ children }) {
    return <p className="my-1 leading-relaxed first:mt-0 last:mb-0">{children}</p>;
  },
  h1({ children }) {
    return <h1 className="mt-3 mb-1 text-lg font-semibold first:mt-0">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="mt-3 mb-1 text-base font-semibold first:mt-0">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="mt-2 mb-1 text-sm font-semibold first:mt-0">{children}</h3>;
  },
  ul({ children }) {
    return <ul className="my-1 list-disc space-y-1 pl-5">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="my-1 list-decimal space-y-1 pl-5">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed">{children}</li>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="my-1 border-l-2 border-border pl-3 text-muted-foreground italic">
        {children}
      </blockquote>
    );
  },
  hr() {
    return <hr className="my-2 border-border" />;
  },
  strong({ children }) {
    return <strong className="font-semibold">{children}</strong>;
  },
  a({ children, href }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="underline underline-offset-2 hover:no-underline"
      >
        {children}
      </a>
    );
  },
  img({ src, alt }) {
    if (typeof src !== "string") {
      return null;
    }
    return (
      // Image source comes from arbitrary markdown content, not a known
      // static asset — next/image requires an allowlisted domain.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt ?? ""}
        loading="lazy"
        className="my-2 max-w-full rounded-md border border-border"
      />
    );
  },
  table({ children }) {
    return (
      <div className="my-2 overflow-x-auto rounded-md border border-border">
        <table className="w-full text-sm">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="bg-muted">{children}</thead>;
  },
  tr({ children }) {
    return <tr className="border-b border-border last:border-0">{children}</tr>;
  },
  th({ children }) {
    return (
      <th className="px-3 py-1.5 text-left font-medium whitespace-nowrap">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="px-3 py-1.5 align-top">{children}</td>;
  },
  pre({ children }) {
    return <>{children}</>;
  },
  code({ className, children }) {
    const match = /language-(\w+)/.exec(className ?? "");
    const value = String(children).replace(/\n$/, "");

    if (!match) {
      return (
        <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">
          {children}
        </code>
      );
    }

    return <CodeBlock language={match[1] ?? ""} code={value} />;
  },
};

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Memoized because MessageList re-renders every message on every streaming
// tick (the `messages` array reference changes every ~25–70ms while any
// message is streaming) — without this, every bubble's markdown would be
// re-parsed and re-syntax-highlighted on every tick, not just the one
// actually streaming. `content` is a primitive string, so the default
// shallow comparison correctly bails out for messages that didn't change.
export const MarkdownRenderer = memo(function MarkdownRenderer({
  content,
  className,
}: MarkdownRendererProps) {
  return (
    <div className={cn("text-sm", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
