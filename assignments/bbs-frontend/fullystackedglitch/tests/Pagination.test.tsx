import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Pagination } from "../src/components/Pagination";

describe("Pagination", () => {
  it("disables Prev on page 1 and Next when no more pages", () => {
    render(<Pagination page={1} hasNext={false} onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /previous page/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next page/i })).toBeDisabled();
  });

  it("marks the current page with aria-current and shows the next page when hasNext", () => {
    render(<Pagination page={2} hasNext={true} onChange={() => {}} />);
    const active = screen.getByRole("button", { name: "Page 2" });
    expect(active).toHaveAttribute("aria-current", "page");

    // hasNext means we render page 3 as a clickable target without claiming
    // the API has more beyond it.
    expect(screen.getByRole("button", { name: "Page 3" })).toBeInTheDocument();
  });

  it("calls onChange(page+1) when Next is clicked", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={2} hasNext={true} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: /next page/i }));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("calls onChange with the clicked page number", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Pagination page={3} hasNext={true} onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: "Page 1" }));
    expect(onChange).toHaveBeenCalledWith(1);
  });
});
