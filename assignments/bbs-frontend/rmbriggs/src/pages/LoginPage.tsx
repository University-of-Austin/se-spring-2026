import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "@/api/client";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { ApiError } from "@/api/types";
import { formatDetail } from "@/api/types";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export default function LoginPage() {
  const { setUsername } = useCurrentUser();
  const navigate = useNavigate();
  const [createValue, setCreateValue] = useState("");
  const [switchValue, setSwitchValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canCreate = USERNAME_RE.test(createValue) && createValue.length >= 3 && createValue.length <= 20;
  const canSwitch = USERNAME_RE.test(switchValue) && switchValue.length >= 3 && switchValue.length <= 20;

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/users", { method: "POST", body: JSON.stringify({ username: createValue }) });
      setUsername(createValue);
      navigate("/");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  async function onSwitch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiFetch(`/users/${switchValue}`);
      setUsername(switchValue);
      navigate("/");
    } catch (e) {
      const err = e as ApiError;
      setError(formatDetail(err.detail));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto space-y-8">
      <section className="space-y-3">
        <h1 className="text-xl font-semibold">Sign in</h1>
        <p className="text-sm text-neutral-600">
          Switch to an existing username. Identity is just a header (X-Username) — not real auth.
        </p>
        <form onSubmit={onSwitch} className="space-y-2">
          <label htmlFor="switch" className="block text-sm font-medium">Username</label>
          <input
            id="switch"
            value={switchValue}
            onChange={(e) => setSwitchValue(e.target.value)}
            className="w-full border border-neutral-300 rounded px-3 py-2"
            placeholder="alice"
            autoFocus
          />
          <button type="submit" disabled={!canSwitch || busy} className="bg-neutral-900 text-white px-4 py-2 rounded disabled:opacity-50">
            Sign in
          </button>
        </form>
      </section>

      <section className="space-y-3 border-t border-neutral-200 pt-6">
        <h2 className="text-lg font-semibold">Create a new user</h2>
        <form onSubmit={onCreate} className="space-y-2">
          <label htmlFor="create" className="block text-sm font-medium">Username (3–20 chars, letters/digits/underscore)</label>
          <input
            id="create"
            value={createValue}
            onChange={(e) => setCreateValue(e.target.value)}
            className="w-full border border-neutral-300 rounded px-3 py-2"
            placeholder="newuser"
          />
          <button type="submit" disabled={!canCreate || busy} className="bg-neutral-900 text-white px-4 py-2 rounded disabled:opacity-50">
            Create
          </button>
        </form>
      </section>

      {error && (
        <div role="alert" className="border border-red-300 bg-red-50 text-red-900 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
