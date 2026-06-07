from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import ClassVar

from rich.markup import escape as escape_markup
from rich.style import Style as RichStyle

from bbs_db_format import escape_display_text
from bbs_tui_backend import (
    BbsBackend,
    JsonBackend,
    PostRecord,
    _format_timestamp,
    format_post_detail,
    format_post_summary,
    format_reply_quote,
    load_backend,
)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual import events, on
from textual.geometry import Size, Spacing
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.visual import Padding, visualize
from textual.widgets import Button, Footer, Header, Input, ListItem, ListView, Select, Static, TextArea
from textual.widgets._option_list import Option
import os as _os
if _os.environ.get("TMUX"):
    from textual_image.widget import HalfcellImage as Image
else:
    from textual_image.widget import Image


@dataclass
class RenderItem:
    kind: str
    label: str
    value: object


def _safe_markup(value: object) -> str:
    return escape_markup(escape_display_text(value))


class TimelineHistoryEdgeReached(Message, bubble=True):
    def __init__(self, option_list: "TimelineOptionList") -> None:
        super().__init__()
        self.option_list = option_list

    @property
    def control(self) -> "TimelineOptionList":
        return self.option_list


class TimelineOptionList(ScrollView, can_focus=True):
    BINDINGS = [
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
        Binding("enter", "select", show=False),
    ]

    COMPONENT_CLASSES: ClassVar[set[str]] = {
        "option-list--option",
        "option-list--option-highlighted",
        "option-list--option-hover",
    }

    DEFAULT_CSS = """
    TimelineOptionList {
        overflow-y: scroll;
        overflow-x: hidden;
    }
    """

    highlighted: reactive[int | None] = reactive(None)

    class OptionMessage(Message):
        def __init__(self, option_list: "TimelineOptionList", option: Option, index: int) -> None:
            super().__init__()
            self.option_list = option_list
            self.option = option
            self.option_id = option.id
            self.option_index = index

        @property
        def control(self) -> "TimelineOptionList":
            return self.option_list

    class OptionHighlighted(OptionMessage):
        pass

    class OptionSelected(OptionMessage):
        pass

    def __init__(
        self,
        *content: object,
        preload_margin: int = 4,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.preload_margin = preload_margin
        self.history_edge = "bottom"
        self._history_preload_armed = True
        self.options: list[Option] = [option for option in content if isinstance(option, Option)]
        self._lines: list[tuple[int, int]] = []
        self._option_render_cache: dict[int, list[Strip]] = {}
        self._option_line_starts: dict[int, int] = {}
        self._option_line_ends: dict[int, int] = {}
        self._cache_width = -1
        self._cache_highlighted: int | None = None

    @property
    def index(self) -> int | None:
        return self.highlighted

    @index.setter
    def index(self, value: int | None) -> None:
        self.highlighted = value

    @property
    def option_count(self) -> int:
        return len(self.options)

    def set_options(self, options: list[Option]) -> None:
        self.options = list(options)
        self._invalidate_option_cache()
        self.highlighted = self.validate_highlighted(self.highlighted)
        self.refresh(layout=True)

    def clear_options(self) -> None:
        self.set_options([])

    def get_option_at_index(self, index: int) -> Option:
        return self.options[index]

    def replace_option_prompt_at_index(self, index: int, prompt: str) -> None:
        self.options[index]._set_prompt(prompt)
        self._invalidate_option_cache()
        self.refresh(layout=True)

    def set_history_edge(self, edge: str) -> None:
        self.history_edge = edge
        self.arm_history_preload()

    def arm_history_preload(self) -> None:
        self._history_preload_armed = True

    def validate_highlighted(self, highlighted: int | None) -> int | None:
        if highlighted is None or not self.options:
            return None
        if highlighted < 0:
            return 0
        if highlighted >= len(self.options):
            return len(self.options) - 1
        return highlighted

    def watch_highlighted(self, highlighted: int | None) -> None:
        self._invalidate_option_cache()
        if highlighted is None or highlighted >= len(self.options):
            self.refresh()
            return
        self.scroll_to_highlight()
        self.post_message(self.OptionHighlighted(self, self.options[highlighted], highlighted))
        self.refresh()

    def _invalidate_option_cache(self) -> None:
        self._lines = []
        self._option_render_cache.clear()
        self._option_line_starts.clear()
        self._option_line_ends.clear()
        self._cache_width = -1
        self._cache_highlighted = None

    def _update_lines(self) -> None:
        width = max(1, self.scrollable_content_region.width)
        if self._cache_width == width and self._cache_highlighted == self.highlighted:
            return
        self._lines = []
        self._option_render_cache.clear()
        self._option_line_starts.clear()
        self._option_line_ends.clear()
        self._cache_width = width
        self._cache_highlighted = self.highlighted
        for index, option in enumerate(self.options):
            component_classes = (
                ("option-list--option-highlighted",)
                if index == self.highlighted
                else ()
            )
            style = self.get_visual_style("option-list--option", *component_classes)
            visual = visualize(self, option.prompt, markup=True)
            visual = Padding(visual, Spacing(0, 1, 1, 2))
            strips = visual.to_strips(self, visual, width, None, style)
            padded = [strip.extend_cell_length(width, style.rich_style) for strip in strips]
            row_style = (
                RichStyle(color="#e6f0ff", bgcolor="#17324d", bold=True)
                if index == self.highlighted
                else RichStyle(bgcolor="#0c0c0c" if index % 2 == 0 else "#090909")
            )
            padded = [strip.apply_style(row_style) for strip in padded]
            self._option_line_starts[index] = len(self._lines)
            self._option_render_cache[index] = padded
            for line_offset in range(len(padded)):
                self._lines.append((index, line_offset))
            self._option_line_ends[index] = len(self._lines) - 1
        self.virtual_size = Size(width, len(self._lines))

    def get_content_width(self, container, viewport) -> int:
        return max(1, viewport.width)

    def get_content_height(self, container, viewport, width: int) -> int:
        self._update_lines()
        return len(self._lines)

    def render_line(self, y: int) -> Strip:
        self._update_lines()
        line_number = int(self.scroll_y) + y
        width = max(1, self.scrollable_content_region.width)
        if not (0 <= line_number < len(self._lines)):
            return Strip.blank(width, self.get_visual_style("option-list--option").rich_style)
        option_index, line_offset = self._lines[line_number]
        return self._option_render_cache[option_index][line_offset]

    def scroll_to_highlight(self) -> None:
        self._update_lines()
        if self.highlighted is None or self.highlighted not in self._option_line_starts:
            return
        start = self._option_line_starts[self.highlighted]
        end = self._option_line_ends[self.highlighted]
        viewport_height = max(1, self.scrollable_content_region.height)
        top = int(self.scroll_y)
        bottom = top + viewport_height - 1
        if start < top:
            self.scroll_to(y=start, animate=False, force=True, immediate=True)
        elif end > bottom:
            self.scroll_to(y=end - viewport_height + 1, animate=False, force=True, immediate=True)

    def _scroll_targets_history(self, *, scroll_up: bool) -> bool:
        return scroll_up if self.history_edge == "top" else not scroll_up

    def _history_edge_distance(self) -> float:
        return self.scroll_y if self.history_edge == "top" else self.max_scroll_y - self.scroll_y

    def _maybe_request_history_preload(self, *, scroll_up: bool) -> None:
        if not self._scroll_targets_history(scroll_up=scroll_up):
            return
        if self._history_edge_distance() > self.preload_margin:
            self._history_preload_armed = True
            return
        if self._history_preload_armed:
            self._history_preload_armed = False
            self.post_message(TimelineHistoryEdgeReached(self))

    def _on_mouse_scroll_down(self, event) -> None:
        super()._on_mouse_scroll_down(event)
        self._maybe_request_history_preload(scroll_up=False)

    def _on_mouse_scroll_up(self, event) -> None:
        super()._on_mouse_scroll_up(event)
        self._maybe_request_history_preload(scroll_up=True)

    def _line_to_option_index(self, y: int) -> int | None:
        self._update_lines()
        line_number = int(self.scroll_y) + y
        if not (0 <= line_number < len(self._lines)):
            return None
        return self._lines[line_number][0]

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        option_index = self._line_to_option_index(event.y)
        if option_index is None:
            return
        self.highlighted = option_index
        self.post_message(self.OptionSelected(self, self.options[option_index], option_index))
        event.stop()

    def action_cursor_down(self) -> None:
        if not self.options:
            return
        self.highlighted = 0 if self.highlighted is None else min(self.highlighted + 1, len(self.options) - 1)

    def action_cursor_up(self) -> None:
        if not self.options:
            return
        self.highlighted = len(self.options) - 1 if self.highlighted is None else max(self.highlighted - 1, 0)

    def action_select(self) -> None:
        if self.highlighted is None or not (0 <= self.highlighted < len(self.options)):
            return
        self.post_message(self.OptionSelected(self, self.options[self.highlighted], self.highlighted))


class ImageLightboxScreen(Screen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    CSS = """
    ImageLightboxScreen {
        background: #080808;
        align: center middle;
    }

    #lightbox-container {
        width: 100%;
        height: 1fr;
        padding: 2 4;
    }

    #lightbox-image {
        width: 1fr;
        height: 1fr;
    }

    #lightbox-close {
        width: auto;
        background: #5a2a2a;
        color: #f0b8b8;
        border: none;
        margin-bottom: 1;
    }

    #lightbox-label {
        color: #555555;
        margin-top: 1;
    }
    """

    def __init__(self, image_path: str, filename: str, size_bytes: int) -> None:
        super().__init__()
        self._image_path = image_path
        self._filename = filename
        self._size_bytes = size_bytes

    def compose(self) -> ComposeResult:
        with Vertical(id="lightbox-container"):
            yield Button("X", id="lightbox-close")
            yield Image(self._image_path, id="lightbox-image")
            size_mb = self._size_bytes / (1024 * 1024)
            yield Static(f"{self._filename}  \u00b7  {size_mb:.1f} MB", id="lightbox-label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "lightbox-close":
            self.dismiss()


class BbsTuiApp(App[None]):
    TIMELINE_POST_LIMIT = 100
    PROFILE_POST_LIMIT = 100
    TIMELINE_PRELOAD_MARGIN = 12
    SEARCH_RESULT_LIMIT = 200
    CSS = """
    Screen {
        background: #080808;
    }

    * {
        scrollbar-color: #333333;
        scrollbar-color-hover: #444444;
        scrollbar-color-active: #555555;
        scrollbar-background: #111111;
        scrollbar-background-hover: #111111;
        scrollbar-background-active: #111111;
    }

    /* --- Global widget overrides --- */
    Button {
        border: none;
        min-height: 3;
        height: 3;
        text-style: none;
        padding: 1 2;
    }

    Button:hover {
        border: none;
        text-style: bold;
    }

    Button:focus {
        border: none;
        text-style: none;
    }

    Input {
        border: none;
        padding: 0 1;
        height: 1;
        background: #1a1a1a;
    }

    Input:focus {
        border: none;
    }

    TextArea {
        border: none;
    }

    TextArea:focus {
        border: none;
    }

    Select {
        border: none;
        height: 1;
    }

    Select:focus > SelectCurrent {
        border: none;
    }

    SelectCurrent {
        border: none;
    }

    #root {
        height: 1fr;
    }

    /* --- Sidebar --- */
    #sidebar {
        width: 20;
        padding: 1 1;
        background: #111111;
    }

    #sidebar Button {
        width: 100%;
        margin: 0;
        background: #161616;
        color: #666666;
        border: none;
    }

    #sidebar Button.-primary {
        background: #2a2a2a;
        color: #eeeeee;
        border: none;
    }

    #board-list {
        height: 1fr;
        background: #111111;
    }

    #board-list ListItem {
        background: #111111;
        padding: 0 1;
        margin: 0;
    }

    #board-list ListItem.is-current-board {
        background: #1a1a1a;
        color: #cccccc;
    }

    /* --- Center pane --- */
    #center {
        width: 2fr;
        padding: 0;
        background: #0c0c0c;
    }

    #status-row {
        height: auto;
    }

    #status {
        width: 1fr;
        color: #888888;
        padding: 1 1 0 1;
    }

    #timeline-order-indicator {
        width: 3;
        color: #888888;
        padding: 1 1 0 0;
        content-align: right middle;
    }

    #items {
        width: 100%;
        height: 1fr;
        background: #0c0c0c;
        border: none;
        outline: none;
        padding: 0;
        scrollbar-gutter: stable;
        scrollbar-size-vertical: 1;
        scrollbar-background: #0c0c0c;
        scrollbar-background-hover: #0c0c0c;
        scrollbar-background-active: #0c0c0c;
        scrollbar-color: #333333;
        scrollbar-color-hover: #555555;
        scrollbar-color-active: #777777;
    }

    #items > .option-list--option {
        padding: 0 1 0 1;
        background: #0c0c0c;
        color: #b8b8b8;
    }

    #items > .option-list--option-highlighted {
        background: #0c0c0c;
        color: #7eb6f5;
        text-style: bold;
    }

    #items > .option-list--option-hover {
        background: #101010;
    }

    #items:focus {
        border: none;
        outline: none;
    }

    /* --- Inspector pane --- */
    #inspector {
        width: 40;
        padding: 1 1;
        background: #111111;
    }

    #inspector-body-scroll {
        height: auto;
        max-height: 10;
    }

    #inspector-image {
        height: auto;
        max-height: 8;
        width: 100%;
    }

    #inspector-image-label {
        color: #555555;
    }

    #inspector-image-view {
        width: auto;
        background: #1a1a1a;
        color: #666666;
        border: none;
        height: 1;
        min-height: 1;
        padding: 0 2;
    }

    /* --- Compose panel --- */
    #compose-panel {
        height: 1fr;
        background: #111111;
        padding: 1 1 0 1;
    }

    #compose-board-select {
        width: 100%;
    }

    #compose-user-row {
        height: 1;
    }

    #compose-user-label {
        width: 1fr;
        color: #666666;
        padding: 0;
    }

    #compose-anon-toggle {
        width: auto;
        height: 1;
        min-height: 1;
        padding: 0 1;
        background: #1a1a1a;
        color: #666666;
        border: none;
    }

    #compose-message {
        height: 1fr;
        min-height: 3;
        background: #1a1a1a;
    }

    #compose-image-row {
        height: 1;
        max-height: 1;
        margin: 0;
    }

    #compose-image {
        width: 1fr;
        background: #0c0c0c;
        border: none;
        padding: 0;
    }

    #compose-image-paste {
        width: auto;
        height: 1;
        min-height: 1;
        padding: 0 1;
        background: #0c0c0c;
        color: #555555;
        border: none;
    }

    #compose-image-status {
        color: #555555;
        height: 1;
    }

    #search-panel {
        height: 1fr;
        background: #161616;
        padding: 1;
    }

    #search-mode-row {
        height: auto;
        layout: grid;
        grid-size: 2 1;
        grid-columns: 1fr 1fr;
        margin-bottom: 1;
    }

    #search-mode-row Button {
        width: 100%;
        min-width: 0;
        margin: 0;
        background: #161616;
        color: #555555;
        border: none;
    }

    #search-mode-row Button.-primary {
        background: #2a2a2a;
        color: #eeeeee;
        border: none;
    }

    #search-input {
        width: 100%;
        background: #1a1a1a;
        min-height: 3;
        margin-bottom: 1;
    }

    #search-panel-spacer {
        height: 1fr;
    }

    #search-action-row {
        height: auto;
    }

    #search-action-row Button {
        width: 1fr;
        background: #222222;
        color: #aaaaaa;
        border: none;
    }

    #search-submit {
        width: 100%;
        background: #222222;
        color: #aaaaaa;
        border: none;
    }

    #reply-context {
        color: #888888;
        margin-bottom: 1;
    }

    #action-btn-row {
        height: 3;
        margin-top: 1;
    }

    #action-btn-row Button {
        height: 3;
        min-height: 3;
        padding: 1 2;
        border: none;
    }

    #compose-submit {
        width: 1fr;
        background: #1a3a1a;
        color: #88aa88;
    }

    #reply-submit {
        width: 1fr;
        background: #1a2a3a;
        color: #88aacc;
    }

    #reply-cancel {
        width: 8;
        min-width: 8;
        background: #3a1a1a;
        color: #cc8888;
    }

    /* --- Search panel --- */
    .panel {
        background: #161616;
        padding: 1;
        margin-top: 1;
    }

    /* --- Profile view --- */
    #profile-view {
        width: 1fr;
        background: #0c0c0c;
        padding: 1 1;
    }

    #profile-header {
        color: #888888;
        margin-bottom: 1;
    }

    #profile-auth-row {
        height: auto;
    }

    #profile-auth-row Input {
        width: 1fr;
    }

    #profile-pin {
        max-width: 16;
    }

    #profile-btn-row {
        height: auto;
        margin-top: 1;
    }

    #profile-btn-row Button {
        width: 1fr;
        background: #222222;
        color: #aaaaaa;
        border: none;
    }

    #profile-bio-label {
        color: #555555;
        margin-top: 1;
    }

    #profile-info-section Button {
        width: 100%;
        margin-top: 1;
        background: #222222;
        color: #aaaaaa;
        border: none;
    }

    #profile-posts {
        height: 1fr;
        background: #0c0c0c;
        margin-top: 1;
    }

    #profile-posts ListItem {
        padding: 1 2;
    }

    #profile-posts ListItem.even-row {
        background: #0c0c0c;
    }

    #profile-posts ListItem.odd-row {
        background: #0a0a0a;
    }

    /* --- Utility --- */
    .hidden {
        display: none;
    }

    .section-title {
        text-style: bold;
        color: #aaaaaa;
        padding: 0 0 1 0;
    }

    .input-error {
        background: #3a1a1a;
    }

    Header {
        background: #111111;
        color: #aaaaaa;
    }

    Footer {
        background: #111111;
        color: #555555;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "show_timeline", "Timeline"),
        Binding("2", "show_users", "Users"),
        Binding("3", "show_search", "Search"),
        Binding("4", "show_profile", "Profile"),
        Binding("o", "toggle_timeline_order", "Order"),
        Binding("r", "refresh", "Refresh"),
        Binding("end", "scroll_bottom", "Bottom"),
        Binding("ctrl+v", "paste_image", "Paste Image", show=False),
    ]

    def __init__(self, backend_mode: str = "auto") -> None:
        super().__init__()
        self.backend_mode = backend_mode
        self.backend: BbsBackend = load_backend(backend_mode)
        self.section = "timeline"
        self.current_board = "general"
        self.creating_new_board = False
        self.draft_board_name = ""
        self.search_mode = "posts"
        self.current_items: list[RenderItem] = []
        self.board_items: list[str] = []
        self.selected_item: RenderItem | None = None
        self.search_selected_post: PostRecord | None = None
        self.status_message = ""
        self.reply_target: PostRecord | None = None
        self.logged_in_user: str | None = None
        self._posting_anonymous = False
        self._profile_mode = "auth"  # "auth" | "own" | "browse"
        self._boards_dirty = True
        self._timeline_dirty = True
        self._users_dirty = True
        self._last_status_text = ""
        self._last_inspector_text = ""
        self._syncing_board_controls = False
        self._syncing_board_sidebar = False
        self._sidebar_rendered_items: list[str] = []
        self.timeline_newest_first = True
        self._timeline_loaded_count = self.TIMELINE_POST_LIMIT
        self._timeline_total_posts = 0
        self._timeline_loading_more = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="root"):
            with Vertical(id="sidebar"):
                yield Static("BBS", classes="section-title")
                yield Static("", id="backend-label")
                yield Button("Timeline", id="nav-timeline", variant="primary")
                yield Button("Users", id="nav-users")
                yield Button("Search", id="nav-search")
                yield Button("Profile", id="nav-profile")
                yield Static("Boards", classes="section-title")
                yield ListView(id="board-list")
            with Vertical(id="center"):
                with Horizontal(id="status-row"):
                    yield Static("", id="status")
                    yield Static("", id="timeline-order-indicator")
                yield TimelineOptionList(id="items", preload_margin=self.TIMELINE_PRELOAD_MARGIN)
            with Vertical(id="inspector"):
                with VerticalScroll(id="inspector-body-scroll"):
                    yield Static("", id="inspector-body")
                yield Image(id="inspector-image", classes="hidden")
                yield Static("", id="inspector-image-label", classes="hidden")
                yield Button("View", id="inspector-image-view", classes="hidden")
                with Vertical(id="compose-panel", classes="panel"):
                    yield Static("Compose", classes="section-title")
                    yield Static("", id="reply-context", classes="hidden")
                    yield Select([("general", "general")], prompt="board", id="compose-board-select", allow_blank=True)
                    yield Input(placeholder="new board name", id="compose-board-new", classes="hidden")
                    with Horizontal(id="compose-user-row"):
                        yield Static("", id="compose-user-label")
                        yield Button("Anonymous", id="compose-anon-toggle")
                    yield TextArea(id="compose-message", language=None)
                    with Horizontal(id="compose-image-row"):
                        yield Input(placeholder="image path", id="compose-image")
                        yield Button("Paste", id="compose-image-paste")
                    yield Static("", id="compose-image-status", classes="hidden")
                    with Horizontal(id="action-btn-row"):
                        yield Button("Post", id="compose-submit", variant="success")
                        yield Button("Reply", id="reply-submit", variant="warning")
                        yield Button("X", id="reply-cancel", variant="error")
                with Vertical(id="search-panel", classes="panel hidden"):
                    yield Static("Search", classes="section-title")
                    with Horizontal(id="search-mode-row"):
                        yield Button("Posts", id="search-mode-posts", variant="primary")
                        yield Button("Users", id="search-mode-users")
                    yield Input(placeholder="keyword", id="search-input")
                    yield Static("", id="search-panel-spacer")
                    with Horizontal(id="search-action-row"):
                        yield Button("Search", id="search-submit")
                        yield Button("Back", id="search-back", classes="hidden")
                        yield Button("Go to Board", id="search-go-board", classes="hidden")
                        yield Button("Go to Profile", id="search-go-profile", classes="hidden")
            with VerticalScroll(id="profile-view", classes="hidden"):
                yield Static("Profile", classes="section-title")
                yield Static("", id="profile-header")
                with Vertical(id="profile-auth-section"):
                    with Horizontal(id="profile-auth-row"):
                        yield Input(placeholder="username", id="profile-search")
                        yield Input(placeholder="pin", id="profile-pin")
                    with Horizontal(id="profile-btn-row"):
                        yield Button("Load", id="profile-load")
                        yield Button("Create", id="profile-create")
                with Vertical(id="profile-info-section", classes="hidden"):
                    yield Static("", id="profile-bio-label")
                    yield Input(placeholder="bio", id="profile-bio")
                    yield Button("Save Bio", id="profile-save-bio")
                    yield Static("Posts", classes="section-title")
                    yield ListView(id="profile-posts")
                    yield Button("Logout", id="profile-logout")
        yield Footer()

    async def on_mount(self) -> None:
        self._refresh_backend_label()
        self._sync_timeline_order_indicator()
        self.query_one("#reply-submit", Button).display = False
        self.query_one("#reply-cancel", Button).display = False
        await self._refresh_board_list()
        await self._show_section("timeline")

    def _refresh_backend_label(self) -> None:
        self.query_one("#backend-label", Static).update(
            f"Backend: {self.backend.label} ({self.backend.kind})"
        )

    async def _refresh_board_list(self) -> None:
        boards = self.backend.list_boards()
        if not self._boards_dirty and boards == self.board_items:
            await self._sync_board_controls()
            return

        self.board_items = list(boards)
        if self.current_board not in self.board_items and self.board_items:
            self.current_board = self.board_items[0]
        await self._sync_board_controls()
        self._boards_dirty = False

    def _format_inspector(self, text: str) -> None:
        if text == self._last_inspector_text:
            return
        self._last_inspector_text = text
        self.query_one("#inspector-body", Static).update(text)

    def _update_inspector_image(self, post: PostRecord) -> None:
        from pathlib import Path as _Path
        image_widget = self.query_one("#inspector-image", Image)
        label_widget = self.query_one("#inspector-image-label", Static)
        if post.has_attachment:
            info = self.backend.get_attachment_info(post.id)
            if info and _Path(info["path"]).exists():
                image_widget.image = info["path"]
                image_widget.display = True
                size_mb = info["size_bytes"] / (1024 * 1024)
                label_widget.update(f"{info['original_name']}  \u00b7  {size_mb:.1f} MB")
                label_widget.display = True
                self.query_one("#inspector-image-view", Button).display = True
                return
        image_widget.display = False
        label_widget.display = False
        self.query_one("#inspector-image-view", Button).display = False

    def _hide_inspector_image(self) -> None:
        self.query_one("#inspector-image").display = False
        self.query_one("#inspector-image-label").display = False
        self.query_one("#inspector-image-view").display = False

    def _set_status(self, text: str) -> None:
        if text == self._last_status_text:
            return
        self._last_status_text = text
        self.status_message = text
        self.query_one("#status", Static).update(text)

    def _posting_username(self) -> str:
        if not self.logged_in_user:
            return "anonymous"
        return "anonymous" if self._posting_anonymous else self.logged_in_user

    def _selected_compose_board(self) -> str:
        select = self.query_one("#compose-board-select", Select)
        if select.value == "__new__":
            board = self.query_one("#compose-board-new", Input).value.strip()
        else:
            board = str(select.value) if select.value != Select.BLANK else self.current_board
        return board or self.current_board

    def _display_board_name(self) -> str:
        return self.draft_board_name or self.current_board

    def _timeline_history_edge(self) -> str:
        return "bottom" if self.timeline_newest_first else "top"

    def _sync_timeline_order_indicator(self) -> None:
        self.query_one("#timeline-order-indicator", Static).update(
            "↓" if self.timeline_newest_first else "↑"
        )
        self.query_one("#items", TimelineOptionList).set_history_edge(self._timeline_history_edge())

    def _display_board_items(self) -> list[str]:
        if not self.draft_board_name or self.draft_board_name in self.board_items:
            return list(self.board_items)
        return [*self.board_items, self.draft_board_name]

    def _clear_compose_message(self) -> None:
        self.query_one("#compose-message", TextArea).clear()
        self.query_one("#compose-image", Input).value = ""
        self.query_one("#compose-image-status", Static).display = False

    async def action_paste_image(self) -> None:
        """Ctrl+V handler: paste image from clipboard, or fall through to text paste."""
        import subprocess

        # Only try image paste if compose panel is visible
        if self.section not in ("timeline", "boards"):
            await self._paste_text_from_clipboard()
            return

        # Check clipboard for image data
        try:
            result = subprocess.run(
                ["wl-paste", "--list-types"],
                capture_output=True, text=True, timeout=3,
            )
            types = result.stdout.strip().split("\n") if result.returncode == 0 else []
        except (FileNotFoundError, subprocess.TimeoutExpired):
            await self._paste_text_from_clipboard()
            return

        has_image = any(t.startswith("image/") for t in types)
        if has_image:
            await self._paste_image_from_clipboard(types)
        else:
            await self._paste_text_from_clipboard()

    async def _paste_text_from_clipboard(self) -> None:
        """Fall through: paste text into the focused widget."""
        import subprocess
        try:
            result = subprocess.run(
                ["wl-paste", "--no-newline"],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0 and result.stdout:
                focused = self.focused
                if isinstance(focused, Input):
                    focused.insert_text_at_cursor(result.stdout)
                elif isinstance(focused, TextArea):
                    focused.insert(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    async def _paste_image_from_clipboard(self, clipboard_types: list[str] | None) -> None:
        """Grab image data from clipboard via wl-paste and save to uploads."""
        import subprocess
        import time
        from app_paths import get_uploads_dir

        status = self.query_one("#compose-image-status", Static)
        image_input = self.query_one("#compose-image", Input)

        # Fetch clipboard types if not provided
        if clipboard_types is None:
            try:
                result = subprocess.run(
                    ["wl-paste", "--list-types"],
                    capture_output=True, text=True, timeout=3,
                )
                clipboard_types = result.stdout.strip().split("\n") if result.returncode == 0 else []
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._set_status("wl-paste not available")
                return

        # Find the best image type
        image_type = None
        for t in clipboard_types:
            if t.startswith("image/"):
                image_type = t
                break

        if not image_type:
            self._set_status("No image in clipboard")
            return

        ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp", "image/bmp": ".bmp"}
        ext = ext_map.get(image_type, ".png")

        uploads_dir = get_uploads_dir()
        dest = uploads_dir / f"pasted_{int(time.time())}{ext}"

        try:
            result = subprocess.run(
                ["wl-paste", "--type", image_type],
                capture_output=True, timeout=10,
            )
            if result.returncode != 0 or not result.stdout:
                self._set_status("Failed to read clipboard image")
                return
            dest.write_bytes(result.stdout)
        except (subprocess.TimeoutExpired, OSError) as e:
            self._set_status(f"Clipboard error: {e}")
            return

        image_input.value = str(dest)
        size_kb = len(result.stdout) / 1024
        status.update(f"Image pasted ({size_kb:.0f} KB)")
        status.display = True
        self._set_status("Image pasted from clipboard")

    def _reset_new_board_input(self) -> None:
        new_board = self.query_one("#compose-board-new", Input)
        new_board.value = ""
        new_board.display = False
        self.creating_new_board = False
        self.draft_board_name = ""

    def _mark_content_dirty(self, *, boards: bool = False, users: bool = False) -> None:
        self._timeline_dirty = True
        self._boards_dirty = self._boards_dirty or boards
        self._users_dirty = self._users_dirty or users

    def _show_only(self, *panel_ids: str) -> None:
        for panel_id in ("search-panel",):
            widget = self.query_one(f"#{panel_id}")
            widget.display = panel_id in panel_ids

    def _show_compose_panel(self, visible: bool) -> None:
        self.query_one("#compose-panel").display = visible

    def _read_posts_window(self, board: str, limit: int) -> list[PostRecord]:
        try:
            return self.backend.read_posts(board, limit=limit)
        except TypeError:
            return self.backend.read_posts(board)[-limit:]

    def _read_user_posts_window(self, username: str, limit: int) -> list[PostRecord]:
        try:
            return self.backend.get_user_posts(username, limit=limit)
        except TypeError:
            return self.backend.get_user_posts(username)[-limit:]

    def _sync_search_mode_buttons(self) -> None:
        self.query_one("#search-mode-posts", Button).variant = (
            "primary" if self.search_mode == "posts" else "default"
        )
        self.query_one("#search-mode-users", Button).variant = (
            "primary" if self.search_mode == "users" else "default"
        )

    def _ordered_timeline_posts(self, posts: list[PostRecord]) -> list[PostRecord]:
        return list(reversed(posts)) if self.timeline_newest_first else posts

    def _timeline_default_index(self, item_count: int) -> int | None:
        if item_count <= 0:
            return None
        return 0 if self.timeline_newest_first else item_count - 1

    def _timeline_should_load_more_at_index(self, index: int) -> bool:
        threshold = self.TIMELINE_PRELOAD_MARGIN
        return (
            index >= len(self.current_items) - threshold
            if self.timeline_newest_first
            else index < threshold
        )

    def _post_summary_lines(
        self,
        post: PostRecord,
        *,
        posts_by_id: dict[int, PostRecord] | None = None,
        include_board: bool = False,
    ) -> str:
        lines = format_post_summary(post, include_board=include_board)
        if post.parent_post_id is None:
            return lines
        parent = None if posts_by_id is None else posts_by_id.get(post.parent_post_id)
        if parent:
            return format_reply_quote(parent) + "\n" + lines
        return f"[#555555]↩ reply to #{post.parent_post_id}[/]\n" + lines

    def _visible_posts_by_id(self) -> dict[int, PostRecord]:
        posts_by_id: dict[int, PostRecord] = {}
        for render_item in self.current_items:
            if render_item.kind == "post" and isinstance(render_item.value, PostRecord):
                posts_by_id[render_item.value.id] = render_item.value
        return posts_by_id

    def _latest_board_post(self, board: str) -> PostRecord | None:
        posts = self._read_posts_window(board, 1)
        if not posts:
            return None
        return posts[-1]

    def _option_id_for_item(self, render_item: RenderItem, index: int) -> str:
        if render_item.kind == "post" and isinstance(render_item.value, PostRecord):
            return f"post:{render_item.value.id}"
        return f"{render_item.kind}:{index}"

    def _prompt_for_render_item(
        self,
        render_item: RenderItem,
        index: int,
        *,
        posts_by_id: dict[int, PostRecord] | None = None,
        include_board: bool = False,
    ) -> str:
        if render_item.kind == "post" and isinstance(render_item.value, PostRecord):
            lines = self._post_summary_lines(
                render_item.value,
                posts_by_id=posts_by_id,
                include_board=include_board,
            )
            if self.reply_target is not None and render_item.value.id == self.reply_target.id:
                return f"[#7eb6f5]▎[/] {lines}"
            return lines
        return escape_display_text(render_item.label)

    def _sync_main_option_prompts(self) -> None:
        items = self.query_one("#items", TimelineOptionList)
        if items.option_count != len(self.current_items):
            return
        posts_by_id = self._visible_posts_by_id()
        include_board = self.section == "search"
        for index, render_item in enumerate(self.current_items):
            items.replace_option_prompt_at_index(
                index,
                self._prompt_for_render_item(
                    render_item,
                    index,
                    posts_by_id=posts_by_id,
                    include_board=include_board,
                ),
            )

    def _set_main_options(self, *, include_board: bool = False) -> None:
        items = self.query_one("#items", TimelineOptionList)
        posts_by_id = self._visible_posts_by_id()
        options = [
            Option(
                self._prompt_for_render_item(
                    render_item,
                    index,
                    posts_by_id=posts_by_id,
                    include_board=include_board,
                ),
                id=self._option_id_for_item(render_item, index),
            )
            for index, render_item in enumerate(self.current_items)
        ]
        items.set_options(options)

    async def _set_items_index(self, index: int | None) -> None:
        items = self.query_one("#items", TimelineOptionList)
        with items.prevent(TimelineOptionList.OptionHighlighted, TimelineOptionList.OptionSelected):
            items.index = index

    async def _set_timeline_focus(self, highlight_post_id: int | None = None) -> None:
        items = self.query_one("#items", TimelineOptionList)
        if items.option_count == 0:
            return
        if highlight_post_id is not None:
            for index, render_item in enumerate(self.current_items):
                if (
                    render_item.kind == "post"
                    and isinstance(render_item.value, PostRecord)
                    and render_item.value.id == highlight_post_id
                    ):
                        await self._set_items_index(index)
                        return
        await self._set_items_index(self._timeline_default_index(items.option_count))

    async def _insert_post_into_timeline(self, post: PostRecord) -> None:
        render_item = RenderItem("post", post.username, post)

        if self.timeline_newest_first:
            self.current_items.insert(0, render_item)
            if len(self.current_items) > self._timeline_loaded_count:
                self.current_items.pop()
        else:
            self.current_items.append(render_item)
            if len(self.current_items) > self._timeline_loaded_count:
                self.current_items.pop(0)

        self._set_main_options()
        await self._set_items_index(0 if self.timeline_newest_first else len(self.current_items) - 1)
        self.selected_item = render_item
        self._format_inspector(format_post_detail(post))

    async def _load_more_timeline_posts(
        self,
        *,
        anchor_post_id: int | None = None,
        preserve_viewport: bool = False,
    ) -> None:
        if (
            self._timeline_loading_more
            or self._timeline_total_posts <= len(self.current_items)
            or not self.current_items
            or self.current_items[0].kind != "post"
        ):
            return
        self._timeline_loading_more = True
        try:
            items = self.query_one("#items", TimelineOptionList)
            previous_scroll_y = items.scroll_y
            previous_max_scroll_y = items.max_scroll_y
            self._timeline_loaded_count = min(
                self._timeline_total_posts,
                self._timeline_loaded_count + self.TIMELINE_POST_LIMIT,
            )
            posts = self._ordered_timeline_posts(
                self._read_posts_window(self.current_board, self._timeline_loaded_count)
            )
            if len(posts) == len(self.current_items):
                items.arm_history_preload()
                return

            self.current_items = [
                RenderItem("post", post.username, post)
                for post in posts
            ]
            self._set_main_options()

            def restore_scroll_position() -> None:
                timeline_items = self.query_one("#items", TimelineOptionList)
                target_scroll_y = previous_scroll_y
                if not self.timeline_newest_first:
                    target_scroll_y = previous_scroll_y + max(
                        0,
                        timeline_items.max_scroll_y - previous_max_scroll_y,
                    )
                timeline_items.scroll_to(
                    y=target_scroll_y,
                    animate=False,
                    force=True,
                    immediate=True,
                )
                timeline_items.arm_history_preload()

            if anchor_post_id is not None:
                await self._set_timeline_focus(anchor_post_id)
                if preserve_viewport:
                    restore_scroll_position()
                else:
                    items.arm_history_preload()
            else:
                if not items.call_after_refresh(restore_scroll_position):
                    restore_scroll_position()
        finally:
            self._timeline_loading_more = False

    def _set_search_detail_actions_visible(self, visible: bool) -> None:
        self.query_one("#search-submit", Button).display = not visible
        self.query_one("#search-back", Button).display = visible
        self.query_one("#search-go-board", Button).display = visible
        self.query_one("#search-go-profile", Button).display = visible

    def _clear_search_selected_post(self) -> None:
        self.search_selected_post = None
        self._set_search_detail_actions_visible(False)
        keyword = self.query_one("#search-input", Input).value.strip()
        if keyword:
            self._format_inspector(
                f"User search results for: {keyword}"
                if self.search_mode == "users"
                else f"Search results for: {keyword}"
            )
            self._set_status(
                f"Search users: {keyword}"
                if self.search_mode == "users"
                else f"Search posts: {keyword}"
            )
            self._hide_inspector_image()
            return
        self._format_inspector(f"Enter a keyword and search {self.search_mode}.")
        self._set_status(f"Search mode: {self.search_mode}")
        self._hide_inspector_image()

    def _set_search_selected_post(self, post: PostRecord) -> None:
        self.search_selected_post = post
        self._set_search_detail_actions_visible(True)
        self._format_inspector(format_post_detail(post))
        self._update_inspector_image(post)
        self._set_status(
            f"Search hit #{post.board_seq if post.board_seq else post.id} in /{post.board}"
        )

    async def _open_profile_view(self, username: str) -> None:
        self.section = "profile"
        self.query_one("#center").display = False
        self.query_one("#inspector").display = False
        self.query_one("#profile-view").display = True
        self._set_profile_mode("browse")
        self.query_one("#profile-header", Static).update("")
        await self._load_profile_view(username)
        for sec, btn_id in {
            "timeline": "nav-timeline",
            "users": "nav-users",
            "search": "nav-search",
            "profile": "nav-profile",
        }.items():
            self.query_one(f"#{btn_id}", Button).variant = "primary" if sec == "profile" else "default"
        self._set_status(f"Viewing @{escape_display_text(username)}")

    async def _go_to_search_post_board(self, post: PostRecord) -> None:
        await self._set_current_board(post.board, show_timeline=True)
        if self.reply_target is not None:
            self._clear_reply_target()
        items = self.query_one("#items", TimelineOptionList)
        for index, render_item in enumerate(self.current_items):
            if (
                render_item.kind == "post"
                and isinstance(render_item.value, PostRecord)
                and render_item.value.id == post.id
            ):
                self.selected_item = render_item
                await self._set_items_index(index)
                self._format_inspector(format_post_detail(post))
                self._set_status(
                    f"/{post.board}  ·  Post #{post.board_seq if post.board_seq else post.id}"
                )
                return

    async def _sync_board_sidebar(self) -> None:
        display_items = self._display_board_items()
        board_list = self.query_one("#board-list", ListView)
        selected_index = None
        if self.creating_new_board and self.draft_board_name and display_items:
            selected_index = len(display_items) - 1
        elif self.current_board in self.board_items:
            selected_index = self.board_items.index(self.current_board)

        existing_children = list(board_list.children)
        if display_items != self._sidebar_rendered_items or len(existing_children) != len(display_items):
            new_items = [
                ListItem(Static(escape_display_text(board_name)))
                for board_name in display_items
            ]
            self._syncing_board_sidebar = True
            await board_list.clear()
            await board_list.mount_all(new_items)
            self._syncing_board_sidebar = False
            self._sidebar_rendered_items = list(display_items)
            existing_children = list(board_list.children)

        for index, item in enumerate(existing_children):
            item.set_class(index == selected_index, "is-current-board")
        if selected_index is not None:
            with board_list.prevent(ListView.Selected):
                board_list.index = selected_index

    def _set_compose_board_value(self, value: object) -> None:
        select = self.query_one("#compose-board-select", Select)
        self._syncing_board_controls = True
        with select.prevent(Select.Changed):
            select.value = value
        self._syncing_board_controls = False

    async def _sync_board_controls(self) -> None:
        new_board_label = self.draft_board_name or "+ New Board"
        options = [(b, b) for b in self.board_items]
        options.append((new_board_label, "__new__"))
        select = self.query_one("#compose-board-select", Select)
        self._syncing_board_controls = True
        with select.prevent(Select.Changed):
            select.set_options(options)
        self._syncing_board_controls = False
        if self.creating_new_board:
            self._set_compose_board_value("__new__")
        elif self.current_board in self.board_items:
            self._set_compose_board_value(self.current_board)
        else:
            self._set_compose_board_value(Select.BLANK)
        await self._sync_board_sidebar()

    async def _set_current_board(
        self,
        board_name: str,
        *,
        refresh_timeline: bool = True,
        show_timeline: bool = False,
    ) -> None:
        if not board_name or board_name not in self.board_items:
            return
        board_changed = board_name != self.current_board
        if self.creating_new_board or self.draft_board_name:
            self._reset_new_board_input()
        self.current_board = board_name
        if board_changed:
            self._timeline_loaded_count = self.TIMELINE_POST_LIMIT
        self._set_compose_board_value(board_name)
        await self._sync_board_sidebar()
        if show_timeline:
            if board_changed:
                self._timeline_dirty = True
            if self.section == "timeline":
                if board_changed:
                    await self._refresh_timeline()
                return
            await self._show_section("timeline")
            return
        if refresh_timeline and board_changed:
            self._timeline_dirty = True
            await self._refresh_timeline()

    def _sync_compose_username(self) -> None:
        label = self.query_one("#compose-user-label", Static)
        anon_btn = self.query_one("#compose-anon-toggle", Button)
        if self.logged_in_user:
            if self._posting_anonymous:
                label.update("[#888888]posting as [bold]anonymous[/bold][/]")
                anon_btn.label = escape_display_text(self.logged_in_user)
            else:
                label.update(f"[#e0e0e0]posting as [bold]@{_safe_markup(self.logged_in_user)}[/bold][/]")
                anon_btn.label = "Anonymous"
            anon_btn.display = True
        else:
            label.update("[#888888]posting as [bold]anonymous[/bold][/]")
            anon_btn.display = False

    def _set_profile_mode(self, mode: str, username: str = "") -> None:
        self._profile_mode = mode
        auth = self.query_one("#profile-auth-section")
        info = self.query_one("#profile-info-section")
        bio_input = self.query_one("#profile-bio", Input)
        save_btn = self.query_one("#profile-save-bio", Button)
        logout_btn = self.query_one("#profile-logout", Button)
        if mode == "auth":
            auth.display = True
            info.display = False
        elif mode == "own":
            auth.display = False
            info.display = True
            bio_input.disabled = False
            save_btn.display = True
            logout_btn.display = True
        elif mode == "browse":
            auth.display = False
            info.display = True
            bio_input.disabled = True
            save_btn.display = False
            logout_btn.display = False

    async def _render_posts(self, posts: list[PostRecord], *, include_board: bool = False) -> None:
        self.current_items = [RenderItem("post", post.username, post) for post in posts]
        self._set_main_options(include_board=include_board)

    async def _render_boards(self) -> None:
        self.current_items = [RenderItem("board", board, board) for board in self.board_items]
        self._set_main_options()
        self._format_inspector(
            "Choose a board from the list or the sidebar. The current timeline tracks the selected board."
        )
        self._hide_inspector_image()

    async def _render_users(self) -> None:
        self.current_items = [
            RenderItem("user", username, username) for username in self.backend.list_users()
        ]
        self._set_main_options()
        self._format_inspector("Select a user to inspect their profile details.")
        self._hide_inspector_image()
        self._users_dirty = False

    async def _render_user_results(self, users: list[str]) -> None:
        self.current_items = [RenderItem("user", username, username) for username in users]
        self._set_main_options()
        await self._set_items_index(None)

    async def _refresh_timeline(self) -> None:
        info = self.backend.get_board_info(self.current_board)
        self._timeline_total_posts = info.post_count if info else 0
        window_size = min(
            max(self._timeline_loaded_count, self.TIMELINE_POST_LIMIT),
            self._timeline_total_posts if self._timeline_total_posts > 0 else self.TIMELINE_POST_LIMIT,
        )
        self._timeline_loaded_count = window_size
        posts = self._ordered_timeline_posts(
            self._read_posts_window(self.current_board, self._timeline_loaded_count)
        )
        await self._render_posts(posts)
        self._sync_timeline_order_indicator()
        await self._set_timeline_focus()
        items = self.query_one("#items", TimelineOptionList)
        if self.timeline_newest_first:
            items.scroll_home(animate=False)
        else:
            items.scroll_end(animate=False)
        items.arm_history_preload()
        self._set_compose_board_value("__new__" if self.creating_new_board else self.current_board)
        self._sync_compose_username()
        if info and info.post_count > 0:
            self._format_inspector(
                (
                    f"/{_safe_markup(info.slug)}  ·  {info.post_count} posts"
                    f"{f'  ·  showing latest {len(posts)}' if info.post_count > len(posts) else ''}"
                    f"  ·  est. {_format_timestamp(info.created_at)} by {_safe_markup(info.created_by)}"
                )
            )
            if info.post_count > len(posts):
                self._set_status(
                    f"/{self._display_board_name()} (showing latest {len(posts)} of {info.post_count})"
                )
            else:
                self._set_status(f"/{self._display_board_name()}")
        else:
            self._format_inspector(f"/{self._display_board_name()}  ·  No posts yet")
            self._set_status(f"/{self._display_board_name()}")
        self._hide_inspector_image()
        self._timeline_dirty = False

    async def _refresh_search_results(self, keyword: str) -> None:
        if self.search_mode == "users":
            users = self.backend.search_users(keyword)
            total_users = len(users)
            visible_users = users[: self.SEARCH_RESULT_LIMIT]
            await self._render_user_results(visible_users)
            if total_users > self.SEARCH_RESULT_LIMIT:
                self._format_inspector(
                    f"User search results for: {keyword}\nShowing first {self.SEARCH_RESULT_LIMIT} of {total_users}. Narrow the query for more."
                )
                self._set_status(
                    f"Search users: {keyword} (showing first {self.SEARCH_RESULT_LIMIT} of {total_users})"
                )
            else:
                self._format_inspector(f"User search results for: {keyword}")
                self._set_status(f"Search users: {keyword}")
            return

        posts = self.backend.search_posts(keyword)
        total_posts = len(posts)
        visible_posts = posts[: self.SEARCH_RESULT_LIMIT]
        await self._render_posts(visible_posts, include_board=True)
        if total_posts > self.SEARCH_RESULT_LIMIT:
            self._format_inspector(
                f"Search results for: {keyword}\nShowing first {self.SEARCH_RESULT_LIMIT} of {total_posts}. Narrow the query for more."
            )
            self._set_status(
                f"Search posts: {keyword} (showing first {self.SEARCH_RESULT_LIMIT} of {total_posts})"
            )
        else:
            self._format_inspector(f"Search results for: {keyword}")
            self._set_status(f"Search posts: {keyword}")

    async def _show_section(self, section: str) -> None:
        previous_section = self.section
        self.section = section
        self._show_only()
        self._clear_reply_target()
        if section != "search":
            self.search_selected_post = None
            self._set_search_detail_actions_visible(False)

        nav_buttons = {
            "timeline": "nav-timeline",
            "users": "nav-users",
            "search": "nav-search",
            "profile": "nav-profile",
        }
        for sec, btn_id in nav_buttons.items():
            btn = self.query_one(f"#{btn_id}", Button)
            btn.variant = "primary" if sec == section else "default"

        # Toggle center+inspector vs profile-view (sidebar always visible)
        is_profile = section == "profile"
        self.query_one("#center").display = not is_profile
        self.query_one("#inspector").display = not is_profile
        self.query_one("#profile-view").display = is_profile

        # Compose panel visible during timeline and boards views
        show_compose = section in ("timeline", "boards")
        self._show_compose_panel(show_compose)

        if section == "timeline":
            if previous_section != "timeline" or self._timeline_dirty:
                await self._refresh_timeline()
        elif section == "boards":
            if previous_section != "boards" or self._boards_dirty:
                await self._render_boards()
        elif section == "users":
            if previous_section != "users" or self._users_dirty:
                await self._render_users()
        elif section == "search":
            self._show_only("search-panel")
            self._sync_search_mode_buttons()
            self._clear_search_selected_post()
        elif section == "profile":
            if self.logged_in_user:
                self._set_profile_mode("own")
                await self._load_profile_view(self.logged_in_user)
                self._set_status(f"Profile: @{escape_display_text(self.logged_in_user)}")
            else:
                self._set_profile_mode("auth")
                self.query_one("#profile-header", Static).update("")
                self._set_status("Profile — log in or create account")
        else:
            self._set_status(section)

    def _set_reply_target(self, post: PostRecord) -> None:
        self.reply_target = post
        if self.creating_new_board or self.draft_board_name:
            self._reset_new_board_input()
        self.current_board = post.board
        self._set_compose_board_value(post.board)
        self.query_one("#compose-board-select", Select).display = False
        self.query_one("#compose-board-new", Input).display = False
        self.query_one("#compose-image-row").display = False
        self.query_one("#compose-image-status", Static).display = False
        seq = post.board_seq if post.board_seq else post.id
        # Show reply context in compose panel
        ctx = self.query_one("#reply-context", Static)
        ctx.update(
            f"[#888888]↩ Replying to [bold]#{seq}[/bold] by @{_safe_markup(post.username)}[/]\n"
            f"[#555555]  \"{_safe_markup(post.message[:60] + ('...' if len(post.message) > 60 else ''))}\"[/]"
        )
        ctx.display = True
        # Show reply + cancel, hide post
        self.query_one("#compose-submit", Button).display = False
        self.query_one("#reply-submit", Button).display = True
        self.query_one("#reply-cancel", Button).display = True
        self._clear_compose_message()
        self._sync_main_option_prompts()
        self.query_one("#inspector-body-scroll").display = False
        self._hide_inspector_image()
        self._set_status(f"Replying to #{seq}")

    def _clear_reply_target(self) -> None:
        self.reply_target = None
        self.query_one("#compose-board-select", Select).display = True
        self.query_one("#reply-context", Static).display = False
        self.query_one("#compose-submit", Button).display = True
        self.query_one("#reply-submit", Button).display = False
        self.query_one("#reply-cancel", Button).display = False
        self.query_one("#compose-image-row").display = True
        self.query_one("#inspector-body-scroll").display = True
        self._sync_main_option_prompts()

    async def action_show_timeline(self) -> None:
        await self._show_section("timeline")

    async def action_show_boards(self) -> None:
        await self._show_section("boards")

    async def action_show_users(self) -> None:
        await self._show_section("users")

    async def action_show_search(self) -> None:
        await self._show_section("search")
        self.query_one("#search-input", Input).focus()

    async def action_show_profile(self) -> None:
        await self._show_section("profile")
        self.query_one("#profile-search", Input).focus()

    async def action_toggle_timeline_order(self) -> None:
        self.timeline_newest_first = not self.timeline_newest_first
        self._timeline_dirty = True
        self._sync_timeline_order_indicator()
        if self.section == "timeline":
            await self._refresh_timeline()
        else:
            self._set_status(f"/{self._display_board_name()}")

    async def action_refresh(self) -> None:
        self._boards_dirty = True
        self._timeline_dirty = True
        self._users_dirty = True
        await self._refresh_board_list()
        await self._show_section(self.section)

    async def action_scroll_bottom(self) -> None:
        items = self.query_one("#items", TimelineOptionList)
        if items.option_count:
            items.index = self._timeline_default_index(items.option_count)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "nav-timeline":
            await self.action_show_timeline()
        elif button_id == "nav-users":
            await self.action_show_users()
        elif button_id == "nav-search":
            await self.action_show_search()
        elif button_id == "nav-profile":
            await self.action_show_profile()
        elif button_id == "compose-anon-toggle":
            self._posting_anonymous = not self._posting_anonymous
            self._sync_compose_username()
        elif button_id == "compose-image-paste":
            await self._paste_image_from_clipboard(None)
        elif button_id == "compose-submit":
            await self._submit_compose()
        elif button_id == "reply-cancel":
            self._clear_reply_target()
            info = self.backend.get_board_info(self.current_board)
            if info and info.post_count > 0:
                self._format_inspector(
                    f"/{_safe_markup(info.slug)}  ·  {info.post_count} posts  ·  est. {_format_timestamp(info.created_at)} by {_safe_markup(info.created_by)}"
                )
            else:
                self._format_inspector(f"/{self._display_board_name()}  ·  No posts yet")
            self._hide_inspector_image()
            self._set_status(f"/{self.current_board}")
        elif button_id == "search-mode-posts":
            self.search_mode = "posts"
            self._sync_search_mode_buttons()
            self._clear_search_selected_post()
        elif button_id == "search-mode-users":
            self.search_mode = "users"
            self._sync_search_mode_buttons()
            self._clear_search_selected_post()
        elif button_id == "search-submit":
            await self._submit_search()
        elif button_id == "search-back":
            self._clear_search_selected_post()
        elif button_id == "search-go-board":
            if self.search_selected_post is not None:
                await self._go_to_search_post_board(self.search_selected_post)
        elif button_id == "search-go-profile":
            if self.search_selected_post is not None:
                await self._open_profile_view(self.search_selected_post.username)
        elif button_id == "profile-load":
            await self._submit_profile_load()
        elif button_id == "profile-create":
            await self._submit_profile_create()
        elif button_id == "profile-save-bio":
            username = self.query_one("#profile-search", Input).value.strip()
            bio = self.query_one("#profile-bio", Input).value.strip()
            if username:
                self.backend.set_bio(username, bio)
                self._set_status(f"Bio updated for @{escape_display_text(username)}")
        elif button_id == "profile-logout":
            self.logged_in_user = None
            self._posting_anonymous = False
            self._set_profile_mode("auth")
            self.query_one("#profile-header", Static).update("")
            self.query_one("#profile-search", Input).value = ""
            self.query_one("#profile-pin", Input).value = ""
            self._sync_compose_username()
            self._set_status("Logged out.")
        elif button_id == "reply-submit":
            await self._submit_reply()
        elif button_id == "inspector-image-view":
            if self.selected_item and isinstance(self.selected_item.value, PostRecord):
                post = self.selected_item.value
                if post.has_attachment:
                    info = self.backend.get_attachment_info(post.id)
                    if info:
                        from pathlib import Path as _Path
                        if _Path(info["path"]).exists():
                            self.push_screen(ImageLightboxScreen(info["path"], info["original_name"], info["size_bytes"]))

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id or ""
        if input_id == "compose-board-new":
            await self._submit_compose()
        elif input_id == "search-input":
            await self._submit_search()
        elif input_id in ("profile-search", "profile-pin"):
            await self._submit_profile_load()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if self._syncing_board_controls:
            return
        if event.select.id == "compose-board-select" and self.section in ("timeline", "boards"):
            new_inputs = list(self.query("#compose-board-new"))
            if not new_inputs:
                return
            new_input = new_inputs[0]
            if (
                new_input.display
                and (self.creating_new_board or self.draft_board_name)
                and (
                    event.select.value == "__new__"
                    or event.value == self.current_board
                    or event.value not in (*self.board_items, "__new__")
                )
            ):
                event.select.value = "__new__"
                return
            if event.value == "__new__":
                new_input.display = True
                new_input.value = ""
                self.creating_new_board = True
                self.draft_board_name = ""
                new_input.focus()
            else:
                new_input.display = False
                self.creating_new_board = False
                self.draft_board_name = ""
                board_name = str(event.value)
                if board_name and board_name in self.board_items:
                    event.select.value = board_name
                    await self._set_current_board(board_name)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "compose-board-new" and self.section in ("timeline", "boards"):
            board_name = event.input.value.strip()
            self.draft_board_name = board_name
            await self._sync_board_sidebar()
            if not board_name:
                self._set_status(f"/{self.current_board}")
                return
            items = self.query_one("#items", TimelineOptionList)
            items.clear_options()
            self.current_items = []
            self._format_inspector(f"/{board_name}  ·  New board (post to create)")
            self._set_status(f"/{board_name} (new)")

    @on(TimelineOptionList.OptionHighlighted)
    async def on_option_list_option_highlighted(self, event: TimelineOptionList.OptionHighlighted) -> None:
        if (
            self.section != "timeline"
            or event.option_list.id != "items"
            or not self.current_items
            or self.current_items[0].kind != "post"
        ):
            return
        current_index = event.option_index
        if current_index is None:
            return
        if not self._timeline_should_load_more_at_index(current_index):
            return
        highlight_post = self.current_items[current_index].value
        await self._load_more_timeline_posts(
            anchor_post_id=highlight_post.id if isinstance(highlight_post, PostRecord) else None
        )

    async def on_timeline_history_edge_reached(self, message: TimelineHistoryEdgeReached) -> None:
        if self.section != "timeline" or message.option_list.id != "items":
            return
        anchor_index = len(self.current_items) - 1 if self.timeline_newest_first else 0
        anchor_post = self.current_items[anchor_index].value if self.current_items else None
        await self._load_more_timeline_posts(
            anchor_post_id=anchor_post.id if isinstance(anchor_post, PostRecord) else None,
            preserve_viewport=True,
        )

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "board-list":
            if self._syncing_board_sidebar:
                return
            if 0 <= event.index < len(self.board_items):
                await self._set_current_board(
                    self.board_items[event.index],
                    show_timeline=True,
                )
            return
        if event.list_view.id == "profile-posts":
            return

    @on(TimelineOptionList.OptionSelected)
    async def on_option_list_option_selected(self, event: TimelineOptionList.OptionSelected) -> None:
        if event.option_list.id != "items" or not self.current_items:
            return
        item = self.current_items[event.option_index]
        self.selected_item = item
        if item.kind == "post" and isinstance(item.value, PostRecord):
            if self.section == "search":
                self._set_search_selected_post(item.value)
                return
            self._format_inspector(format_post_detail(item.value))
            self._update_inspector_image(item.value)
            if self.backend.capabilities.supports_threads:
                self._set_reply_target(item.value)
            else:
                self._clear_reply_target()
            self._set_status(f"Post #{item.value.board_seq if item.value.board_seq else item.value.id}")
        elif item.kind == "board":
            await self._set_current_board(str(item.value), show_timeline=True)
        elif item.kind == "user":
            username = str(item.value)
            await self._open_profile_view(username)

    async def _submit_compose(self) -> None:
        username = self._posting_username()
        board = self._selected_compose_board()
        message = self.query_one("#compose-message", TextArea).text.strip()
        if not username or not message:
            self._set_status("Username and message are required.")
            return
        previous_board = self.current_board
        result = self.backend.post(username, board, message)

        # Handle image attachment
        image_input = self.query_one("#compose-image", Input)
        image_path = image_input.value.strip()
        if image_path:
            try:
                from pathlib import Path as _Path
                resolved = _Path(image_path).expanduser().resolve()
                fresh_posts = self.backend.read_posts(result.board)
                if fresh_posts:
                    new_post_id = fresh_posts[-1].id
                    self.backend.store_attachment(new_post_id, str(resolved))
            except (FileNotFoundError, ValueError, OSError) as e:
                self._set_status(f"Image error: {e}")
        image_input.value = ""

        if result.created_board:
            self._set_status(f"Created board {result.created_board}. Posted.")
        else:
            self._set_status("Posted.")
        self.current_board = result.board
        self.draft_board_name = ""
        self._users_dirty = True

        inserted_locally = False
        if (
            not result.created_board
            and self.section == "timeline"
            and result.board == previous_board
        ):
            latest_post = self._latest_board_post(result.board)
            if latest_post is not None:
                self._timeline_total_posts += 1
                await self._insert_post_into_timeline(latest_post)
                self._timeline_dirty = False
                inserted_locally = True

        if result.created_board:
            self._boards_dirty = True
        if not inserted_locally:
            self._timeline_dirty = True
            if result.created_board:
                await self._refresh_board_list()
            await self._show_section("timeline")
        self._clear_compose_message()
        self._reset_new_board_input()

    async def _submit_search(self) -> None:
        keyword = self.query_one("#search-input", Input).value.strip()
        if not keyword:
            self._set_status("Search keyword is required.")
            return
        self.search_selected_post = None
        self._set_search_detail_actions_visible(False)
        await self._refresh_search_results(keyword)

    async def _load_profile_view(self, username: str) -> None:
        """Populate profile view with user data and posts."""
        profile = self.backend.get_profile(username)
        if profile is None:
            return
        joined = _format_timestamp(profile.joined_at)
        self.query_one("#profile-header", Static).update(
            f"@{_safe_markup(profile.username)}  ·  Joined {joined}  ·  {profile.post_count} posts"
        )
        self.query_one("#profile-bio-label", Static).update("Bio:")
        self.query_one("#profile-bio", Input).value = profile.bio
        posts_list = self.query_one("#profile-posts", ListView)
        await posts_list.clear()
        user_posts = self._read_user_posts_window(username, self.PROFILE_POST_LIMIT)
        if profile.post_count > len(user_posts):
            self.query_one("#profile-header", Static).update(
                f"@{_safe_markup(profile.username)}  ·  Joined {joined}  ·  {profile.post_count} posts (showing latest {len(user_posts)})"
            )
        new_items: list[ListItem] = []
        for idx, post in enumerate(user_posts):
            lines = format_post_summary(post, include_board=True)
            row_class = "even-row" if idx % 2 == 0 else "odd-row"
            new_items.append(ListItem(Static(lines), classes=row_class))
        await posts_list.mount_all(new_items)

    async def _submit_profile_load(self) -> None:
        user_input = self.query_one("#profile-search", Input)
        pin_input = self.query_one("#profile-pin", Input)
        username = user_input.value.strip()
        pin = pin_input.value.strip()
        user_input.remove_class("input-error")
        pin_input.remove_class("input-error")
        if not username:
            user_input.add_class("input-error")
            self._set_status("Username is required.")
            return
        auth_state = self.backend.get_user_auth_state(username)
        if auth_state == "setup_required":
            self.query_one("#profile-header", Static).update(
                f"@{_safe_markup(username)} needs a PIN. Enter one and press Create."
            )
            self._set_status("PIN setup required.")
            return
        if not pin:
            if not username:
                user_input.add_class("input-error")
            if not pin:
                pin_input.add_class("input-error")
            self._set_status("Username and pin are required.")
            return
        if not self.backend.capabilities.supports_profiles:
            self.query_one("#profile-header", Static).update(
                "Profiles require the SQLite backend."
            )
            self._set_status("Profile unavailable.")
            return
        if not self.backend.verify_user(username, pin):
            self.query_one("#profile-header", Static).update(
                "Invalid username or pin."
            )
            self._set_status("Login failed.")
            return
        self.logged_in_user = username
        self._set_profile_mode("own")
        await self._load_profile_view(username)
        self._sync_compose_username()
        self._set_status(f"Logged in as @{escape_display_text(username)}")

    async def _submit_profile_create(self) -> None:
        user_input = self.query_one("#profile-search", Input)
        pin_input = self.query_one("#profile-pin", Input)
        username = user_input.value.strip()
        pin = pin_input.value.strip()
        user_input.remove_class("input-error")
        pin_input.remove_class("input-error")
        if not username or not pin:
            if not username:
                user_input.add_class("input-error")
            if not pin:
                pin_input.add_class("input-error")
            self._set_status("Username and pin are required.")
            return
        if not self.backend.capabilities.supports_profiles:
            self.query_one("#profile-header", Static).update(
                "Profiles require the SQLite backend."
            )
            self._set_status("Profile unavailable.")
            return
        auth_state = self.backend.get_user_auth_state(username)
        if auth_state == "setup_required":
            try:
                self.backend.set_initial_pin(username, pin)
            except ValueError as error:
                self.query_one("#profile-header", Static).update(str(error))
                self._set_status("PIN setup failed.")
                return
            self.logged_in_user = username
            self._set_profile_mode("own")
            await self._load_profile_view(username)
            self._sync_compose_username()
            self._set_status(f"PIN set for @{escape_display_text(username)}")
            return

        created = self.backend.create_user(username, pin)
        if not created:
            self.query_one("#profile-header", Static).update(
                f"Username '{_safe_markup(username)}' is already taken."
            )
            self._set_status("Username taken.")
            return
        self.logged_in_user = username
        self._set_profile_mode("own")
        await self._load_profile_view(username)
        self._sync_compose_username()
        self._set_status(f"Account created: @{escape_display_text(username)}")

    async def _submit_reply(self) -> None:
        if self.reply_target is None:
            self._set_status("No reply target selected.")
            return
        if not self.backend.capabilities.supports_threads:
            self._set_status("Replies require the SQLite backend.")
            return
        username = self._posting_username()
        message = self.query_one("#compose-message", TextArea).text.strip()
        if not username or not message:
            self._set_status("Username and message are required.")
            return
        self.backend.reply(username, self.reply_target.id, message)
        self._set_status("Reply posted.")
        self._clear_reply_target()
        self._clear_compose_message()
        self._mark_content_dirty(users=True)
        await self._refresh_board_list()
        await self._refresh_timeline()
        await self._set_timeline_focus()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Textual BBS viewer")
    parser.add_argument(
        "--backend",
        choices=("auto", "json", "sqlite"),
        default="auto",
        help="Select which storage backend to use",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = BbsTuiApp(backend_mode=args.backend)
    app.run()


if __name__ == "__main__":
    main()
