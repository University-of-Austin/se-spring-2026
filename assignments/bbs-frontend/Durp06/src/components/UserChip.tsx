import { Link } from 'react-router-dom';

interface Props {
  username: string;
}

export function UserChip({ username }: Props) {
  return (
    <Link to={`/users/${encodeURIComponent(username)}`} className="user-chip">
      @{username}
    </Link>
  );
}
