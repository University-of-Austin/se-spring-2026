import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from bbs_db_format import format_threaded_posts
from tests.sqlalchemy_test_helper import fetch_all, fetch_scalar
from tests.support import bbs_test_env


REPO_ROOT = Path(__file__).resolve().parents[1]
BBS_DB_SCRIPT = REPO_ROOT / "bbs_db.py"


class BbsDbCliBronzeTests(unittest.TestCase):
    def run_bbs_db(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BBS_DB_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_post_creates_database_and_prints_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("post", "alice", "Hello from SQLite!", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "Posted.\n")
            self.assertEqual(result.stderr, "")
            self.assertTrue((workdir / "bbs.db").exists())

            rows = fetch_all(
                workdir / "bbs.db",
                """
                SELECT u.username, p.message
                FROM posts p
                JOIN users u ON u.id = p.user_id
                """,
            )

            self.assertEqual(rows, [("alice", "Hello from SQLite!")])

    def test_bronze_post_shape_stays_migration_friendly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            json_result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "bbs.py"), "post", "alice", "Hello from JSON"],
                cwd=workdir,
                env=bbs_test_env(workdir),
                capture_output=True,
                text=True,
                check=False,
            )
            sqlite_result = self.run_bbs_db("post", "alice", "Hello from SQLite", cwd=workdir)

            self.assertEqual(json_result.returncode, 0)
            self.assertEqual(json_result.stdout, "Posted.\n")
            self.assertEqual(json_result.stderr, "")
            json_path = workdir / "bbs.json"
            json_snapshot = json_path.read_text()
            json_posts = json.loads(json_snapshot)
            self.assertEqual(len(json_posts), 1)
            self.assertEqual(set(json_posts[0]), {"username", "message", "timestamp"})
            self.assertEqual(json_posts[0]["username"], "alice")
            self.assertEqual(json_posts[0]["message"], "Hello from JSON")
            datetime.fromisoformat(json_posts[0]["timestamp"])
            self.assertEqual(sqlite_result.returncode, 0)
            self.assertEqual(sqlite_result.stdout, "Posted.\n")
            self.assertEqual(sqlite_result.stderr, "")

            rows = fetch_all(
                workdir / "bbs.db",
                """
                SELECT u.username, p.message, p.timestamp
                FROM posts p
                JOIN users u ON u.id = p.user_id
                ORDER BY p.id ASC
                """,
            )
            post_count = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM posts")

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][:2], ("alice", "Hello from SQLite"))
            datetime.fromisoformat(rows[0][2])
            self.assertEqual(post_count, 1)
            self.assertEqual(json_path.read_text(), json_snapshot)

    def test_read_users_and_search_match_bronze_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "alice", "Hello, is anyone out there?", cwd=workdir)
            self.run_bbs_db(
                "post", "bob", "I heard the hello from down the hall.", cwd=workdir
            )

            read_result = self.run_bbs_db("read", cwd=workdir)
            users_result = self.run_bbs_db("users", cwd=workdir)
            search_result = self.run_bbs_db("search", "hello", cwd=workdir)

            self.assertEqual(read_result.returncode, 0)
            self.assertEqual(read_result.stderr, "")
            self.assertRegex(
                read_result.stdout,
                (
                    r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] alice: Hello, is anyone out there\?\n"
                    r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] bob: I heard the hello from down the hall\.\n$"
                ),
            )

            self.assertEqual(users_result.returncode, 0)
            self.assertEqual(users_result.stderr, "")
            self.assertEqual(users_result.stdout, "alice\nbob\n")

            self.assertEqual(search_result.returncode, 0)
            self.assertEqual(search_result.stderr, "")
            self.assertRegex(
                search_result.stdout,
                (
                    r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] alice: Hello, is anyone out there\?\n"
                    r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] bob: I heard the hello from down the hall\.\n$"
                ),
            )

    def test_users_preserves_first_seen_order_instead_of_sorting_alphabetically(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "zoe", "First post", cwd=workdir)
            self.run_bbs_db("post", "alice", "Second post", cwd=workdir)
            self.run_bbs_db("post", "mike", "Third post", cwd=workdir)

            result = self.run_bbs_db("users", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "zoe\nalice\nmike\n")
            self.assertEqual(result.stderr, "")

    def test_read_only_commands_seed_default_general_board_on_first_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            for command in (("read",), ("users",), ("search", "hello")):
                result = self.run_bbs_db(*command, cwd=workdir)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")

            board_rows = fetch_all(
                workdir / "bbs.db", "SELECT slug FROM boards ORDER BY id ASC"
            )
            user_rows = fetch_all(
                workdir / "bbs.db", "SELECT username FROM users ORDER BY id ASC"
            )
            post_rows = fetch_all(
                workdir / "bbs.db", "SELECT message FROM posts ORDER BY id ASC"
            )

            self.assertEqual(board_rows, [("general",)])
            self.assertEqual(user_rows, [])
            self.assertEqual(post_rows, [])

    def test_post_to_named_board_auto_creates_board_and_confirms_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db(
                "post",
                "alice",
                "Announcements",
                "Hello board!",
                cwd=workdir,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "Created board announcements.\nPosted.\n")
            self.assertEqual(result.stderr, "")

            boards_result = self.run_bbs_db("boards", cwd=workdir)

            self.assertEqual(boards_result.returncode, 0)
            self.assertEqual(boards_result.stdout, "announcements\ngeneral\n")
            self.assertEqual(boards_result.stderr, "")

    def test_read_returns_all_posts_across_boards_in_bronze_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            general_post = self.run_bbs_db("post", "alice", "Hello general", cwd=workdir)
            board_post = self.run_bbs_db(
                "post",
                "bob",
                "Announcements",
                "System update",
                cwd=workdir,
            )

            result = self.run_bbs_db("read", cwd=workdir)

            self.assertEqual(general_post.returncode, 0)
            self.assertEqual(general_post.stdout, "Posted.\n")
            self.assertEqual(general_post.stderr, "")

            self.assertEqual(board_post.returncode, 0)
            self.assertEqual(board_post.stdout, "Created board announcements.\nPosted.\n")
            self.assertEqual(board_post.stderr, "")

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn("alice: Hello general", result.stdout)
            self.assertIn("bob: System update", result.stdout)
            self.assertNotIn("(#1)", result.stdout)
            self.assertNotIn("(#2)", result.stdout)

    def test_create_board_reuses_normalized_slug_for_post_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            create_result = self.run_bbs_db("create-board", "Team Updates", cwd=workdir)
            post_result = self.run_bbs_db(
                "post",
                "alice",
                "TEAM UPDATES",
                "Off-topic thought",
                cwd=workdir,
            )
            read_result = self.run_bbs_db("read-board", "team-updates", cwd=workdir)

            self.assertEqual(create_result.returncode, 0)
            self.assertEqual(create_result.stdout, "Created board team-updates.\n")
            self.assertEqual(create_result.stderr, "")

            self.assertEqual(post_result.returncode, 0)
            self.assertEqual(post_result.stdout, "Posted.\n")
            self.assertEqual(post_result.stderr, "")

            self.assertEqual(read_result.returncode, 0)
            self.assertEqual(read_result.stderr, "")
            self.assertIn("alice: Off-topic thought", read_result.stdout)

    def test_create_board_general_reports_created_on_fresh_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("create-board", "general", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "Created board general.\n")
            self.assertEqual(result.stderr, "")

            board_rows = fetch_all(
                workdir / "bbs.db", "SELECT slug FROM boards ORDER BY id ASC"
            )

            self.assertEqual(board_rows, [("general",)])

    def test_create_board_rejects_whitespace_only_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("create-board", "   ", cwd=workdir)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("board name cannot be blank", result.stderr)

    def test_reply_inherits_parent_board_and_renders_indented_on_named_board(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "alice", "Announcements", "Original post", cwd=workdir)
            reply_result = self.run_bbs_db(
                "reply", "bob", "1", "Reply message", cwd=workdir
            )
            board_result = self.run_bbs_db("read-board", "announcements", cwd=workdir)
            default_result = self.run_bbs_db("read", cwd=workdir)

            self.assertEqual(reply_result.returncode, 0)
            self.assertEqual(reply_result.stdout, "Posted.\n")
            self.assertEqual(reply_result.stderr, "")

            self.assertEqual(board_result.returncode, 0)
            self.assertEqual(board_result.stderr, "")
            board_lines = board_result.stdout.splitlines()
            self.assertEqual(len(board_lines), 2)
            self.assertRegex(
                board_lines[0],
                r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#1\) alice: Original post$",
            )
            self.assertRegex(
                board_lines[1],
                r"^  \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#2\) bob: Reply message$",
            )

            self.assertEqual(default_result.returncode, 0)
            self.assertEqual(default_result.stderr, "")
            self.assertIn("alice: Original post", default_result.stdout)
            self.assertIn("bob: Reply message", default_result.stdout)
            self.assertNotIn("(#1)", default_result.stdout)
            self.assertNotIn("(#2)", default_result.stdout)

    def test_reply_to_missing_post_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("reply", "alice", "999", "No parent", cwd=workdir)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Post 999 does not exist.", result.stderr)

    def test_read_renders_reply_directly_under_parent_when_threads_are_interleaved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "alice", "Parent one", cwd=workdir)
            self.run_bbs_db("post", "carol", "Parent two", cwd=workdir)
            self.run_bbs_db("reply", "bob", "1", "Reply to parent one", cwd=workdir)

            result = self.run_bbs_db("read-board", "general", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 3)
            self.assertRegex(
                lines[0],
                r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#1\) alice: Parent one$",
            )
            self.assertRegex(
                lines[1],
                r"^  \[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#3\) bob: Reply to parent one$",
            )
            self.assertRegex(
                lines[2],
                r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#2\) carol: Parent two$",
            )

    def test_read_board_surfaces_post_ids_for_reply_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "alice", "Need an ID", cwd=workdir)

            result = self.run_bbs_db("read-board", "general", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertRegex(
                result.stdout,
                r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \(#1\) alice: Need an ID\n$",
            )

    def test_profile_shows_join_date_post_count_and_bio(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_bbs_db("post", "alice", "general", "First post", cwd=workdir)
            self.run_bbs_db("post", "alice", "random", "Second post", cwd=workdir)
            set_bio_result = self.run_bbs_db(
                "set-bio", "alice", "Building the board.", cwd=workdir
            )
            result = self.run_bbs_db("profile", "alice", cwd=workdir)

            self.assertEqual(set_bio_result.returncode, 0)
            self.assertEqual(set_bio_result.stdout, "Bio updated.\n")
            self.assertEqual(set_bio_result.stderr, "")

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn("Username: alice", result.stdout)
            self.assertRegex(result.stdout, r"Joined: \d{4}-\d{2}-\d{2} \d{2}:\d{2}")
            self.assertIn("Posts: 2", result.stdout)
            self.assertIn("Bio: Building the board.", result.stdout)

    def test_set_bio_for_unknown_user_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("set-bio", "ghost", "No profile", cwd=workdir)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("User ghost does not exist.", result.stderr)

    def test_profile_for_unknown_user_fails_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("profile", "ghost", cwd=workdir)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "User ghost does not exist.\n")

    def test_profile_escapes_bio_control_characters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            malicious_bio = "Line 1\nLine 2\x1b[31m\tDone"

            self.run_bbs_db("post", "alice", "general", "First post", cwd=workdir)
            set_bio_result = self.run_bbs_db("set-bio", "alice", malicious_bio, cwd=workdir)
            result = self.run_bbs_db("profile", "alice", cwd=workdir)

            self.assertEqual(set_bio_result.returncode, 0)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn(r"Bio: Line 1\nLine 2\x1b[31m\tDone", result.stdout)
            self.assertNotIn("Bio: Line 1\nLine 2", result.stdout)
            self.assertNotIn("\x1b", result.stdout)

    def test_format_threaded_posts_handles_deep_reply_chains_without_recursion(self) -> None:
        posts: list[dict[str, object]] = []
        for post_id in range(1, 1201):
            posts.append(
                {
                    "id": post_id,
                    "username": f"user{post_id}",
                    "message": f"message {post_id}",
                    "timestamp": "2026-04-08T16:00:00",
                    "parent_post_id": None if post_id == 1 else post_id - 1,
                }
            )

        lines = format_threaded_posts(posts)

        self.assertEqual(len(lines), 1200)
        self.assertEqual(lines[0], "[2026-04-08 16:00] (#1) user1: message 1")
        self.assertEqual(
            lines[-1],
            f"{'  ' * 1199}[2026-04-08 16:00] (#1200) user1200: message 1200",
        )


if __name__ == "__main__":
    unittest.main()
