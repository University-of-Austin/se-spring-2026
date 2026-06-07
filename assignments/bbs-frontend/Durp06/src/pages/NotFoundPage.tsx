import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <section className="page page--notfound">
      <h1>Not found</h1>
      <p className="empty">That page doesn't exist.</p>
      <Link to="/" className="btn">
        Back to feed
      </Link>
    </section>
  );
}
