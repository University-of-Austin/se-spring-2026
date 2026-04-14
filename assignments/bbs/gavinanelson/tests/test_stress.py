"""Stress tests for the BBS system.

Tests how the system handles large datasets — many boards, many posts,
search performance at scale. Each test seeds data via the backend API,
then exercises read/search operations.
"""

import os
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

from bbs_tui_backend import SqliteBackend
from tests.support import use_bbs_data_dir


@contextmanager
def _workdir():
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        with use_bbs_data_dir(workdir):
            os.chdir(workdir)
            try:
                yield workdir
            finally:
                os.chdir(cwd)


def _seed(backend: SqliteBackend, *, users: int, boards: int, posts_per_board: int, replies_per_board: int = 0) -> None:
    """Seed a backend with data using the post/reply API for correctness."""
    board_names = [f"board-{i}" if i > 0 else "general" for i in range(boards)]

    # Create boards by posting one message to each
    for i, board in enumerate(board_names):
        username = f"user-{i % users}"
        backend.post(username, board, f"First post in {board}")

    # Fill remaining posts per board
    for board_idx, board in enumerate(board_names):
        for j in range(1, posts_per_board):  # already posted 1
            username = f"user-{(board_idx * posts_per_board + j) % users}"
            backend.post(username, board, f"Post {j} in {board} about topic-{j % 50}")

    # Add replies
    if replies_per_board > 0:
        for board in board_names:
            posts = backend.read_posts(board)
            for j in range(min(replies_per_board, len(posts))):
                username = f"user-{j % users}"
                backend.reply(username, posts[j].id, f"Reply {j} to post in {board}")


def _seed_fast(backend: SqliteBackend, *, users: int, boards: int, posts_per_board: int) -> None:
    """Seed using direct SQL for speed at large scale. No replies."""
    import random as random_mod
    from db import engine, init_db
    from sqlalchemy import text
    from datetime import datetime, timedelta
    from seed_fake_data import generate_message, generate_reply_message

    rng = random_mod.Random(42)
    init_db()
    base_time = datetime(2026, 3, 24, 14, 0, 0)

    board_names = [f"board-{i}" if i > 0 else "general" for i in range(boards)]

    with engine.begin() as conn:
        for i in range(users):
            conn.execute(text(
                "INSERT OR IGNORE INTO users (username, joined_at, bio) VALUES (:u, :j, :b)"
            ), {"u": f"user-{i}", "j": base_time.isoformat(), "b": f"User {i} bio"})

        for i, board in enumerate(board_names):
            conn.execute(text(
                "INSERT OR IGNORE INTO boards (slug, name, created_at) VALUES (:s, :n, :c)"
            ), {"s": board, "n": board, "c": base_time.isoformat()})

        user_ids = {}
        for row in conn.execute(text("SELECT id, username FROM users")):
            user_ids[row[1]] = row[0]

        board_ids = {}
        for row in conn.execute(text("SELECT id, slug FROM boards")):
            board_ids[row[1]] = row[0]

        batch = []
        post_id = 0
        for board in board_names:
            for j in range(posts_per_board):
                post_id += 1
                username = f"user-{(post_id - 1) % users}"
                batch.append({
                    "uid": user_ids[username],
                    "bid": board_ids[board],
                    "msg": generate_message(rng),
                    "ts": (base_time + timedelta(minutes=post_id)).isoformat(timespec="seconds"),
                })
                if len(batch) >= 5000:
                    conn.execute(text(
                        "INSERT INTO posts (user_id, board_id, message, timestamp) VALUES (:uid, :bid, :msg, :ts)"
                    ), batch)
                    batch = []
        if batch:
            conn.execute(text(
                "INSERT INTO posts (user_id, board_id, message, timestamp) VALUES (:uid, :bid, :msg, :ts)"
            ), batch)


class StressBoardCount(unittest.TestCase):
    """Test handling large numbers of boards."""

    def test_50_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed(backend, users=10, boards=50, posts_per_board=2)
            boards = backend.list_boards()
            self.assertEqual(len(boards), 50)

    def test_200_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed(backend, users=10, boards=200, posts_per_board=1)
            boards = backend.list_boards()
            self.assertEqual(len(boards), 200)


