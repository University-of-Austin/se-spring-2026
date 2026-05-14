import { Link } from "react-router-dom";

export default function UserPill({ username }: { username: string }) {
  if (username === "[deleted]") {
    return <span className="text-muted-foreground italic">[deleted]</span>;
  }
  return (
    <Link to={`/users/${username}`} className="font-medium text-foreground hover:underline">
      {username}
    </Link>
  );
}
