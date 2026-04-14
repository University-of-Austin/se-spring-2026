import os
import tempfile
import unittest
from pathlib import Path
from contextlib import contextmanager

from bbs_tui_backend import (
    BackendCapabilities,
    BoardInfo,
    JsonBackend,
    PostActionResult,
    PostRecord,
    ProfileRecord,
    SqliteBackend,
    load_backend,
)
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


class BbsTuiBackendTests(_DataDirTestCase):
    def setUp(self) -> None:
        # Tests explicitly select their own temporary data directory.
        return None

    def test_json_backend_reads_and_posts_flat_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = JsonBackend()
                result = backend.post("alice", "general", "Hello from the TUI")
                posts = backend.read_posts("general")
                users = backend.list_users()

            self.assertEqual(result.board, "general")
            self.assertIsNone(result.created_board)
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0].username, "alice")
            self.assertEqual(posts[0].message, "Hello from the TUI")
            self.assertEqual(users, ["alice"])

    def test_sqlite_backend_supports_boards_threads_and_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                created = backend.post("alice", "announcements", "Hello board")
                backend.reply("alice", 1, "Reply message")
                backend.set_bio("alice", "First caller")
                posts = backend.read_posts("announcements")
                profile = backend.get_profile("alice")
                boards = backend.list_boards()

            self.assertEqual(created.created_board, "announcements")
            self.assertEqual(created.board, "announcements")
            self.assertEqual([post.id for post in posts], [1, 2])
            self.assertEqual(posts[1].parent_post_id, 1)
            self.assertIsNotNone(profile)
            self.assertEqual(profile.username, "alice")
            self.assertEqual(profile.post_count, 2)
            self.assertIn("announcements", boards)

    def test_sqlite_backend_can_limit_board_reads_to_latest_posts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                for index in range(1, 6):
                    backend.post("alice", "general", f"General {index}")
                posts = backend.read_posts("general", limit=2)

        self.assertEqual([post.message for post in posts], ["General 4", "General 5"])
        self.assertEqual([post.board_seq for post in posts], [4, 5])

    def test_sqlite_backend_can_limit_user_posts_to_recent_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Alice 1")
                backend.post("bob", "general", "Bob 1")
                backend.post("alice", "random", "Alice 2")
                backend.post("carol", "general", "Carol 1")
                backend.post("alice", "general", "Alice 3")
                posts = backend.get_user_posts("alice", limit=2)

        self.assertEqual([post.message for post in posts], ["Alice 2", "Alice 3"])
        self.assertEqual([post.board for post in posts], ["random", "general"])

    def test_sqlite_backend_lists_created_users_before_they_post(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                created = backend.create_user("alice", "1234")
                users = backend.list_users()

        self.assertTrue(created)
        self.assertEqual(users, ["alice"])

    def test_sqlite_backend_can_search_users_by_substring(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.create_user("alice", "1234")
                backend.create_user("alina", "1234")
                backend.create_user("bob", "1234")
                users = backend.search_users("ali")

        self.assertEqual(users, ["alice", "alina"])

    def test_sqlite_board_info_returns_post_count_and_creator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "First post")
                backend.post("bob", "general", "Second post")
                info = backend.get_board_info("general")

            self.assertIsNotNone(info)
            self.assertEqual(info.slug, "general")
            self.assertEqual(info.post_count, 2)
            self.assertEqual(info.created_by, "alice")
            self.assertIsNotNone(info.created_at)

    def test_sqlite_posts_have_per_board_sequence_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Gen 1")
                backend.post("alice", "random", "Rand 1")
                backend.post("bob", "general", "Gen 2")
                backend.post("bob", "random", "Rand 2")
                gen_posts = backend.read_posts("general")
                rand_posts = backend.read_posts("random")

            self.assertEqual([p.board_seq for p in gen_posts], [1, 2])
            self.assertEqual([p.board_seq for p in rand_posts], [1, 2])

    def test_sqlite_get_user_posts_returns_posts_with_board_info(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Post on general")
                backend.post("alice", "random", "Post on random")
                backend.post("bob", "general", "Bob's post")
                posts = backend.get_user_posts("alice")

            self.assertEqual(len(posts), 2)
            self.assertEqual(posts[0].board, "general")
            self.assertEqual(posts[1].board, "random")
            self.assertEqual(posts[0].username, "alice")

    def test_format_post_summary_uses_board_seq_and_friendly_date(self) -> None:
        from bbs_tui_backend import format_post_summary

        post = PostRecord(
            id=5, username="alice", message="Hello world",
            timestamp="2026-04-08T18:55:09", board="general",
            board_seq=2,
        )
        summary = format_post_summary(post)
        # Metadata line should come first, then message
        lines = summary.split("\n")
        self.assertEqual(len(lines), 2)
        # First line: metadata with username, timestamp, seq number
        self.assertIn("alice", lines[0])
        self.assertIn("#2", lines[0])
        self.assertNotIn("Hello world", lines[0])
        # Second line: the message
        self.assertIn("Hello world", lines[1])
        # Should use board_seq #2, not global id #5
        self.assertNotIn("#5", summary)
        # Should use friendly date, not ISO format
        self.assertNotIn("2026-04-08", summary)

    def test_format_post_summary_includes_board_when_requested(self) -> None:
        from bbs_tui_backend import format_post_summary

        post = PostRecord(
            id=5, username="alice", message="Hello world",
            timestamp="2026-04-08T18:55:09", board="random",
            board_seq=1,
        )
        summary = format_post_summary(post, include_board=True)
        lines = summary.split("\n")
        # Board slug should appear in the metadata line
        self.assertIn("/random", lines[0])

    def test_format_post_summary_preserves_message_newlines(self) -> None:
        from bbs_tui_backend import format_post_summary

        post = PostRecord(
            id=5,
            username="alice",
            message="line one\nline two\n\nline four",
            timestamp="2026-04-08T18:55:09",
            board="general",
            board_seq=2,
        )
        summary = format_post_summary(post)
        self.assertIn("line one\nline two\n\nline four", summary)
        self.assertNotIn(r"\n", summary)

    def test_format_post_summary_shows_img_tag_when_attachment_present(self) -> None:
        from bbs_tui_backend import format_post_summary

        post_with = PostRecord(
            id=1, username="alice", message="Check this out",
            timestamp="2026-04-08T18:55:09", board="general",
            board_seq=1, has_attachment=True,
        )
        post_without = PostRecord(
            id=2, username="bob", message="Just text",
            timestamp="2026-04-08T18:56:00", board="general",
            board_seq=2, has_attachment=False,
        )
        summary_with = format_post_summary(post_with)
        summary_without = format_post_summary(post_without)
        self.assertIn("[img]", summary_with)
        self.assertNotIn("[img]", summary_without)

    def test_auto_backend_prefers_sqlite_when_database_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                (workdir / "bbs.db").touch()
                backend = load_backend("auto")

            self.assertIsInstance(backend, SqliteBackend)

    def test_init_db_creates_attachments_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                from db import init_db, get_engine
                from sqlalchemy import text
                init_db()
                with get_engine().begin() as conn:
                    tables = [row[0] for row in conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ))]
                self.assertIn("attachments", tables)

    def test_store_attachment_copies_file_and_creates_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Check this out")
                posts = backend.read_posts("general")
                post_id = posts[-1].id

                # Create a fake image file
                img_path = workdir / "test.png"
                img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake image data")

                from bbs_db_store import store_attachment, get_attachment
                result = store_attachment(post_id, str(img_path))

                self.assertIsNotNone(result)
                self.assertEqual(len(result), 16)  # 16-char hex hash

                attachment = get_attachment(post_id)
                self.assertIsNotNone(attachment)
                self.assertEqual(attachment["original_name"], "test.png")
                self.assertEqual(attachment["mime_type"], "image/png")
                self.assertGreater(attachment["size_bytes"], 0)

                # File should exist in uploads dir
                from app_paths import get_uploads_dir
                stored_path = get_uploads_dir() / f"{result}.png"
                self.assertTrue(stored_path.exists())

    def test_store_attachment_deduplicates_identical_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Post 1")
                backend.post("bob", "general", "Post 2")
                posts = backend.read_posts("general")

                img_path = workdir / "test.png"
                img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"same content")

                from bbs_db_store import store_attachment
                from app_paths import get_uploads_dir
                hash1 = store_attachment(posts[0].id, str(img_path))
                hash2 = store_attachment(posts[1].id, str(img_path))

                self.assertEqual(hash1, hash2)
                # Only one file in uploads
                uploads = list(get_uploads_dir().iterdir())
                self.assertEqual(len(uploads), 1)

    def test_get_attachment_returns_none_for_post_without_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "No image here")
                posts = backend.read_posts("general")

                from bbs_db_store import get_attachment
                result = get_attachment(posts[0].id)
                self.assertIsNone(result)

    def test_posts_with_attachment_have_has_attachment_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            with self.use_workdir(workdir):
                backend = SqliteBackend()
                backend.post("alice", "general", "Post with image")
                backend.post("bob", "general", "Post without image")
                posts = backend.read_posts("general")
                post_with_img = posts[0]

                img_path = workdir / "photo.png"
                img_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"test image")

                from bbs_db_store import store_attachment
                store_attachment(post_with_img.id, str(img_path))

                # Re-read posts — first should have attachment, second should not
                posts = backend.read_posts("general")
                self.assertTrue(posts[0].has_attachment)
                self.assertFalse(posts[1].has_attachment)


