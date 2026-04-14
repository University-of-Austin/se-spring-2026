import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import bbs
import bbs_db_format
import bbs_tui_backend
import db
from app_paths import get_backups_dir, get_data_dir, get_db_path, get_exports_dir, get_json_path
from tests.support import use_bbs_data_dir


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


class SecurityAndRuntimeTests(_DataDirTestCase):
    def test_create_user_stores_hashed_pin_and_marks_account_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                from bbs_db_store import create_user, get_profile, get_user_auth_state, verify_user

                created = create_user("alice", "1234")
                profile = get_profile("alice")
                state = get_user_auth_state("alice")
                verified = verify_user("alice", "1234")

                with db.engine.connect() as connection:
                    row = connection.execute(
                        text("SELECT pin, pin_hash, pin_needs_reset FROM users WHERE username = :username"),
                        {"username": "alice"},
                    ).fetchone()
        self.assertTrue(created)
        self.assertIsNotNone(profile)
        self.assertEqual(state, "ready")
        self.assertTrue(verified)
        self.assertEqual(row.pin, "")
        self.assertNotEqual(row.pin_hash, "")
        self.assertNotEqual(row.pin_hash, "1234")
        self.assertEqual(row.pin_needs_reset, 0)

    def test_auto_created_account_requires_pin_setup_until_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                from bbs_db_store import (
                    create_post,
                    get_user_auth_state,
                    set_initial_pin,
                    verify_user,
                )

                create_post("alice", "hello from general")
                before_state = get_user_auth_state("alice")
                before_verify = verify_user("alice", "1234")
                set_initial_pin("alice", "1234")
                after_state = get_user_auth_state("alice")
                after_verify = verify_user("alice", "1234")
        self.assertEqual(before_state, "setup_required")
        self.assertFalse(before_verify)
        self.assertEqual(after_state, "ready")
        self.assertTrue(after_verify)

    def test_verify_user_upgrades_legacy_plaintext_pin_to_hashed_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                db.init_db()
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            """
                            INSERT INTO users (username, joined_at, bio, pin, pin_hash, pin_needs_reset)
                            VALUES (:username, :joined_at, :bio, :pin, :pin_hash, :pin_needs_reset)
                            """
                        ),
                        {
                            "username": "legacy",
                            "joined_at": "2026-04-01T10:00:00",
                            "bio": "",
                            "pin": "4321",
                            "pin_hash": "",
                            "pin_needs_reset": 0,
                        },
                    )

                from bbs_db_store import verify_user

                verified = verify_user("legacy", "4321")
                with db.engine.connect() as connection:
                    row = connection.execute(
                        text("SELECT pin, pin_hash FROM users WHERE username = :username"),
                        {"username": "legacy"},
                    ).fetchone()
        self.assertTrue(verified)
        self.assertEqual(row.pin, "")
        self.assertNotEqual(row.pin_hash, "")
        self.assertNotEqual(row.pin_hash, "4321")

    def test_sqlite_enforces_foreign_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                db.init_db()
                with self.assertRaises(IntegrityError):
                    with db.engine.begin() as connection:
                        connection.execute(
                            text(
                                """
                                INSERT INTO posts (user_id, board_id, parent_post_id, message, timestamp)
                                VALUES (999, 999, NULL, 'bad row', '2026-04-01T10:00:00')
                                """
                            )
                        )
    def test_cli_formatters_escape_control_characters(self) -> None:
        post = {
            "username": "ali\x1bce",
            "message": "line 1\nline 2\tboom",
            "timestamp": "2026-04-08T18:55:09",
        }

        json_rendered = bbs.format_post(post)
        sqlite_rendered = bbs_db_format.format_post(post)

        self.assertIn(r"ali\x1bce", json_rendered)
        self.assertIn(r"line 1\nline 2\tboom", json_rendered)
        self.assertIn(r"ali\x1bce", sqlite_rendered)
        self.assertIn(r"line 1\nline 2\tboom", sqlite_rendered)

    def test_tui_summary_escapes_rich_markup_from_user_content(self) -> None:
        post = bbs_tui_backend.PostRecord(
            id=7,
            username="[admin]",
            message="[bold]boom[/bold]",
            timestamp="2026-04-08T18:55:09",
            board="gen[eral]",
            board_seq=3,
        )

        summary = bbs_tui_backend.format_post_summary(post, include_board=True)
        detail = bbs_tui_backend.format_post_detail(post)

        self.assertIn(r"\[admin]", summary)
        self.assertIn(r"\[bold]boom\[/bold]", summary)
        self.assertIn(r"/gen\[eral]", summary)
        self.assertIn(r"\[admin]", detail)
        self.assertIn(r"\[bold]boom\[/bold]", detail)

    def test_bbs_tui_main_keeps_callers_working_directory(self) -> None:
        import bbs_tui

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                argv = ["bbs_tui.py", "--backend", "json"]
                with mock.patch.object(sys, "argv", argv):
                    with mock.patch.object(bbs_tui.BbsTuiApp, "run", autospec=True, return_value=None):
                        bbs_tui.main()
                final_cwd = Path.cwd()

        self.assertEqual(final_cwd, workdir)

    def test_app_paths_resolve_inside_configured_data_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with use_bbs_data_dir(workdir):
                self.assertEqual(get_data_dir(), workdir)
                self.assertEqual(get_db_path(), workdir / "bbs.db")
                self.assertEqual(get_json_path(), workdir / "bbs.json")
                self.assertEqual(get_backups_dir(), workdir / "backups")
                self.assertEqual(get_exports_dir(), workdir / "exports")


if __name__ == "__main__":
    unittest.main()
