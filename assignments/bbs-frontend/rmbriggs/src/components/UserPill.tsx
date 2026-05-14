import { Link } from "react-router-dom";

export default function UserPill({ username }: { username: string }) {
  if (username === "[deleted]") {
    return <span className="text-neutral-500 italic">[deleted]</span>;
  }
  return (
    <Link to={`/users/${username}`} className="font-medium text-neutral-900 hover:underline">
      {username}
    </Link>
  );
}
