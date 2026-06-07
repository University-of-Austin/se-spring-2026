// Tests for the @mention parser. Real behavior under test: which strings
// produce a clickable link vs plain text, and where the link points.

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Mentions } from "../src/components/Mentions";

function renderWithRouter(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("Mentions", () => {
  it("renders a valid @mention as a link to that user's profile", () => {
    renderWithRouter(<Mentions text="hey @alice check this" />);
    const link = screen.getByRole("link", { name: "@alice" });
    expect(link).toHaveAttribute("href", "/users/alice");
  });

  it("does not treat email-style @ as a mention", () => {
    renderWithRouter(<Mentions text="email me at foo@bar.com" />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("ignores mentions shorter than 3 chars", () => {
    renderWithRouter(<Mentions text="hi @ab not a mention" />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("renders multiple mentions in one message", () => {
    renderWithRouter(<Mentions text="@alice and @bob_99 should meet" />);
    expect(screen.getByRole("link", { name: "@alice" })).toHaveAttribute("href", "/users/alice");
    expect(screen.getByRole("link", { name: "@bob_99" })).toHaveAttribute("href", "/users/bob_99");
  });

  it("preserves the surrounding text around mentions", () => {
    renderWithRouter(<Mentions text="welcome @newuser to the BBS" />);
    expect(screen.getByText(/welcome/)).toBeInTheDocument();
    expect(screen.getByText(/to the BBS/)).toBeInTheDocument();
  });
});