class BbsTuiSmokeTest(_DataDirTestCase):
    def test_app_starts_and_renders(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            async with app.run_test(size=(120, 40)) as pilot:
                assert app.section == "timeline"

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_repeated_timeline_action_uses_cached_view_until_refresh(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp

        class CountingBackend:
            kind = "json"
            label = "Counting"
            capabilities = BackendCapabilities(False, False, False)

            def __init__(self) -> None:
                self.board_calls = 0
                self.timeline_calls = 0

            def list_boards(self) -> list[str]:
                self.board_calls += 1
                return ["general"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                self.timeline_calls += 1
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board="general")

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            backend = CountingBackend()
            app.backend = backend
            async with app.run_test(size=(120, 40)):
                self.assertEqual(backend.board_calls, 1)
                self.assertEqual(backend.timeline_calls, 1)
                await app.action_show_timeline()
                self.assertEqual(backend.timeline_calls, 1)
                await app.action_refresh()
                self.assertEqual(backend.timeline_calls, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_caps_rendered_posts_to_recent_window(self) -> None:
        import asyncio
        from textual.widgets import Static
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 256):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                items = app.query_one("#items", OptionList)
                status = app.query_one("#status", Static)

                self.assertEqual(items.option_count, app.TIMELINE_POST_LIMIT)
                self.assertEqual(len(app.current_items), app.TIMELINE_POST_LIMIT)
                self.assertEqual(
                    app.current_items[0].value.message,
                    "General 255",
                )
                self.assertEqual(
                    app.current_items[-1].value.message,
                    f"General {256 - app.TIMELINE_POST_LIMIT}",
                )
                self.assertEqual(
                    status.render().plain,
                    f"/general (showing latest {app.TIMELINE_POST_LIMIT} of 255)",
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_defaults_to_newest_first(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 4):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                self.assertEqual(app.current_items[0].value.message, "General 3")
                self.assertEqual(app.current_items[-1].value.message, "General 1")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_loads_older_posts_when_highlight_reaches_end(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 261):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                items = app.query_one("#items", OptionList)
                expected_count = app.TIMELINE_POST_LIMIT
                self.assertEqual(len(app.current_items), expected_count)

                items.highlighted = items.option_count - 1
                await app.on_option_list_option_highlighted(
                    OptionList.OptionHighlighted(
                        items,
                        items.get_option_at_index(items.option_count - 1),
                        items.option_count - 1,
                    )
                )
                await pilot.pause()

                loaded_count = min(260, app.TIMELINE_POST_LIMIT * 2)
                self.assertEqual(len(app.current_items), loaded_count)
                self.assertEqual(app.current_items[0].value.message, "General 260")
                self.assertEqual(app.current_items[-1].value.message, f"General {261 - loaded_count}")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_oldest_first_timeline_loads_older_posts_when_highlight_reaches_top(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 261):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await app.action_toggle_timeline_order()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                expected_count = app.TIMELINE_POST_LIMIT
                oldest_visible = 261 - expected_count
                self.assertEqual(len(app.current_items), expected_count)
                self.assertEqual(items.highlighted, items.option_count - 1)
                self.assertEqual(app.current_items[0].value.message, f"General {oldest_visible}")
                self.assertEqual(app.current_items[-1].value.message, "General 260")

                items.highlighted = 0
                await pilot.pause()

                loaded_count = min(260, expected_count + app.TIMELINE_POST_LIMIT)
                newly_loaded = loaded_count - expected_count
                self.assertEqual(len(app.current_items), loaded_count)
                self.assertEqual(items.highlighted, newly_loaded)
                self.assertEqual(app.current_items[0].value.message, f"General {261 - loaded_count}")
                self.assertEqual(app.current_items[-1].value.message, "General 260")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_newest_first_timeline_loads_older_posts_when_scrolled_to_bottom_edge(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 261):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                items = app.query_one("#items", OptionList)
                items.scroll_to(
                    y=max(0, items.max_scroll_y - 3),
                    animate=False,
                    force=True,
                    immediate=True,
                )
                scroll_before = items.scroll_y

                items._maybe_request_history_preload(scroll_up=False)
                await pilot.pause()

                loaded_count = min(260, app.TIMELINE_POST_LIMIT * 2)
                self.assertEqual(len(app.current_items), loaded_count)
                self.assertEqual(app.current_items[0].value.message, "General 260")
                self.assertEqual(app.current_items[-1].value.message, f"General {261 - loaded_count}")
                self.assertLessEqual(abs(items.scroll_y - scroll_before), 3)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_option_list_fills_center_pane_width(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                center = app.query_one("#center")
                self.assertGreaterEqual(items.region.width, center.region.width - 4)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_standard_terminal_allocates_majority_width_to_timeline(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                sidebar = app.query_one("#sidebar")
                inspector = app.query_one("#inspector")
                self.assertGreaterEqual(items.region.width, 55)
                self.assertLess(sidebar.region.width, items.region.width)
                self.assertLess(inspector.region.width, items.region.width)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_reply_timeline_rows_do_not_start_with_extra_indent(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            parent = backend.post("alice", "general", "Parent post")
            backend.reply("bob", 1, "Reply body")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(140, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                self.assertIn("↩", items.render_line(0).text.lstrip()[:2])

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_first_rendered_line_is_not_blank_spacer(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Earlier post")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                first_line = items.render_line(0).text
                self.assertIn("alice", first_line)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_uses_stable_vertical_scrollbar_gutter(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(150):
                backend.post("alice", "general", f"post {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                self.assertTrue(items.show_vertical_scrollbar)
                self.assertEqual(str(items.styles.scrollbar_gutter), "stable")
                self.assertEqual(str(items.styles.overflow_y), "scroll")
                self.assertEqual(items.styles.scrollbar_size_vertical, 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_inserts_blank_line_between_posts(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "first")
            backend.post("bob", "general", "second")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                self.assertIn("bob", items.render_line(0).text)
                self.assertIn("second", items.render_line(1).text)
                self.assertEqual(items.render_line(2).text.strip(), "")
                self.assertIn("alice", items.render_line(3).text)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_newest_first_timeline_preloads_before_hard_edge(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 261):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                items = app.query_one("#items", OptionList)
                items.scroll_to(y=max(0, items.max_scroll_y - 10), animate=False, force=True, immediate=True)

                items._maybe_request_history_preload(scroll_up=False)
                await pilot.pause()

                self.assertEqual(len(app.current_items), app.TIMELINE_POST_LIMIT * 2)
                self.assertEqual(app.current_items[0].value.message, "General 260")
                self.assertEqual(app.current_items[-1].value.message, f"General {261 - (app.TIMELINE_POST_LIMIT * 2)}")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_oldest_first_timeline_loads_older_posts_when_scrolled_to_top_edge(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 261):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await app.action_toggle_timeline_order()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                items.scroll_to(y=3, animate=False, force=True, immediate=True)
                scroll_before = items.scroll_y

                items._maybe_request_history_preload(scroll_up=True)
                await pilot.pause()
                await pilot.pause()

                loaded_count = min(260, app.TIMELINE_POST_LIMIT * 2)
                newly_loaded = loaded_count - app.TIMELINE_POST_LIMIT
                self.assertEqual(len(app.current_items), loaded_count)
                self.assertEqual(app.current_items[0].value.message, f"General {261 - loaded_count}")
                self.assertEqual(app.current_items[-1].value.message, "General 260")
                self.assertEqual(items.highlighted, newly_loaded)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_board_switch_inside_timeline_avoids_section_switch_and_resets_to_live_edge(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        class BoardBackend:
            kind = "sqlite"
            label = "Boards"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "testing"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
                count = 4
                posts = [
                    PostRecord(
                        id=index if board == "general" else 100 + index,
                        username="alice",
                        message=f"{board} {index}",
                        timestamp=f"2026-04-09T12:00:0{index}",
                        board=board,
                        board_seq=index,
                    )
                    for index in range(1, count + 1)
                ]
                return posts[-limit:] if limit is not None else posts

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def search_users(self, keyword: str) -> list[str]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return BoardInfo(
                    slug=board,
                    name=board,
                    post_count=4,
                    created_at="2026-04-09T12:00:01",
                    created_by="alice",
                )

            def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

            def get_user_auth_state(self, username: str) -> str:
                return "missing"

            def set_initial_pin(self, username: str, pin: str) -> None:
                raise NotImplementedError

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = BoardBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app._refresh_board_list()
                await app._show_section("timeline")
                items = app.query_one("#items", OptionList)

                async def unexpected_show_section(section: str) -> None:
                    raise AssertionError("board switch inside the timeline should not route through a section switch")

                app._show_section = unexpected_show_section  # type: ignore[method-assign]

                await app._set_current_board("testing", show_timeline=True)
                await pilot.pause()

                self.assertEqual(app.current_board, "testing")
                self.assertEqual(app.current_items[0].value.message, "testing 4")
                self.assertEqual(items.highlighted, 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_order_indicator_shows_arrow_for_current_mode(self) -> None:
        import asyncio
        from textual.widgets import Static
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "General 1")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                indicator = app.query_one("#timeline-order-indicator", Static)
                self.assertEqual(indicator.render().plain, "↓")

                await app.action_toggle_timeline_order()
                await pilot.pause()

                self.assertEqual(indicator.render().plain, "↑")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_timeline_order_can_be_toggled(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 4):
                backend.post("alice", "general", f"General {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                self.assertEqual(app.current_items[0].value.message, "General 3")

                await app.action_toggle_timeline_order()
                await pilot.pause()

                self.assertEqual(app.current_items[0].value.message, "General 1")
                self.assertEqual(app.current_items[-1].value.message, "General 3")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_submitting_post_shows_new_post_immediately_in_newest_first_view(self) -> None:
        import asyncio
        from textual.widgets import TextArea
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Earlier post")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                composer = app.query_one("#compose-message", TextArea)
                composer.text = "Newest post"
                await app._submit_compose()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                self.assertEqual(app.current_items[0].value.message, "Newest post")
                self.assertEqual(items.highlighted, 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_submitting_post_on_current_board_avoids_full_reload_path(self) -> None:
        import asyncio
        from textual.widgets import TextArea
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Earlier post")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                composer = app.query_one("#compose-message", TextArea)
                composer.text = "In-place post"

                async def unexpected_board_refresh() -> None:
                    raise AssertionError("posting on the current board should not refresh the board list")

                async def unexpected_show_section(section: str) -> None:
                    raise AssertionError("posting on the current board should not switch sections")

                app._refresh_board_list = unexpected_board_refresh  # type: ignore[method-assign]
                app._show_section = unexpected_show_section  # type: ignore[method-assign]

                await app._submit_compose()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                self.assertEqual(app.current_items[0].value.message, "In-place post")
                self.assertEqual(items.highlighted, 0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_submitting_long_post_keeps_body_visible_in_timeline(self) -> None:
        import asyncio
        from textual.widgets import TextArea
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            long_message = " ".join(
                ["This is a deliberately long post body to test rendering and wrapping behavior."] * 8
            )
            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                composer = app.query_one("#compose-message", TextArea)
                composer.text = long_message
                await app._submit_compose()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                rendered = "\n".join(items.render_line(index).text for index in range(min(8, len(items._lines))))
                self.assertIn("deliberately long post body", rendered)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_submitting_long_reply_keeps_body_visible_in_timeline(self) -> None:
        import asyncio
        from textual.widgets import TextArea
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Parent post")
            long_reply = " ".join(
                ["This is a deliberately long reply body to test rendering and wrapping behavior."] * 8
            )

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                parent = app.current_items[0].value
                app._set_reply_target(parent)
                composer = app.query_one("#compose-message", TextArea)
                composer.text = long_reply
                await app._submit_reply()
                await pilot.pause()

                items = app.query_one("#items", OptionList)
                rendered = "\n".join(items.render_line(index).text for index in range(min(12, len(items._lines))))
                self.assertIn("deliberately long reply body", rendered)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_future_timestamps_do_not_hide_new_posts_in_newest_first_timeline(self) -> None:
        import asyncio
        from sqlalchemy import text
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList
        from db import engine, init_db

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Future-dated seed post")
            init_db()
            with engine.begin() as connection:
                connection.execute(
                    text("UPDATE posts SET timestamp = '2026-12-31T23:59:59' WHERE id = 1")
                )
            backend.post("alice", "general", "Actual new post")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                items = app.query_one("#items", OptionList)
                self.assertEqual(items.highlighted, 0)
                self.assertEqual(app.current_items[0].value.message, "Actual new post")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_profile_view_caps_rendered_posts_to_recent_window(self) -> None:
        import asyncio
        from textual.widgets import ListView, Static
        from bbs_tui import BbsTuiApp

        async def run() -> None:
            backend = SqliteBackend()
            for index in range(1, 256):
                backend.post("alice", "general", f"Alice {index}")

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await app._load_profile_view("alice")
                await pilot.pause()
                header = app.query_one("#profile-header", Static)
                posts = app.query_one("#profile-posts", ListView)

                self.assertIn("255 posts", header.render().plain)
                self.assertEqual(len(posts.children), app.PROFILE_POST_LIMIT)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_board_sidebar_and_compose_select_share_one_current_board_state(self) -> None:
        import asyncio
        from textual.widgets import ListView, Select
        from bbs_tui import BbsTuiApp

        class BoardBackend:
            kind = "sqlite"
            label = "Boards"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "build-log", "announcements"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = BoardBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app._refresh_board_list()
                board_list = app.query_one("#board-list", ListView)
                board_select = app.query_one("#compose-board-select", Select)

                await app._set_current_board("build-log", refresh_timeline=False)

                self.assertEqual(app.current_board, "build-log")
                self.assertEqual(board_select.value, "build-log")
                self.assertEqual(board_list.index, 1)

                await app._set_current_board("announcements", refresh_timeline=False)

                self.assertEqual(app.current_board, "announcements")
                self.assertEqual(board_select.value, "announcements")
                self.assertEqual(board_list.index, 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_board_switch_does_not_rebuild_sidebar_rows_when_boards_are_unchanged(self) -> None:
        import asyncio
        from textual.widgets import ListView
        from bbs_tui import BbsTuiApp

        class BoardBackend:
            kind = "sqlite"
            label = "Boards"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "build-log", "announcements"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

            def get_user_auth_state(self, username: str) -> str:
                return "missing"

            def set_initial_pin(self, username: str, pin: str) -> None:
                raise NotImplementedError

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = BoardBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app._refresh_board_list()
                board_list = app.query_one("#board-list", ListView)
                before_children = list(board_list.children)

                await app._set_current_board("build-log", refresh_timeline=False)
                await pilot.pause()

                after_children = list(board_list.children)
                self.assertEqual(before_children, after_children)
                self.assertEqual(board_list.index, 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_board_switch_only_syncs_sidebar_once(self) -> None:
        import asyncio
        from types import MethodType
        from textual.widgets import ListView
        from bbs_tui import BbsTuiApp

        class BoardBackend:
            kind = "sqlite"
            label = "Boards"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "build-log", "announcements"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

            def get_user_auth_state(self, username: str) -> str:
                return "missing"

            def set_initial_pin(self, username: str, pin: str) -> None:
                raise NotImplementedError

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = BoardBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                counts = {"sidebar": 0}
                original = app._sync_board_sidebar

                async def wrapped(self) -> None:
                    counts["sidebar"] += 1
                    await original()

                app._sync_board_sidebar = MethodType(wrapped, app)
                board_list = app.query_one("#board-list", ListView)
                second_board = list(board_list.children)[1]

                await app.on_list_view_selected(ListView.Selected(board_list, second_board, 1))
                await pilot.pause()

                self.assertEqual(app.current_board, "build-log")
                self.assertEqual(counts["sidebar"], 1)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_search_panel_can_switch_between_post_and_user_results(self) -> None:
        import asyncio
        from textual.widgets import Button, Input, Static
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        class SearchBackend:
            kind = "sqlite"
            label = "Search"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general"]

            def list_users(self) -> list[str]:
                return ["alice", "bob"]

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return [
                    PostRecord(
                        id=1,
                        username="alice",
                        message=f"post match {keyword}",
                        timestamp="2026-04-09T12:00:00",
                        board="general",
                        board_seq=1,
                    )
                ]

            def search_users(self, keyword: str) -> list[str]:
                return ["alice"] if "ali" in keyword else []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = SearchBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app.action_show_search()
                search_input = app.query_one("#search-input", Input)
                users_button = app.query_one("#search-mode-users", Button)
                items = app.query_one("#items", OptionList)
                status = app.query_one("#status", Static)

                search_input.value = "ali"
                await app._submit_search()
                self.assertEqual(len(app.current_items), 1)
                self.assertEqual(app.current_items[0].kind, "post")

                await app.on_button_pressed(Button.Pressed(users_button))
                await app._submit_search()
                await pilot.pause()

                self.assertEqual(app.search_mode, "users")
                self.assertEqual(len(app.current_items), 1)
                self.assertEqual(app.current_items[0].kind, "user")
                self.assertEqual(app.current_items[0].value, "alice")
                self.assertEqual(status.render().plain, "Search users: ali")
                self.assertEqual(items.highlighted, None)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_search_posts_caps_large_result_sets_for_responsive_rendering(self) -> None:
        import asyncio
        from textual.widgets import Input, Static
        from bbs_tui import BbsTuiApp

        class SearchBackend:
            kind = "sqlite"
            label = "Search"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return [
                    PostRecord(
                        id=index,
                        username="alice",
                        message=f"post match {keyword} {index}",
                        timestamp="2026-04-09T12:00:00",
                        board="general",
                        board_seq=index,
                    )
                    for index in range(1, 451)
                ]

            def search_users(self, keyword: str) -> list[str]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

            def get_user_auth_state(self, username: str) -> str:
                return "missing"

            def set_initial_pin(self, username: str, pin: str) -> None:
                raise NotImplementedError

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = SearchBackend()
            async with app.run_test(size=(120, 40)):
                await app.action_show_search()
                search_input = app.query_one("#search-input", Input)
                status = app.query_one("#status", Static)

                search_input.value = "ali"
                await app._submit_search()

                self.assertEqual(len(app.current_items), 200)
                self.assertEqual(
                    status.render().plain,
                    "Search posts: ali (showing first 200 of 450)",
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_search_post_selection_exposes_back_board_and_profile_actions(self) -> None:
        import asyncio
        from textual.widgets import Button, Input, Static
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        class SearchBackend:
            kind = "sqlite"
            label = "Search"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general"]

            def list_users(self) -> list[str]:
                return ["alice"]

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                return [
                    PostRecord(
                        id=1,
                        username="alice",
                        message="post match ali",
                        timestamp="2026-04-09T12:00:00",
                        board="general",
                        board_seq=1,
                    )
                ]

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return [
                    PostRecord(
                        id=1,
                        username="alice",
                        message="post match ali",
                        timestamp="2026-04-09T12:00:00",
                        board="general",
                        board_seq=1,
                    )
                ]

            def search_users(self, keyword: str) -> list[str]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return ProfileRecord(username="alice", joined_at="2026-04-09T12:00:00", bio="", post_count=1)

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = SearchBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app.action_show_search()
                search_input = app.query_one("#search-input", Input)
                items = app.query_one("#items", OptionList)
                inspector = app.query_one("#inspector-body", Static)
                back_button = app.query_one("#search-back", Button)
                board_button = app.query_one("#search-go-board", Button)
                profile_button = app.query_one("#search-go-profile", Button)

                search_input.value = "ali"
                await app._submit_search()
                await app.on_option_list_option_selected(
                    OptionList.OptionSelected(items, items.get_option_at_index(0), 0)
                )
                await pilot.pause()

                self.assertIsNotNone(app.search_selected_post)
                self.assertIn("post match ali", inspector.render().plain)
                self.assertTrue(back_button.display)
                self.assertTrue(board_button.display)
                self.assertTrue(profile_button.display)

                await app.on_button_pressed(Button.Pressed(back_button))
                self.assertIsNone(app.search_selected_post)
                self.assertFalse(back_button.display)
                self.assertFalse(board_button.display)
                self.assertFalse(profile_button.display)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_search_post_actions_can_jump_to_board_and_profile(self) -> None:
        import asyncio
        from textual.widgets import Button, Input, Static
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        class SearchBackend:
            kind = "sqlite"
            label = "Search"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "testing"]

            def list_users(self) -> list[str]:
                return ["alice"]

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                if board == "testing":
                    return [
                        PostRecord(
                            id=7,
                            username="alice",
                            message="found in testing",
                            timestamp="2026-04-09T12:00:00",
                            board="testing",
                            board_seq=2,
                        )
                    ]
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return [
                    PostRecord(
                        id=7,
                        username="alice",
                        message="found in testing",
                        timestamp="2026-04-09T12:00:00",
                        board="testing",
                        board_seq=2,
                    )
                ]

            def search_users(self, keyword: str) -> list[str]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return ProfileRecord(username="alice", joined_at="2026-04-09T12:00:00", bio="", post_count=1)

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = SearchBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app.action_show_search()
                search_input = app.query_one("#search-input", Input)
                items = app.query_one("#items", OptionList)
                board_button = app.query_one("#search-go-board", Button)
                profile_button = app.query_one("#search-go-profile", Button)

                search_input.value = "testing"
                await app._submit_search()
                await app.on_option_list_option_selected(
                    OptionList.OptionSelected(items, items.get_option_at_index(0), 0)
                )
                await pilot.pause()

                await app.on_button_pressed(Button.Pressed(board_button))
                self.assertEqual(app.section, "timeline")
                self.assertEqual(app.current_board, "testing")

                await app.action_show_search()
                search_input.value = "testing"
                await app._submit_search()
                await app.on_option_list_option_selected(
                    OptionList.OptionSelected(items, items.get_option_at_index(0), 0)
                )
                await pilot.pause()

                await app.on_button_pressed(Button.Pressed(profile_button))
                self.assertEqual(app.section, "profile")
                self.assertEqual(app.query_one("#profile-header", Static).render().plain.startswith("@alice"), True)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_draft_board_name_is_rendered_across_ui_while_typing(self) -> None:
        import asyncio
        from textual.widgets import Input, ListItem, ListView, Select, Static
        from bbs_tui import BbsTuiApp

        class BoardBackend:
            kind = "sqlite"
            label = "Boards"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "build-log", "announcements"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                return []

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                raise NotImplementedError

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = BoardBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                board_input = app.query_one("#compose-board-new", Input)
                board_list = app.query_one("#board-list", ListView)
                status = app.query_one("#status", Static)

                app.creating_new_board = True
                board_input.display = True
                board_input.value = "release notes"
                await pilot.pause()

                self.assertEqual(app.current_board, "general")
                self.assertEqual(app.draft_board_name, "release notes")
                self.assertTrue(board_input.display)
                self.assertEqual(status.render().plain, "/release notes (new)")
                board_rows = [child for child in board_list.children if isinstance(child, ListItem)]
                self.assertEqual(len(board_rows), 4)
                self.assertEqual(
                    board_rows[-1].query_one(Static).render().plain,
                    "release notes",
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_reply_mode_locks_board_selection_to_parent_board(self) -> None:
        import asyncio
        from textual.widgets import Input, Select
        from bbs_tui import BbsTuiApp

        class ReplyBackend:
            kind = "sqlite"
            label = "Reply"
            capabilities = BackendCapabilities(True, True, True)

            def list_boards(self) -> list[str]:
                return ["general", "testing"]

            def list_users(self) -> list[str]:
                return []

            def read_posts(self, board: str = "general") -> list[PostRecord]:
                if board != "general":
                    return []
                return [
                    PostRecord(
                        id=3,
                        username="anonymous",
                        message="Hello",
                        timestamp="2026-04-09T15:00:00",
                        board="general",
                        board_seq=3,
                    )
                ]

            def search_posts(self, keyword: str) -> list[PostRecord]:
                return []

            def search_users(self, keyword: str) -> list[str]:
                return []

            def post(self, username: str, board: str, message: str) -> PostActionResult:
                return PostActionResult(board=board)

            def reply(self, username: str, parent_post_id: int, message: str) -> None:
                return None

            def get_profile(self, username: str) -> ProfileRecord | None:
                return None

            def set_bio(self, username: str, bio: str) -> None:
                raise NotImplementedError

            def get_board_info(self, board: str) -> BoardInfo | None:
                return None

            def get_user_posts(self, username: str) -> list[PostRecord]:
                return []

            def create_user(self, username: str, pin: str) -> bool:
                return False

            def verify_user(self, username: str, pin: str) -> bool:
                return False

        async def run() -> None:
            app = BbsTuiApp(backend_mode="json")
            app.backend = ReplyBackend()
            async with app.run_test(size=(120, 40)) as pilot:
                await app._refresh_board_list()
                await app._set_current_board("testing", refresh_timeline=False)
                board_select = app.query_one("#compose-board-select", Select)
                board_input = app.query_one("#compose-board-new", Input)

                app.creating_new_board = True
                app.draft_board_name = "test"
                board_input.display = True
                board_input.value = "test"

                parent = PostRecord(
                    id=3,
                    username="anonymous",
                    message="Hello",
                    timestamp="2026-04-09T15:00:00",
                    board="general",
                    board_seq=3,
                )
                app._set_reply_target(parent)
                await pilot.pause()

                self.assertEqual(app.current_board, "general")
                self.assertFalse(app.creating_new_board)
                self.assertEqual(app.draft_board_name, "")
                self.assertEqual(board_select.value, "general")
                self.assertFalse(board_select.display)
                self.assertFalse(board_input.display)

                app._clear_reply_target()
                self.assertTrue(board_select.display)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())

    def test_reply_target_highlights_selected_timeline_post(self) -> None:
        import asyncio
        from bbs_tui import BbsTuiApp, TimelineOptionList as OptionList

        async def run() -> None:
            backend = SqliteBackend()
            backend.post("alice", "general", "Parent post")
            backend.post("bob", "general", "Another post")
            parent = backend.read_posts("general")[0]

            app = BbsTuiApp(backend_mode="sqlite")
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                items = app.query_one("#items", OptionList)
                target_index = next(
                    index
                    for index, render_item in enumerate(app.current_items)
                    if render_item.kind == "post" and render_item.value.id == parent.id
                )
                original_prompt = str(items.get_option_at_index(target_index).prompt)
                original_line_count = original_prompt.count("\n")

                app._set_reply_target(parent)
                await pilot.pause()

                reply_prompt = str(items.get_option_at_index(target_index).prompt)
                self.assertIn("▎", reply_prompt)
                self.assertNotIn("Reply target", reply_prompt)
                self.assertEqual(reply_prompt.count("\n"), original_line_count)

                app._clear_reply_target()
                await pilot.pause()

                cleared_prompt = str(items.get_option_at_index(target_index).prompt)
                self.assertNotIn("▎", cleared_prompt)
                self.assertEqual(cleared_prompt, original_prompt)

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.use_workdir(Path(tmpdir)):
                asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
