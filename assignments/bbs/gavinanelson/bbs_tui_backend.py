from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app_paths import get_db_path, get_json_path
from rich.markup import escape as escape_markup

from bbs_db_format import escape_display_text

_SQLITE_STORE: dict[str, object] | None = None


@dataclass(frozen=True)
class PostRecord:
    id: int
    username: str
    message: str
    timestamp: str
    board: str = "general"
    parent_post_id: int | None = None
    board_seq: int = 0
    has_attachment: bool = False


@dataclass(frozen=True)
class ProfileRecord:
    username: str
    joined_at: str
    bio: str
    post_count: int


@dataclass(frozen=True)
class PostActionResult:
    board: str
    created_board: str | None = None


@dataclass(frozen=True)
class BoardInfo:
    slug: str
    name: str
    post_count: int
    created_at: str
    created_by: str


@dataclass(frozen=True)
class BackendCapabilities:
    supports_boards: bool
    supports_threads: bool
    supports_profiles: bool


class BbsBackend(Protocol):
    kind: str
    label: str
    capabilities: BackendCapabilities

    def list_boards(self) -> list[str]:
        ...

    def list_users(self) -> list[str]:
        ...

    def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
        ...

    def search_posts(self, keyword: str) -> list[PostRecord]:
        ...

    def search_users(self, keyword: str) -> list[str]:
        ...

    def post(self, username: str, board: str, message: str) -> PostActionResult:
        ...

    def reply(self, username: str, parent_post_id: int, message: str) -> None:
        ...

    def get_profile(self, username: str) -> ProfileRecord | None:
        ...

    def set_bio(self, username: str, bio: str) -> None:
        ...

    def get_board_info(self, board: str) -> BoardInfo | None:
        ...

    def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
        ...

    def create_user(self, username: str, pin: str) -> bool:
        ...

    def verify_user(self, username: str, pin: str) -> bool:
        ...

    def get_user_auth_state(self, username: str) -> str:
        ...

    def set_initial_pin(self, username: str, pin: str) -> None:
        ...


def _normalize_board_name(board_name: str) -> str:
    slug = "-".join(board_name.strip().lower().split())
    return slug or "general"


def _format_timestamp(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp)
    return dt.strftime("%b %-d · %-I:%M %p")


def _safe_rich(value: object) -> str:
    return escape_markup(escape_display_text(value))


def _safe_rich_message(value: object) -> str:
    escaped = escape_markup(str(value))
    safe: list[str] = []
    for character in escaped:
        if character == "\n":
            safe.append("\n")
        elif character == "\r":
            safe.append(r"\r")
        elif character == "\t":
            safe.append(r"\t")
        elif ord(character) < 32 or ord(character) == 127:
            safe.append(f"\\x{ord(character):02x}")
        else:
            safe.append(character)
    return "".join(safe)


def _row_mapping(row: object) -> dict[str, object]:
    mapping = getattr(row, "_mapping", row)
    return dict(mapping)


def _post_record(mapping: dict[str, object], *, default_board: str = "general", default_seq: int = 0) -> PostRecord:
    return PostRecord(
        id=int(mapping["id"]),
        username=str(mapping["username"]),
        message=str(mapping["message"]),
        timestamp=str(mapping["timestamp"]),
        board=str(mapping.get("board_slug", default_board)),
        parent_post_id=None if mapping.get("parent_post_id") is None else int(mapping["parent_post_id"]),
        board_seq=int(mapping.get("board_seq", default_seq)),
        has_attachment=bool(mapping.get("has_attachment", False)),
    )


def _profile_record(mapping: dict[str, object]) -> ProfileRecord:
    return ProfileRecord(
        username=str(mapping["username"]),
        joined_at=str(mapping["joined_at"]),
        bio=str(mapping["bio"]),
        post_count=int(mapping["post_count"]),
    )


def _board_info(mapping: dict[str, object]) -> BoardInfo:
    return BoardInfo(
        slug=str(mapping["slug"]),
        name=str(mapping["name"]),
        post_count=int(mapping["post_count"]),
        created_at=str(mapping["created_at"]),
        created_by=str(mapping["created_by"]),
    )