class StressPostCount(unittest.TestCase):
    """Test handling large numbers of posts."""

    def test_1000_posts_single_board(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=20, boards=1, posts_per_board=1000)
            posts = backend.read_posts("general")
            self.assertEqual(len(posts), 1000)

    def test_5000_posts_across_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=30, boards=10, posts_per_board=500)
            total = 0
            for board in backend.list_boards():
                total += len(backend.read_posts(board))
            self.assertEqual(total, 5000)

    def test_10000_posts_single_board(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=50, boards=1, posts_per_board=10000)
            posts = backend.read_posts("general")
            self.assertEqual(len(posts), 10000)


class StressSearchPerformance(unittest.TestCase):
    """Measure search speed at different scales."""

    def _time_search(self, backend: SqliteBackend, keyword: str) -> tuple[float, int]:
        start = time.perf_counter()
        results = backend.search_posts(keyword)
        elapsed = time.perf_counter() - start
        return elapsed, len(results)

    def test_search_1000_posts_under_100ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=20, boards=3, posts_per_board=334)
            elapsed, count = self._time_search(backend, "pipeline")
            self.assertGreater(count, 0, "Search should find results")
            self.assertLess(elapsed, 0.1, f"Search took {elapsed:.3f}s, expected < 0.1s")

    def test_search_10000_posts_under_500ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=50, boards=5, posts_per_board=2000)
            elapsed, count = self._time_search(backend, "debugging")
            self.assertGreater(count, 0, "Search should find results")
            self.assertLess(elapsed, 0.5, f"Search took {elapsed:.3f}s, expected < 0.5s")

    def test_search_50000_posts_under_2s(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=50, boards=10, posts_per_board=5000)
            elapsed, count = self._time_search(backend, "migration")
            self.assertGreater(count, 0, "Search should find results")
            self.assertLess(elapsed, 2.0, f"Search took {elapsed:.3f}s, expected < 2.0s")

    def test_search_users_500_under_500ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=500, boards=1, posts_per_board=1)
            start = time.perf_counter()
            results = backend.search_users("user-1")
            elapsed = time.perf_counter() - start
            self.assertGreater(len(results), 0, "Should find users matching 'user-1'")
            self.assertLess(elapsed, 0.5, f"User search took {elapsed:.3f}s, expected < 0.5s")


class StressReadPerformance(unittest.TestCase):
    """Measure read speed at different scales."""

    def test_read_1000_posts_under_100ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=20, boards=1, posts_per_board=1000)
            start = time.perf_counter()
            posts = backend.read_posts("general")
            elapsed = time.perf_counter() - start
            self.assertEqual(len(posts), 1000)
            self.assertLess(elapsed, 0.1, f"Read took {elapsed:.3f}s, expected < 0.1s")

    def test_read_10000_posts_under_500ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=50, boards=1, posts_per_board=10000)
            start = time.perf_counter()
            posts = backend.read_posts("general")
            elapsed = time.perf_counter() - start
            self.assertEqual(len(posts), 10000)
            self.assertLess(elapsed, 0.5, f"Read took {elapsed:.3f}s, expected < 0.5s")

    def test_list_200_boards_under_50ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=5, boards=200, posts_per_board=1)
            start = time.perf_counter()
            boards = backend.list_boards()
            elapsed = time.perf_counter() - start
            self.assertEqual(len(boards), 200)
            self.assertLess(elapsed, 0.05, f"List boards took {elapsed:.3f}s, expected < 0.05s")

    def test_profile_with_5000_posts_under_500ms(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=1, boards=1, posts_per_board=5000)
            users = backend.list_users()
            self.assertTrue(len(users) > 0)
            username = users[0]
            start = time.perf_counter()
            profile = backend.get_profile(username)
            user_posts = backend.get_user_posts(username)
            elapsed = time.perf_counter() - start
            self.assertIsNotNone(profile)
            self.assertGreater(len(user_posts), 0)
            self.assertLess(elapsed, 0.5, f"Profile load took {elapsed:.3f}s, expected < 0.5s")


