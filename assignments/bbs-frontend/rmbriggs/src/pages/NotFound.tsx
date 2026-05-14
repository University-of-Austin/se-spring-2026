import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="py-12 text-center">
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="text-neutral-600 mt-2">That page doesn't exist.</p>
      <Link to="/" className="text-neutral-900 underline mt-4 inline-block">Back to feed</Link>
    </div>
  );
}
