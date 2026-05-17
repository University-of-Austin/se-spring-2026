import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { useCurrentUser } from "../src/hooks/useCurrentUser";

function Probe() {
  const { currentUser, setCurrentUser } = useCurrentUser();
  return (
    <div>
      <span data-testid="who">{currentUser ?? "(none)"}</span>
      <button onClick={() => setCurrentUser("alice")}>set</button>
      <button onClick={() => setCurrentUser(null)}>clear</button>
    </div>
  );
}

describe("useCurrentUser", () => {
  it("starts as null when localStorage has no entry", () => {
    render(<Probe />);
    expect(screen.getByTestId("who").textContent).toBe("(none)");
  });

  it("persists the username across re-mounts via localStorage", async () => {
    const user = userEvent.setup();
    const { unmount } = render(<Probe />);
    await user.click(screen.getByText("set"));
    expect(screen.getByTestId("who").textContent).toBe("alice");
    unmount();

    render(<Probe />);
    expect(screen.getByTestId("who").textContent).toBe("alice");
  });

  it("clears the storage entry when set to null", async () => {
    const user = userEvent.setup();
    render(<Probe />);
    await user.click(screen.getByText("set"));
    expect(localStorage.getItem("bbs:current-username")).toBe("alice");
    await user.click(screen.getByText("clear"));
    expect(localStorage.getItem("bbs:current-username")).toBeNull();
  });

  it("reflects external storage changes from other tabs", () => {
    render(<Probe />);
    act(() => {
      // Simulate a 'storage' event fired by another tab.
      localStorage.setItem("bbs:current-username", "from-other-tab");
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: "bbs:current-username",
          newValue: "from-other-tab",
        }),
      );
    });
    expect(screen.getByTestId("who").textContent).toBe("from-other-tab");
  });
});