class JsonBackend:
    kind = "json"
    label = "JSON"
    capabilities = BackendCapabilities(
        supports_boards=False,
        supports_threads=False,
        supports_profiles=False,
    )

    def _load_posts(self) -> list[dict[str, str]]:
        from bbs import load_posts

        return load_posts()

    def _save_posts(self, posts: list[dict[str, str]]) -> None:
        from bbs import save_posts

        save_posts(posts)

    def list_boards(self) -> list[str]:
        return ["general"]

    def list_users(self) -> list[str]:
        seen: set[str] = set()
        users: list[str] = []
        for post in self._load_posts():
            username = post["username"]
            if username in seen:
                continue
            seen.add(username)
            users.append(username)
        return users

    def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
        if _normalize_board_name(board) != "general":
            return []

        posts = self._load_posts()
        start_index = 1
        if limit is not None and limit < len(posts):
            start_index = len(posts) - limit + 1
            posts = posts[-limit:]

        return [
            _post_record(
                {"id": index, **post},
                default_board="general",
                default_seq=index,
            )
            for index, post in enumerate(posts, start=start_index)
        ]

    def search_posts(self, keyword: str) -> list[PostRecord]:
        needle = keyword.casefold()
        return [
            _post_record({"id": index, **post}, default_board="general")
            for index, post in enumerate(self._load_posts(), start=1)
            if needle in post["message"].casefold()
        ]

    def search_users(self, keyword: str) -> list[str]:
        needle = keyword.casefold()
        return [username for username in self.list_users() if needle in username.casefold()]

    def post(self, username: str, board: str, message: str) -> PostActionResult:
        posts = self._load_posts()
        posts.append(
            {
                "username": username,
                "message": message,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._save_posts(posts)
        return PostActionResult(board="general")

    def reply(self, username: str, parent_post_id: int, message: str) -> None:
        raise NotImplementedError("Replies require the SQLite backend.")

    def get_profile(self, username: str) -> ProfileRecord | None:
        return None

    def set_bio(self, username: str, bio: str) -> None:
        raise NotImplementedError("Profiles require the SQLite backend.")

    def get_board_info(self, board: str) -> BoardInfo | None:
        if _normalize_board_name(board) != "general":
            return None
        posts = self._load_posts()
        if not posts:
            return _board_info(
                {
                    "slug": "general",
                    "name": "general",
                    "post_count": 0,
                    "created_at": "",
                    "created_by": "",
                }
            )
        return _board_info(
            {
                "slug": "general",
                "name": "general",
                "post_count": len(posts),
                "created_at": posts[0]["timestamp"],
                "created_by": posts[0]["username"],
            }
        )

    def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
        posts = [
            post
            for post in self._load_posts()
            if post["username"] == username
        ]
        start_index = 1
        if limit is not None and limit < len(posts):
            start_index = len(posts) - limit + 1
            posts = posts[-limit:]
        return [
            _post_record({"id": index, **post}, default_board="general")
            for index, post in enumerate(posts, start=start_index)
        ]

    def create_user(self, username: str, pin: str) -> bool:
        raise NotImplementedError("User accounts require the SQLite backend.")

    def verify_user(self, username: str, pin: str) -> bool:
        raise NotImplementedError("User accounts require the SQLite backend.")

    def get_user_auth_state(self, username: str) -> str:
        return "missing"

    def set_initial_pin(self, username: str, pin: str) -> None:
        raise NotImplementedError("User accounts require the SQLite backend.")


class SqliteBackend:
    kind = "sqlite"
    label = "SQLite"
    capabilities = BackendCapabilities(
        supports_boards=True,
        supports_threads=True,
        supports_profiles=True,
    )

    @staticmethod
    def _store():
        global _SQLITE_STORE
        if _SQLITE_STORE is not None:
            return _SQLITE_STORE

        from bbs_db_store import (
            create_post,
            create_reply,
            create_user,
            get_attachment,
            get_board_info,
            get_profile,
            get_user_auth_state,
            get_user_posts,
            list_boards,
            list_users,
            read_posts,
            search_posts,
            set_initial_pin,
            search_users,
            set_bio,
            store_attachment,
            verify_user,
        )

        _SQLITE_STORE = {
            "create_post": create_post,
            "create_reply": create_reply,
            "create_user": create_user,
            "get_attachment": get_attachment,
            "get_board_info": get_board_info,
            "get_profile": get_profile,
            "get_user_auth_state": get_user_auth_state,
            "get_user_posts": get_user_posts,
            "list_boards": list_boards,
            "list_users": list_users,
            "read_posts": read_posts,
            "search_posts": search_posts,
            "set_initial_pin": set_initial_pin,
            "search_users": search_users,
            "set_bio": set_bio,
            "store_attachment": store_attachment,
            "verify_user": verify_user,
        }
        return _SQLITE_STORE

    def list_boards(self) -> list[str]:
        return self._store()["list_boards"]()

    def list_users(self) -> list[str]:
        return self._store()["list_users"]()

    def read_posts(self, board: str = "general", limit: int | None = None) -> list[PostRecord]:
        rows = self._store()["read_posts"](board, limit=limit)
        return [_post_record(row, default_seq=int(row["board_seq"])) for row in rows]

    def search_posts(self, keyword: str) -> list[PostRecord]:
        rows = self._store()["search_posts"](keyword)
        return [_post_record(row) for row in rows]

    def search_users(self, keyword: str) -> list[str]:
        return self._store()["search_users"](keyword)

    def post(self, username: str, board: str, message: str) -> PostActionResult:
        created_board, board_slug = self._store()["create_post"](username, message, board)
        return PostActionResult(
            board=board_slug,
            created_board=board_slug if created_board else None,
        )

    def reply(self, username: str, parent_post_id: int, message: str) -> None:
        self._store()["create_reply"](username, parent_post_id, message)

    def get_profile(self, username: str) -> ProfileRecord | None:
        profile = self._store()["get_profile"](username)
        if profile is None:
            return None
        return _profile_record(profile)

    def set_bio(self, username: str, bio: str) -> None:
        self._store()["set_bio"](username, bio)

    def get_board_info(self, board: str) -> BoardInfo | None:
        row = self._store()["get_board_info"](board)
        if row is None:
            return None
        return _board_info(row)

    def get_user_posts(self, username: str, limit: int | None = None) -> list[PostRecord]:
        rows = self._store()["get_user_posts"](username, limit=limit)
        return [_post_record(row) for row in rows]

    def create_user(self, username: str, pin: str) -> bool:
        return self._store()["create_user"](username, pin)

    def verify_user(self, username: str, pin: str) -> bool:
        return self._store()["verify_user"](username, pin)

    def get_user_auth_state(self, username: str) -> str:
        return self._store()["get_user_auth_state"](username)

    def set_initial_pin(self, username: str, pin: str) -> None:
        self._store()["set_initial_pin"](username, pin)

    def store_attachment(self, post_id: int, file_path: str) -> str:
        return self._store()["store_attachment"](post_id, file_path)

    def get_attachment_path(self, post_id: int) -> str | None:
        info = self._store()["get_attachment"](post_id)
        if info is None:
            return None
        return info["path"]

    def get_attachment_info(self, post_id: int) -> dict | None:
        return self._store()["get_attachment"](post_id)


def load_backend(mode: str) -> BbsBackend:
    normalized = mode.casefold()
    if normalized == "json":
        return JsonBackend()
    if normalized == "sqlite":
        return SqliteBackend()
    if normalized != "auto":
        raise ValueError(f"Unknown backend mode: {mode}")

    if get_db_path().exists():
        return SqliteBackend()
    if get_json_path().exists():
        return JsonBackend()
    return SqliteBackend()


def format_post_summary(post: PostRecord, include_board: bool = False) -> str:
    timestamp = _format_timestamp(post.timestamp)
    seq = post.board_seq if post.board_seq else post.id
    board_part = f"  [#666666]/{_safe_rich(post.board)}[/]" if include_board else ""
    img_part = "  [#666666]\\[img][/]" if post.has_attachment else ""
    return (
        f"[#888888]{_safe_rich(post.username)}[/] [#333333]\u00b7[/] [#666666]{timestamp}[/]  [#666666]#{seq}[/]{board_part}{img_part}\n"
        f"[#dddddd]{_safe_rich_message(post.message)}[/]"
    )


def format_post_detail(post: PostRecord) -> str:
    seq = post.board_seq if post.board_seq else post.id
    lines = [
        f"[#555555]#{seq}[/]  [bold #dddddd]{_safe_rich(post.username)}[/]",
        f"[#555555]{_format_timestamp(post.timestamp)}[/]  [#666666]/{_safe_rich(post.board)}[/]",
        "",
        f"[#bbbbbb]{_safe_rich_message(post.message)}[/]",
    ]
    if post.parent_post_id is not None:
        lines.insert(0, f"[#555555]\u21a9 Reply to #{post.parent_post_id}[/]")
    return "\n".join(lines)


def format_reply_quote(parent: PostRecord) -> str:
    flattened = parent.message.replace("\r", " ").replace("\n", " ")
    truncated = flattened[:60] + ("..." if len(flattened) > 60 else "")
    return f"[#555555]↩ @{_safe_rich(parent.username)}: {_safe_rich(truncated)}[/]"
