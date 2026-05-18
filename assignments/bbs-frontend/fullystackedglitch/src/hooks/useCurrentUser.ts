import { useSyncExternalStore } from "react";
import { getStoredUsername, subscribeUsername } from "../lib/storage";

// useSyncExternalStore keeps every consumer in sync when the active username
// changes (header dropdown, sign-in form, etc) without prop-drilling.
export function useCurrentUser(): string | null {
  return useSyncExternalStore(
    subscribeUsername,
    getStoredUsername,
    () => null,
  );
}
