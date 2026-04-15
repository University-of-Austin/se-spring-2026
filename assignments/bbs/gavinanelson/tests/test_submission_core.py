from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.sqlalchemy_test_helper import fetch_all, fetch_scalar
from tests.support import bbs_test_env


REPO_ROOT = Path(__file__).resolve().parents[1]
BBS_SCRIPT = REPO_ROOT / "bbs.py"
BBS_DB_SCRIPT = REPO_ROOT / "bbs_db.py"
MIGRATE_SCRIPT = REPO_ROOT / "migrate.py"


class SubmissionCoreTests(unittest.TestCase):
    def run_script(self, script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_json_cli_post_read_users_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            post_a = self.run_script(BBS_SCRIPT, "post", "alice", "Hello, world!", cwd=workdir)
            post_b = self.run_script(BBS_SCRIPT, "post", "bob", "I heard the hello too.", cwd=workdir)
            read_result = self.run_script(BBS_SCRIPT, "read", cwd=workdir)
            users_result = self.run_script(BBS_SCRIPT, "users", cwd=workdir)
            search_result = self.run_script(BBS_SCRIPT, "search", "hello", cwd=workdir)

            self.assertEqual(post_a.returncode, 0)
            self.assertEqual(post_b.returncode, 0)
            self.assertEqual(read_result.returncode, 0)
            self.assertEqual(users_result.returncode, 0)
            self.assertEqual(search_result.returncode, 0)
            self.assertEqual(users_result.stdout, "alice\nbob\n")
            self.assertIn("alice: Hello, world!", read_result.stdout)
            self.assertIn("bob: I heard the hello too.", read_result.stdout)
            self.assertIn("alice: Hello, world!", search_result.stdout)
            self.assertIn("bob: I heard the hello too.", search_result.stdout)

            payload = json.loads((workdir / "bbs.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 2)
            self.assertEqual(set(payload[0]), {"username", "message", "timestamp"})

    def test_sqlite_cli_covers_core_and_silver_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            post_general = self.run_script(BBS_DB_SCRIPT, "post", "alice", "Hello from SQLite", cwd=workdir)
            post_board = self.run_script(BBS_DB_SCRIPT, "post", "alice", "announcements", "Board post", cwd=workdir)
            reply_result = self.run_script(BBS_DB_SCRIPT, "reply", "bob", "2", "Replying in thread", cwd=workdir)
            bio_result = self.run_script(BBS_DB_SCRIPT, "set-bio", "alice", "Building the board.", cwd=workdir)
            read_result = self.run_script(BBS_DB_SCRIPT, "read", cwd=workdir)
            board_result = self.run_script(BBS_DB_SCRIPT, "read-board", "announcements", cwd=workdir)
            profile_result = self.run_script(BBS_DB_SCRIPT, "profile", "alice", cwd=workdir)
            users_result = self.run_script(BBS_DB_SCRIPT, "users", cwd=workdir)
            search_result = self.run_script(BBS_DB_SCRIPT, "search", "hello", cwd=workdir)

            for result in (
                post_general,
                post_board,
                reply_result,
                bio_result,
                read_result,
                board_result,
                profile_result,
                users_result,
                search_result,
            ):
                self.assertEqual(result.returncode, 0, msg=result.stderr)

            self.assertIn("alice\nbob\n", users_result.stdout)
            self.assertIn("alice: Hello from SQLite", read_result.stdout)
            self.assertIn("(#2) alice: Board post", board_result.stdout)
            self.assertIn("(#3) bob: Replying in thread", board_result.stdout)
            self.assertIn("Username: alice", profile_result.stdout)
            self.assertIn("Posts: 2", profile_result.stdout)
            self.assertIn("Bio: Building the board.", profile_result.stdout)
            self.assertIn("alice: Hello from SQLite", search_result.stdout)

            posts = fetch_all(
                workdir / "bbs.db",
                """
                SELECT u.username, b.slug, p.message, p.parent_post_id
                FROM posts p
                JOIN users u ON u.id = p.user_id
                JOIN boards b ON b.id = p.board_id
                ORDER BY p.id ASC
                """,
            )
            self.assertEqual(
                posts,
                [
                    ("alice", "general", "Hello from SQLite", None),
                    ("alice", "announcements", "Board post", None),
                    ("bob", "announcements", "Replying in thread", 2),
                ],
            )

    def test_migration_preserves_timeline_and_refuses_existing_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            payload = [
                {
                    "username": "alice",
                    "message": "Hello, is anyone out there?",
                    "timestamp": "2026-03-24T14:01:32",
                },
                {
                    "username": "bob",
                    "message": "Hey Alice! Welcome to the board.",
                    "timestamp": "2026-03-24T14:03:02",
                },
            ]
            (workdir / "bbs.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            json_read = self.run_script(BBS_SCRIPT, "read", cwd=workdir)
            migrate_result = self.run_script(MIGRATE_SCRIPT, cwd=workdir)
            sqlite_read = self.run_script(BBS_DB_SCRIPT, "read", cwd=workdir)
            second_migrate = self.run_script(MIGRATE_SCRIPT, cwd=workdir)

            self.assertEqual(json_read.returncode, 0)
            self.assertEqual(migrate_result.returncode, 0)
            self.assertEqual(sqlite_read.returncode, 0)
            self.assertEqual(sqlite_read.stdout, json_read.stdout)
            self.assertNotEqual(second_migrate.returncode, 0)
            self.assertIn("bbs.db already contains data", second_migrate.stderr)

            users = fetch_all(
                workdir / "bbs.db",
                "SELECT username FROM users ORDER BY id ASC",
            )
            boards = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM boards")
            posts = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM posts")

            self.assertEqual(users, [("alice",), ("bob",)])
            self.assertEqual(boards, 1)
            self.assertEqual(posts, 2)


if __name__ == "__main__":
    unittest.main()
