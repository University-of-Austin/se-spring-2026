import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { Boards } from "../src/pages/Boards";

vi.mock("../src/api", () => ({
  api: {
    listBoards: vi.fn(async () => [
      { name: "random",  created_at: "2026-05-02T00:00:00", post_count: 7 },
      { name: "general", created_at: "2026-05-01T00:00:00", post_count: 12 },
      { name: "tech",    created_at: "2026-05-03T00:00:00", post_count: 3 },
    ]),
  },
}));

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("Boards page", () => {
  it("renders each board with its post count once loaded", async () => {
    wrap(<Boards />);
    expect(await screen.findByText("#general")).toBeInTheDocument();
    expect(screen.getByText("#random")).toBeInTheDocument();
    expect(screen.getByText("#tech")).toBeInTheDocument();
    expect(screen.getByText("12 posts")).toBeInTheDocument();
    expect(screen.getByText("7 posts")).toBeInTheDocument();
  });

  it("pins #general first regardless of post count", async () => {
    wrap(<Boards />);
    const items = await screen.findAllByRole("listitem");
    expect(items[0]).toHaveTextContent("#general");
  });

  it("uses singular 'post' when post_count === 1", async () => {
    // Override the mock for this test only.
    const apiModule = await import("../src/api");
    (apiModule.api.listBoards as ReturnType<typeof vi.fn>).mockResolvedValueOnce([
      { name: "solo", created_at: "2026-05-01T00:00:00", post_count: 1 },
    ]);
    wrap(<Boards />);
    expect(await screen.findByText("1 post")).toBeInTheDocument();
  });

  it("links each board to the feed with ?board=name", async () => {
    wrap(<Boards />);
    const link = await screen.findByRole("link", { name: /#general/ });
    expect(link).toHaveAttribute("href", "/?board=general");
  });
});
