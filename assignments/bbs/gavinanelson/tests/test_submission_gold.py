from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from tests.sqlalchemy_test_helper import fetch_scalar
from tests.support import bbs_test_env, use_bbs_data_dir


REPO_ROOT = Path(__file__).resolve().parents[1]
BBS_DB_SCRIPT = REPO_ROOT / "bbs_db.py"
SEED_SCRIPT = REPO_ROOT / "seed_fake_data.py"


class _DataDirTestCase(unittest.TestCase):
    @contextmanager
    def use_workdir(self, workdir: Path):
        cwd = Path.cwd()
        with use_bbs_data_dir(workdir):
            os.chdir(workdir)
            try:
                yield
            finally:
                os.chdir(cwd)


class SubmissionGoldTests(_DataDirTestCase):
    def run_bbs_db(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(BBS_DB_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def run_seed(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SEED_SCRIPT), *args],
            cwd=cwd,
            env=bbs_test_env(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_paths_and_uploads_live_inside_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_bbs_db("paths", cwd=workdir)

            self.assertEqual(result.returncode, 0)
            self.assertIn(f"Data directory: {workdir}", result.stdout)
            self.assertIn(str(workdir / "bbs.db"), result.stdout)
            self.assertIn(str(workdir / "bbs.json"), result.stdout)

            with use_bbs_data_dir(workdir):
                from app_paths import get_uploads_dir

                uploads = get_uploads_dir()
                self.assertEqual(uploads, workdir / "uploads")
                self.assertTrue(uploads.exists())

    def test_pin_lifecycle_and_export_json_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            export_path = workdir / "export.json"

            post_result = self.run_bbs_db("post", "alice", "Hello world", cwd=workdir)
            init_result = self.run_bbs_db("init-pin", "alice", "1234", cwd=workdir)
            change_result = self.run_bbs_db("change-pin", "alice", "1234", "5678", cwd=workdir)
            export_result = self.run_bbs_db("export-json", str(export_path), cwd=workdir)

            self.assertEqual(post_result.returncode, 0)
            self.assertEqual(init_result.returncode, 0)
            self.assertEqual(change_result.returncode, 0)
            self.assertEqual(export_result.returncode, 0)
            self.assertEqual(init_result.stdout, "PIN initialized.\n")
            self.assertEqual(change_result.stdout, "PIN updated.\n")
            self.assertTrue(export_path.exists())

            payload = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["username"], "alice")

    def test_seed_creates_requested_dataset_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            result = self.run_seed(
                "--users",
                "12",
                "--posts",
                "40",
                "--boards",
                "4",
                "--replies",
                "10",
                "--seed",
                "7",
                cwd=workdir,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("Seeded", result.stdout)
            self.assertEqual(fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM users"), 12)
            self.assertEqual(fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM boards"), 4)
            self.assertEqual(fetch_scalar(workdir / "bbs.db", "SELECT COUNT(*) FROM posts"), 40)
            self.assertEqual(
                fetch_scalar(
                    workdir / "bbs.db",
                    "SELECT COUNT(*) FROM posts WHERE parent_post_id IS NOT NULL",
                ),
                10,
            )

    def test_sqlite_attachment_storage_marks_post_and_copies_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                from app_paths import get_uploads_dir
                from bbs_db_store import get_attachment, store_attachment
                from bbs_tui_backend import SqliteBackend

                backend = SqliteBackend()
                backend.post("alice", "general", "Check this out")
                post = backend.read_posts("general")[-1]

                img_path = workdir / "photo.png"
                img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake image data")

                attachment_hash = store_attachment(post.id, str(img_path))
                attachment = get_attachment(post.id)
                reread = backend.read_posts("general")[-1]

                self.assertEqual(len(attachment_hash), 16)
                self.assertIsNotNone(attachment)
                self.assertEqual(attachment["original_name"], "photo.png")
                self.assertTrue(reread.has_attachment)
                self.assertTrue((get_uploads_dir() / f"{attachment_hash}.png").exists())

    def test_textual_app_starts_in_json_mode(self) -> None:
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            async with app.run_test(size=(120, 40)):
                self.assertEqual(app.section, "timeline")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
