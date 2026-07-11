import { SendHorizontal, Square } from "lucide-react";
import { FormEvent, useState } from "react";

import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";

type ChatInputProps = {
  disabled?: boolean;
  streaming?: boolean;
  onSubmit: (question: string) => void;
  onCancel: () => void;
};

export function ChatInput({ disabled, streaming, onSubmit, onCancel }: ChatInputProps) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled || streaming) return;
    setQuestion("");
    onSubmit(trimmed);
  };

  return (
    <form onSubmit={handleSubmit} className="border-t border-border bg-background p-4">
      <div className="mx-auto flex max-w-4xl items-end gap-3 rounded-lg border border-border bg-card p-2 shadow-sm">
        <textarea
          className="min-h-11 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground"
          rows={1}
          placeholder="Hỏi tài liệu của bạn..."
          value={question}
          disabled={streaming}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        {streaming ? (
          <Button type="button" variant="secondary" onClick={onCancel} aria-label="Stop generating" title="Stop generating">
            <Square className="h-4 w-4 fill-current" />
          </Button>
        ) : (
          <Button type="submit" disabled={disabled || !question.trim()} aria-label="Send">
            {disabled ? <Spinner /> : <SendHorizontal className="h-4 w-4" />}
          </Button>
        )}
      </div>
    </form>
  );
}