class StressHighScale(unittest.TestCase):
    """Push the system to higher limits."""

    def test_100000_posts_read(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=100, boards=1, posts_per_board=100000)
            start = time.perf_counter()
            posts = backend.read_posts("general")
            elapsed = time.perf_counter() - start
            self.assertEqual(len(posts), 100000)
            print(f"\n  100k posts read: {elapsed:.3f}s")
            self.assertLess(elapsed, 5.0, f"100k read took {elapsed:.3f}s")

    def test_100000_posts_search(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=100, boards=1, posts_per_board=100000)
            start = time.perf_counter()
            results = backend.search_posts("authentication")
            elapsed = time.perf_counter() - start
            print(f"\n  100k posts search: {elapsed:.3f}s, {len(results)} results")
            self.assertGreater(len(results), 0)
            self.assertLess(elapsed, 5.0, f"100k search took {elapsed:.3f}s")

    def test_500_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=10, boards=500, posts_per_board=1)
            start = time.perf_counter()
            boards = backend.list_boards()
            elapsed = time.perf_counter() - start
            self.assertEqual(len(boards), 500)
            print(f"\n  500 boards list: {elapsed:.3f}s")
            self.assertLess(elapsed, 0.1, f"500 boards took {elapsed:.3f}s")

    def test_100000_posts_across_100_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=100, boards=100, posts_per_board=1000)
            total = 0
            start = time.perf_counter()
            for board in backend.list_boards():
                total += len(backend.read_posts(board))
            elapsed = time.perf_counter() - start
            self.assertEqual(total, 100000)
            print(f"\n  100k posts across 100 boards: {elapsed:.3f}s")
            self.assertLess(elapsed, 10.0, f"Full read took {elapsed:.3f}s")


class StressMillionMessages(unittest.TestCase):
    """The million message test. Can the system handle it?"""

    def test_1000000_posts_search(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=200, boards=50, posts_per_board=20000)
            # Total: 1,000,000 posts across 50 boards

            start = time.perf_counter()
            results = backend.search_posts("authentication")
            search_time = time.perf_counter() - start
            print(f"\n  1M posts search: {search_time:.3f}s, {len(results)} results")
            self.assertGreater(len(results), 0)
            self.assertLess(search_time, 30.0, f"1M search took {search_time:.3f}s")

    def test_1000000_posts_read_single_board(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            # 20k posts per board, read one board
            _seed_fast(backend, users=200, boards=50, posts_per_board=20000)

            start = time.perf_counter()
            posts = backend.read_posts("general")
            read_time = time.perf_counter() - start
            self.assertEqual(len(posts), 20000)
            print(f"\n  1M total, read 20k from one board: {read_time:.3f}s")
            self.assertLess(read_time, 5.0, f"Board read took {read_time:.3f}s")

    def test_1000000_posts_list_boards(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=200, boards=50, posts_per_board=20000)

            start = time.perf_counter()
            boards = backend.list_boards()
            elapsed = time.perf_counter() - start
            self.assertEqual(len(boards), 50)
            print(f"\n  1M total, list 50 boards: {elapsed:.3f}s")
            self.assertLess(elapsed, 1.0, f"Board list took {elapsed:.3f}s")

    def test_1000000_posts_user_profile(self) -> None:
        with _workdir():
            backend = SqliteBackend()
            _seed_fast(backend, users=200, boards=50, posts_per_board=20000)

            users = backend.list_users()
            username = users[0]
            start = time.perf_counter()
            profile = backend.get_profile(username)
            user_posts = backend.get_user_posts(username)
            elapsed = time.perf_counter() - start
            self.assertIsNotNone(profile)
            print(f"\n  1M total, profile for {username}: {elapsed:.3f}s, {len(user_posts)} posts")
            self.assertLess(elapsed, 10.0, f"Profile took {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
