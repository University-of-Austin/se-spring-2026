import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ReactionBar from "@/components/ReactionBar";

describe("ReactionBar", () => {
  it("test_reaction_bar_renders_counts", () => {
    render(<ReactionBar postId={1} counts={{ heart: 3, laugh: 1 }} canReact onReact={vi.fn()} />);
    expect(screen.getByRole("button", { name: /heart/i })).toHaveTextContent("3");
    expect(screen.getByRole("button", { name: /laugh/i })).toHaveTextContent("1");
    expect(screen.getByRole("button", { name: /fire/i })).toHaveTextContent("0");
  });

  it("test_reaction_bar_calls_onReact_with_kind", () => {
    const onReact = vi.fn().mockResolvedValue(undefined);
    render(<ReactionBar postId={1} counts={{}} canReact onReact={onReact} />);
    fireEvent.click(screen.getByRole("button", { name: /heart/i }));
    expect(onReact).toHaveBeenCalledWith("heart");
  });

  it("test_reaction_bar_disables_buttons_when_cannot_react", () => {
    render(<ReactionBar postId={1} counts={{}} canReact={false} onReact={vi.fn()} />);
    expect(screen.getByRole("button", { name: /heart/i })).toBeDisabled();
  });
});
