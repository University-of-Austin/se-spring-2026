import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="py-12 text-center">
      <h1 className="text-xl font-semibold">Not found</h1>
      <p className="text-muted-foreground mt-2">That page doesn't exist.</p>
      <Link to="/" className="text-foreground underline mt-4 inline-block">Back to feed</Link>
    </div>
  );
}
