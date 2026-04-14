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


class MigrationCliTests(unittest.TestCase):
    def run_script(
        self, script: Path, *args: str, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_migrate_preserves_json_timeline_and_normalizes_rows(self) -> None:
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
                {
                    "username": "alice",
                    "message": "Glad to be here.",
                    "timestamp": "2026-03-24T14:04:15",
                },
            ]
            (workdir / "bbs.json").write_text(json.dumps(payload, indent=2) + "\n")

            json_read = self.run_script(BBS_SCRIPT, "read", cwd=workdir)
            migrate_result = self.run_script(MIGRATE_SCRIPT, cwd=workdir)
            sqlite_read = self.run_script(BBS_DB_SCRIPT, "read", cwd=workdir)

            self.assertEqual(json_read.returncode, 0)
            self.assertEqual(migrate_result.returncode, 0)
            self.assertEqual(sqlite_read.returncode, 0)
            self.assertEqual(sqlite_read.stdout, json_read.stdout)

            user_rows = fetch_all(
                workdir / "bbs.db",
                "SELECT username, joined_at, bio FROM users ORDER BY id ASC",
            )
            post_rows = fetch_all(
                workdir / "bbs.db",
                """
                SELECT u.username, p.message, p.timestamp, p.parent_post_id
                FROM posts p
                JOIN users u ON u.id = p.user_id
                ORDER BY p.id ASC
                """,
            )
            board_rows = fetch_all(
                workdir / "bbs.db", "SELECT slug FROM boards ORDER BY id ASC"
            )

            self.assertEqual(board_rows, [("general",)])
            self.assertEqual(
                user_rows,
                [
                    ("alice", "2026-03-24T14:01:32", ""),
                    ("bob", "2026-03-24T14:03:02", ""),
                ],
            )
            self.assertEqual(
                post_rows,
                [
                    ("alice", "Hello, is anyone out there?", "2026-03-24T14:01:32", None),
                    ("bob", "Hey Alice! Welcome to the board.", "2026-03-24T14:03:02", None),
                    ("alice", "Glad to be here.", "2026-03-24T14:04:15", None),
                ],
            )

    def test_migrate_refuses_to_overwrite_existing_database_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            (workdir / "bbs.json").write_text(
                json.dumps(
                    [
                        {
                            "username": "alice",
                            "message": "New data should not be imported",
                            "timestamp": "2026-03-24T14:01:32",
                        }
                    ]
                )
                + "\n"
            )

            seed_result = self.run_script(
                BBS_DB_SCRIPT, "post", "seed", "Existing row", cwd=workdir
            )
            migrate_result = self.run_script(MIGRATE_SCRIPT, cwd=workdir)

            self.assertEqual(seed_result.returncode, 0)
            self.assertEqual(migrate_result.returncode, 1)
            self.assertIn("bbs.db already contains data", migrate_result.stderr)

            counts = {
                table: fetch_scalar(workdir / "bbs.db", f"SELECT COUNT(*) FROM {table}")
                for table in ("users", "boards", "posts")
            }

            self.assertGreater(counts["posts"], 0)

    def test_migrate_allows_empty_seeded_database_with_only_general_board(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            payload = [
                {
                    "username": "alice",
                    "message": "Still migrates after a harmless read",
                    "timestamp": "2026-03-24T14:01:32",
                }
            ]
            (workdir / "bbs.json").write_text(json.dumps(payload, indent=2) + "\n")

            seed_result = self.run_script(BBS_DB_SCRIPT, "read", cwd=workdir)
            migrate_result = self.run_script(MIGRATE_SCRIPT, cwd=workdir)
            sqlite_read = self.run_script(BBS_DB_SCRIPT, "read", cwd=workdir)

            self.assertEqual(seed_result.returncode, 0)
            self.assertEqual(migrate_result.returncode, 0)
            self.assertEqual(sqlite_read.returncode, 0)
            self.assertEqual(
                sqlite_read.stdout,
                "[2026-03-24 14:01] alice: Still migrates after a harmless read\n",
            )


if __name__ == "__main__":
    unittest.main()
