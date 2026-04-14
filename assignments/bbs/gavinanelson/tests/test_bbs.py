import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import bbs_test_env


REPO_ROOT = Path(__file__).resolve().parents[1]
BBS_SCRIPT = REPO_ROOT / "bbs.py"


class BbsCliTests(unittest.TestCase):
    def run_bbs(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BBS_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_post_creates_bbs_json_and_prints_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs("post", "alice", "Hello, world!", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "Posted.\n")
            self.assertEqual(result.stderr, "")

            posts = json.loads((workdir / "bbs.json").read_text())
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["username"], "alice")
            self.assertEqual(posts[0]["message"], "Hello, world!")
            self.assertIn("timestamp", posts[0])

    def test_read_prints_all_messages_in_expected_display_format(self) -> None:
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
            (workdir / "bbs.json").write_text(json.dumps(payload))

            result = self.run_bbs("read", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout,
                "[2026-03-24 14:01] alice: Hello, is anyone out there?\n"
                "[2026-03-24 14:03] bob: Hey Alice! Welcome to the board.\n",
            )
            self.assertEqual(result.stderr, "")

    def test_users_prints_unique_usernames_in_first_seen_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            payload = [
                {
                    "username": "alice",
                    "message": "First post",
                    "timestamp": "2026-03-24T14:01:32",
                },
                {
                    "username": "bob",
                    "message": "Second post",
                    "timestamp": "2026-03-24T14:03:02",
                },
                {
                    "username": "alice",
                    "message": "Third post",
                    "timestamp": "2026-03-24T14:05:20",
                },
            ]
            (workdir / "bbs.json").write_text(json.dumps(payload))

            result = self.run_bbs("users", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "alice\nbob\n")
            self.assertEqual(result.stderr, "")

    def test_search_returns_only_matching_posts_case_insensitively(self) -> None:
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
                    "message": "I heard the hello from down the hall.",
                    "timestamp": "2026-03-24T14:03:02",
                },
                {
                    "username": "clara",
                    "message": "Goodbye for now.",
                    "timestamp": "2026-03-24T14:06:10",
                },
            ]
            (workdir / "bbs.json").write_text(json.dumps(payload))

            result = self.run_bbs("search", "hello", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout,
                "[2026-03-24 14:01] alice: Hello, is anyone out there?\n"
                "[2026-03-24 14:03] bob: I heard the hello from down the hall.\n",
            )
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
