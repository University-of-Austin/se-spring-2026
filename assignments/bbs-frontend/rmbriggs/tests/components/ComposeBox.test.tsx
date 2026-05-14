import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ComposeBox from "@/components/ComposeBox";

describe("ComposeBox", () => {
  it("test_compose_box_disables_submit_when_empty", () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("test_compose_box_enables_submit_with_text", async () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hello");
    expect(screen.getByRole("button", { name: /post/i })).not.toBeDisabled();
  });

  it("test_compose_box_shows_red_char_count_past_500", async () => {
    render(<ComposeBox onSubmit={vi.fn()} />);
    const ta = screen.getByLabelText(/message/i);
    fireEvent.change(ta, { target: { value: "x".repeat(501) } });
    expect(screen.getByTestId("char-count")).toHaveClass("text-red-600");
    expect(screen.getByRole("button", { name: /post/i })).toBeDisabled();
  });

  it("test_compose_box_submits_on_button_click", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ComposeBox onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hello");
    await userEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(onSubmit).toHaveBeenCalledWith("hello");
  });

  it("test_compose_box_submits_on_cmd_enter", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<ComposeBox onSubmit={onSubmit} />);
    const ta = screen.getByLabelText(/message/i);
    await userEvent.type(ta, "hello");
    fireEvent.keyDown(ta, { key: "Enter", metaKey: true });
    expect(onSubmit).toHaveBeenCalledWith("hello");
  });

  it("test_compose_box_surfaces_server_422_detail", async () => {
    const onSubmit = vi.fn().mockRejectedValue({ status: 422, detail: "message: too long" });
    render(<ComposeBox onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/message/i), "hi");
    await userEvent.click(screen.getByRole("button", { name: /post/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("message: too long");
  });
});
