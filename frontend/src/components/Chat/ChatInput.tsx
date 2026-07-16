"use client";

import { Send } from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { Button } from "@/components/ui/button";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

const MAX_LENGTH = 4000;
const MAX_TEXTAREA_HEIGHT_PX = 200;

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [value]);

  // Desktop-only: auto-focusing on mobile would pop the on-screen keyboard
  // the instant the page loads, which is jarring rather than convenient.
  useEffect(() => {
    if (window.matchMedia("(min-width: 1024px)").matches) {
      textareaRef.current?.focus();
    }
  }, []);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }
    onSend(trimmed);
    setValue("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    submit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
      return;
    }
    if (event.key === "Escape" && value) {
      event.preventDefault();
      setValue("");
    }
  };

  const isNearLimit = value.length >= MAX_LENGTH * 0.9;

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-1 border-t border-border p-4"
    >
      <div className="flex items-end gap-2">
        <label htmlFor="chat-input" className="sr-only">
          Message the AI Assistant
        </label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          maxLength={MAX_LENGTH}
          placeholder="Ask your AI Assistant anything…"
          className={cn(
            "max-h-[200px] flex-1 resize-none overflow-y-auto rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50",
            FOCUS_RING_CLASS
          )}
        />
        <Button
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <Send className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
      {value.length > 0 && (
        <span
          className={cn(
            "self-end text-xs text-muted-foreground",
            isNearLimit && "text-destructive"
          )}
        >
          {value.length}/{MAX_LENGTH}
        </span>
      )}
    </form>
  );
}
