import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bbs_tui_backend import SqliteBackend
from tests.sqlalchemy_test_helper import fetch_scalar
from tests.support import bbs_test_env, use_bbs_data_dir


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_SCRIPT = REPO_ROOT / "seed_fake_data.py"


class SeedFakeDataCliTests(unittest.TestCase):
    def run_seed(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SEED_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_seed_creates_requested_dataset_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_seed(
                "--users", "12",
                "--posts", "40",
                "--boards", "4",
                "--replies", "10",
                "--seed", "7",
                cwd=workdir,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Seeded", result.stdout)
            self.assertEqual(result.stderr, "")

            users = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM users")
            boards = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM boards")
            posts = fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM posts")
            replies = fetch_scalar(
                workdir / "bbs.db",
                "SELECT COUNT(*) FROM posts WHERE parent_post_id IS NOT NULL",
            )

            self.assertEqual(users, 12)
            self.assertEqual(boards, 4)
            self.assertEqual(posts, 40)
            self.assertEqual(replies, 10)

    def test_seed_refuses_to_overwrite_existing_data_without_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            first = self.run_seed("--users", "4", "--posts", "12", cwd=workdir)
            second = self.run_seed("--users", "6", "--posts", "20", cwd=workdir)

            self.assertEqual(first.returncode, 0)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("bbs.db already contains data", second.stderr)

    def test_seed_reset_replaces_existing_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            self.run_seed("--users", "4", "--posts", "12", cwd=workdir)
            result = self.run_seed(
                "--reset",
                "--users", "8",
                "--posts", "30",
                "--boards", "3",
                "--replies", "5",
                cwd=workdir,
            )

            self.assertEqual(result.returncode, 0)

            counts = {
                table: fetch_scalar(workdir / "bbs.db", f"SELECT COUNT(*) FROM {table}")
                for table in ("users", "boards", "posts")
            }
            replies = fetch_scalar(
                workdir / "bbs.db",
                "SELECT COUNT(*) FROM posts WHERE parent_post_id IS NOT NULL",
            )

            self.assertEqual(counts["users"], 8)
            self.assertEqual(counts["boards"], 3)
            self.assertEqual(counts["posts"], 30)
            self.assertEqual(replies, 5)

    def test_seed_large_dataset_supports_backend_reads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_seed(
                "--users", "80",
                "--posts", "1500",
                "--boards", "8",
                "--replies", "300",
                "--seed", "99",
                cwd=workdir,
            )

            self.assertEqual(result.returncode, 0)

            cwd = Path.cwd()
            try:
                # SQLite engine path is process-relative, so run the backend in the seeded cwd.
                import os
                with use_bbs_data_dir(workdir):
                    os.chdir(workdir)
                    backend = SqliteBackend()
                    boards = backend.list_boards()
                    timeline = backend.read_posts("general")
                    users = backend.list_users()
                    search_results = backend.search_posts("project")
            finally:
                os.chdir(cwd)

            self.assertEqual(len(boards), 8)
            self.assertGreaterEqual(len(timeline), 1)
            self.assertEqual(len(users), 80)
            self.assertGreaterEqual(len(search_results), 1)

    def test_sqlite_backend_follows_current_working_directory_after_prior_use(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmpdir, tempfile.TemporaryDirectory() as second_tmpdir:
            first_workdir = Path(first_tmpdir)
            second_workdir = Path(second_tmpdir)
            cwd = Path.cwd()

            try:
                with use_bbs_data_dir(first_workdir):
                    os.chdir(first_workdir)
                    warm_backend = SqliteBackend()
                    warm_backend.post("alice", "general", "Warm cache")

                result = self.run_seed(
                    "--users", "16",
                    "--posts", "60",
                    "--boards", "5",
                    "--replies", "12",
                    "--seed", "17",
                    cwd=second_workdir,
                )
                self.assertEqual(result.returncode, 0)

                with use_bbs_data_dir(second_workdir):
                    os.chdir(second_workdir)
                    backend = SqliteBackend()
                    boards = backend.list_boards()
                    users = backend.list_users()
            finally:
                os.chdir(cwd)

            self.assertEqual(len(boards), 5)
            self.assertEqual(len(users), 16)


if __name__ == "__main__":
    unittest.main()
