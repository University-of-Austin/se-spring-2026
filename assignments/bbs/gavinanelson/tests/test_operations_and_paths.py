import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import bbs_test_env


REPO_ROOT = Path(__file__).resolve().parents[1]
BBS_DB_SCRIPT = REPO_ROOT / "bbs_db.py"


class OperationsAndPathsCliTests(unittest.TestCase):
    def run_bbs_db(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BBS_DB_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_init_pin_and_change_pin_complete_account_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            post_result = self.run_bbs_db("post", "alice", "Hello world", cwd=workdir)
            init_result = self.run_bbs_db("init-pin", "alice", "1234", cwd=workdir)
            change_result = self.run_bbs_db("change-pin", "alice", "1234", "5678", cwd=workdir)

            self.assertEqual(post_result.returncode, 0)
            self.assertEqual(init_result.returncode, 0)
            self.assertEqual(init_result.stdout, "PIN initialized.\n")
            self.assertEqual(change_result.returncode, 0)
            self.assertEqual(change_result.stdout, "PIN updated.\n")

    def test_export_json_writes_expected_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            export_path = workdir / "export.json"

            self.run_bbs_db("post", "alice", "Hello export", cwd=workdir)
            result = self.run_bbs_db("export-json", str(export_path), cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertIn(str(export_path), result.stdout)
            payload = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["username"], "alice")
            self.assertEqual(payload[0]["message"], "Hello export")

    def test_backup_copies_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            backup_path = workdir / "backup" / "bbs-copy.db"

            self.run_bbs_db("post", "alice", "Hello backup", cwd=workdir)
            result = self.run_bbs_db("backup", str(backup_path), cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertIn(str(backup_path), result.stdout)
            self.assertTrue(backup_path.exists())
            self.assertGreater(backup_path.stat().st_size, 0)

    def test_paths_reports_active_storage_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("paths", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Data directory: {workdir}", result.stdout)
            self.assertIn(str(workdir / "bbs.db"), result.stdout)
            self.assertIn(str(workdir / "bbs.json"), result.stdout)


    def test_uploads_dir_lives_inside_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            from unittest import mock
            with mock.patch.dict(os.environ, {"BBS_DATA_DIR": str(workdir)}):
                from app_paths import get_uploads_dir
                uploads = get_uploads_dir()
                self.assertEqual(uploads, workdir / "uploads")
                self.assertTrue(uploads.exists())


if __name__ == "__main__":
    unittest.main()
