// Loadable is the single chokepoint that enforces the assignment's
// "every fetch shows loading + error" rule.  These tests pin down
// its four branches.

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Loadable } from "./Loadable";
import { ApiError } from "../api/client";

describe("<Loadable>", () => {
  it("renders the spinner while loading and no data", () => {
    render(
      <Loadable state={{ data: null, loading: true, error: null, refetch: () => {} }}>
        {() => <span>never</span>}
      </Loadable>,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
  });

  it("renders the error detail and a retry button when error.status !== 404", async () => {
    const refetch = vi.fn();
    render(
      <Loadable
        state={{
          data: null,
          loading: false,
          error: new ApiError(500, "Server exploded"),
          refetch,
        }}
      >
        {() => <span>never</span>}
      </Loadable>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Server exploded");
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders the notFoundView when error.status === 404", () => {
    render(
      <Loadable
        state={{
          data: null,
          loading: false,
          error: new ApiError(404, "not found"),
          refetch: () => {},
        }}
        notFoundView={<div>custom 404</div>}
      >
        {() => <span>never</span>}
      </Loadable>,
    );

    expect(screen.getByText("custom 404")).toBeInTheDocument();
  });

  it("renders the empty message when data is an empty array", () => {
    render(
      <Loadable
        state={{ data: [], loading: false, error: null, refetch: () => {} }}
        emptyMessage="nothing here"
      >
        {() => <span>never</span>}
      </Loadable>,
    );

    expect(screen.getByText("nothing here")).toBeInTheDocument();
  });

  it("renders children with the data on success", () => {
    render(
      <Loadable
        state={{ data: [1, 2, 3], loading: false, error: null, refetch: () => {} }}
      >
        {(nums) => <span>sum:{nums.reduce((a, b) => a + b, 0)}</span>}
      </Loadable>,
    );

    expect(screen.getByText("sum:6")).toBeInTheDocument();
  });
});
