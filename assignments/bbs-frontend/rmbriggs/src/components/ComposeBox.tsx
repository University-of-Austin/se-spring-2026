import { FormEvent, KeyboardEvent, useState } from "react";
import { type ApiError, formatDetail } from "@/api/types";

type Props = {
  onSubmit: (message: string) => Promise<void>;
  placeholder?: string;
  buttonLabel?: string;
};

const MAX = 500;

export default function ComposeBox({ onSubmit, placeholder = "What's on your mind?", buttonLabel = "Post" }: Props) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const len = value.length;
  const valid = len > 0 && len <= MAX;

  async function submit() {
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit(value);
      setValue("");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  function onFormSubmit(e: FormEvent) {
    e.preventDefault();
    void submit();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  }

  return (
    <form onSubmit={onFormSubmit} className="border border-border rounded-lg bg-card p-3 space-y-2">
      <label htmlFor="compose-message" className="sr-only">Message</label>
      <textarea
        id="compose-message"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        rows={3}
        className="w-full resize-y border-0 focus:ring-0 p-0 text-base placeholder:text-muted-foreground"
      />
      <div className="flex items-center gap-3">
        <span
          data-testid="char-count"
          className={`text-xs ${len > MAX ? "text-destructive font-medium" : "text-muted-foreground"}`}
        >
          {len} / {MAX}
        </span>
        <button
          type="submit"
          disabled={!valid || busy}
          className="ml-auto bg-primary text-primary-foreground text-sm px-3 py-1.5 rounded disabled:opacity-50"
        >
          {busy ? "Posting…" : buttonLabel}
        </button>
      </div>
      {error && (
        <div role="alert" className="text-sm text-destructive border border-destructive bg-destructive/10 px-2 py-1 rounded">
          {error}
        </div>
      )}
    </form>
  );
}
