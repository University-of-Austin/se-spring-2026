from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from app_paths import ensure_data_dir, get_db_path
from sqlalchemy import text

from db import engine, init_db


def _rows_to_dicts(rows) -> list[dict[str, object]]:
    return [dict(row._mapping) for row in rows]


def _bounded_limit(limit: int | None) -> int | None:
    if limit is None:
        return None
    return max(1, int(limit))


def _validate_pin(pin: str) -> str:
    normalized = pin.strip()
    if len(normalized) != 4 or not normalized.isdigit():
        raise ValueError("pin must be exactly 4 digits")
    return normalized


def _hash_pin(pin: str) -> str:
    iterations = 200_000
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_pin_hash(pin: str, pin_hash: str) -> bool:
    try:
        algorithm, iteration_text, salt_hex, digest_hex = pin_hash.split("$", maxsplit=3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iteration_text),
    ).hex()
    return hmac.compare_digest(computed, digest_hex)


def normalize_board_name(board_name: str) -> str:
    slug = "-".join(board_name.strip().lower().split())
    if not slug:
        raise ValueError("board name cannot be blank")
    return slug


def _ensure_board(connection, board_name: str) -> tuple[int, bool, str]:
    slug = normalize_board_name(board_name)
    display_name = board_name.strip()
    insert_result = connection.execute(
        text(
            "INSERT OR IGNORE INTO boards (slug, name, created_at) VALUES (:slug, :name, :created_at)"
        ),
        {
            "slug": slug,
            "name": display_name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    created = connection.execute(
        text("SELECT id, slug FROM boards WHERE slug = :slug"),
        {"slug": slug},
    ).fetchone()
    return int(created.id), insert_result.rowcount > 0, str(created.slug)


def ensure_board(board_name: str) -> tuple[int, bool, str]:
    init_db()
    with engine.begin() as connection:
        return _ensure_board(connection, board_name)


def ensure_general_board() -> tuple[int, bool, str]:
    return ensure_board("general")


def _ensure_user(connection, username: str) -> int:
    connection.execute(
        text(
            """
            INSERT OR IGNORE INTO users (username, joined_at, bio, pin, pin_hash, pin_needs_reset)
            VALUES (:username, :joined_at, :bio, :pin, :pin_hash, :pin_needs_reset)
            """
        ),
        {
            "username": username,
            "joined_at": datetime.now().isoformat(timespec="seconds"),
            "bio": "",
            "pin": "",
            "pin_hash": "",
            "pin_needs_reset": 1,
        },
    )
    created = connection.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).fetchone()
    return int(created.id)


def ensure_user(username: str) -> int:
    init_db()
    with engine.begin() as connection:
        return _ensure_user(connection, username)


def create_user(username: str, pin: str) -> bool:
    """Create a new user with a 4-digit pin. Returns True if created, False if name taken."""
    init_db()
    normalized_pin = _validate_pin(pin)
    with engine.begin() as connection:
        insert_result = connection.execute(
            text(
                """
                INSERT OR IGNORE INTO users (username, joined_at, bio, pin, pin_hash, pin_needs_reset)
                VALUES (:username, :joined_at, :bio, :pin, :pin_hash, :pin_needs_reset)
                """
            ),
            {
                "username": username,
                "joined_at": datetime.now().isoformat(timespec="seconds"),
                "bio": "",
                "pin": "",
                "pin_hash": _hash_pin(normalized_pin),
                "pin_needs_reset": 0,
            },
        )
        return insert_result.rowcount > 0


def get_user_auth_state(username: str) -> str:
    init_db()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pin, pin_hash, pin_needs_reset FROM users WHERE username = :username"
            ),
            {"username": username},
        ).fetchone()
        if row is None:
            return "missing"
        if bool(row.pin_needs_reset):
            return "setup_required"
        return "ready"


def set_initial_pin(username: str, pin: str) -> None:
    init_db()
    normalized_pin = _validate_pin(pin)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "SELECT pin_needs_reset FROM users WHERE username = :username"
            ),
            {"username": username},
        ).fetchone()
        if row is None:
            raise ValueError(f"User {username} does not exist.")
        if not bool(row.pin_needs_reset):
            raise ValueError(f"User {username} already has a pin.")
        connection.execute(
            text(
                """
                UPDATE users
                SET pin = :legacy_pin, pin_hash = :pin_hash, pin_needs_reset = 0
                WHERE username = :username
                """
            ),
            {
                "legacy_pin": "",
                "pin_hash": _hash_pin(normalized_pin),
                "username": username,
            },
        )


def update_user_pin(username: str, current_pin: str, new_pin: str) -> None:
    init_db()
    normalized_new_pin = _validate_pin(new_pin)
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT pin, pin_hash, pin_needs_reset
                FROM users
                WHERE username = :username
                """
            ),
            {"username": username},
        ).fetchone()
        if row is None:
            raise ValueError(f"User {username} does not exist.")
        if bool(row.pin_needs_reset):
            raise ValueError(f"User {username} must set an initial pin first.")
        pin_hash = str(row.pin_hash or "")
        legacy_pin = str(row.pin or "")
        if pin_hash:
            valid_current_pin = _verify_pin_hash(current_pin, pin_hash)
        else:
            valid_current_pin = bool(legacy_pin) and hmac.compare_digest(legacy_pin, current_pin)
        if not valid_current_pin:
            raise ValueError("current pin is invalid")
        connection.execute(
            text(
                """
                UPDATE users
                SET pin = :legacy_pin, pin_hash = :pin_hash, pin_needs_reset = 0
                WHERE username = :username
                """
            ),
            {
                "legacy_pin": "",
                "pin_hash": _hash_pin(normalized_new_pin),
                "username": username,
            },
        )


def verify_user(username: str, pin: str) -> bool:
    """Verify a user's pin. Returns True if username exists and pin matches."""
    init_db()
    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT pin, pin_hash, pin_needs_reset
                FROM users
                WHERE username = :username
                """
            ),
            {"username": username},
        ).fetchone()
        if row is None:
            return False
        if bool(row.pin_needs_reset):
            return False

        pin_hash = str(row.pin_hash or "")
        if pin_hash:
            return _verify_pin_hash(pin, pin_hash)

        legacy_pin = str(row.pin or "")
        if not legacy_pin or not hmac.compare_digest(legacy_pin, pin):
            return False

        connection.execute(
            text(
                """
                UPDATE users
                SET pin = :legacy_pin, pin_hash = :pin_hash, pin_needs_reset = 0
                WHERE username = :username
                """
            ),
            {
                "legacy_pin": "",
                "pin_hash": _hash_pin(pin),
                "username": username,
            },
        )
        return True


def export_posts_to_json(destination: Path) -> Path:
    init_db()
    destination_path = destination.expanduser().resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    payload = read_all_posts()
    destination_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination_path


def backup_database(destination: Path) -> Path:
    init_db()
    ensure_data_dir()
    source_path = get_db_path()
    destination_path = destination.expanduser().resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    return destination_path


def create_board(board_name: str) -> tuple[bool, str]:
    init_db()
    slug = normalize_board_name(board_name)
    with engine.begin() as connection:
        if slug != "general":
            _ensure_board(connection, "general")
        _, created, created_slug = _ensure_board(connection, board_name)
        return created, created_slug


def create_post(username: str, message: str, board_name: str = "general") -> tuple[bool, str]:
    init_db()
    with engine.begin() as connection:
        if normalize_board_name(board_name) != "general":
            _ensure_board(connection, "general")
        board_id, created_board, board_slug = _ensure_board(connection, board_name)
        user_id = _ensure_user(connection, username)
        connection.execute(
            text(
                """
                INSERT INTO posts (user_id, board_id, parent_post_id, message, timestamp)
                VALUES (:user_id, :board_id, :parent_post_id, :message, :timestamp)
                """
            ),
            {
                "user_id": user_id,
                "board_id": board_id,
                "parent_post_id": None,
                "message": message,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            },
        )
    return created_board, board_slug


def _get_post(connection, post_id: int):
    return connection.execute(
        text(
            """
            SELECT p.id, p.board_id, p.parent_post_id
            FROM posts p
            WHERE p.id = :post_id
            """
        ),
        {"post_id": post_id},
    ).fetchone()


def get_post(post_id: int):
    init_db()
    with engine.connect() as connection:
        return _get_post(connection, post_id)


def create_reply(username: str, parent_post_id: int, message: str) -> None:
    init_db()
    with engine.begin() as connection:
        parent = _get_post(connection, parent_post_id)
        if parent is None:
            raise ValueError(f"Post {parent_post_id} does not exist.")
        user_id = _ensure_user(connection, username)
        connection.execute(
            text(
                """
                INSERT INTO posts (user_id, board_id, parent_post_id, message, timestamp)
                VALUES (:user_id, :board_id, :parent_post_id, :message, :timestamp)
                """
            ),
            {
                "user_id": user_id,
                "board_id": int(parent.board_id),
                "parent_post_id": parent_post_id,
                "message": message,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            },
        )


def list_boards() -> list[str]:
    init_db()
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        rows = connection.execute(
            text("SELECT slug FROM boards ORDER BY slug ASC")
        )
        return [str(row.slug) for row in rows]


def read_posts(board_name: str = "general", limit: int | None = None) -> list[dict[str, object]]:
    init_db()
    slug = normalize_board_name(board_name)
    bounded_limit = _bounded_limit(limit)
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        board = connection.execute(
            text("SELECT id FROM boards WHERE slug = :slug"),
            {"slug": slug},
        ).fetchone()
        if board is None:
            return []

        if bounded_limit is None:
            rows = connection.execute(
                text(
                    """
                    SELECT
                        p.id,
                        u.username,
                        b.slug AS board_slug,
                        p.message,
                        p.timestamp,
                        p.parent_post_id,
                        ROW_NUMBER() OVER (ORDER BY p.id ASC) AS board_seq,
                        CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_attachment
                    FROM posts p
                    JOIN users u ON u.id = p.user_id
                    JOIN boards b ON b.id = p.board_id
                    LEFT JOIN attachments a ON a.post_id = p.id
                    WHERE p.board_id = :board_id
                    ORDER BY p.id ASC
                    """
                ),
                {"board_id": int(board.id)},
            )
        else:
            rows = connection.execute(
                text(
                    """
                    WITH ranked_posts AS (
                        SELECT
                            p.id,
                            u.username,
                            b.slug AS board_slug,
                            p.message,
                            p.timestamp,
                            p.parent_post_id,
                            ROW_NUMBER() OVER (ORDER BY p.id ASC) AS board_seq,
                            CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_attachment
                        FROM posts p
                        JOIN users u ON u.id = p.user_id
                        JOIN boards b ON b.id = p.board_id
                        LEFT JOIN attachments a ON a.post_id = p.id
                        WHERE p.board_id = :board_id
                    ),
                    windowed_posts AS (
                        SELECT *
                        FROM ranked_posts
                        ORDER BY board_seq DESC
                        LIMIT :limit
                    )
                    SELECT
                        id,
                        username,
                        board_slug,
                        message,
                        timestamp,
                        parent_post_id,
                        board_seq,
                        has_attachment
                    FROM windowed_posts
                    ORDER BY board_seq ASC
                    """
                ),
                {"board_id": int(board.id), "limit": bounded_limit},
            )
        return _rows_to_dicts(rows)


def read_all_posts() -> list[dict[str, str]]:
    init_db()
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        rows = connection.execute(
            text(
                """
                SELECT u.username, p.message, p.timestamp
                FROM posts p
                JOIN users u ON u.id = p.user_id
                ORDER BY p.timestamp ASC, p.id ASC
                """
            )
        )
        return _rows_to_dicts(rows)


def list_users() -> list[str]:
    init_db()
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        rows = connection.execute(
            text(
                """
                SELECT u.username
                FROM users u
                ORDER BY u.joined_at ASC, u.id ASC
                """
            )
        )
        return [str(row.username) for row in rows]


def search_posts(keyword: str) -> list[dict[str, str]]:
    init_db()
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        rows = connection.execute(
            text(
                """
                SELECT
                    p.id,
                    u.username,
                    b.slug AS board_slug,
                    p.message,
                    p.timestamp,
                    p.parent_post_id,
                    CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_attachment
                FROM posts p
                JOIN users u ON u.id = p.user_id
                JOIN boards b ON b.id = p.board_id
                LEFT JOIN attachments a ON a.post_id = p.id
                WHERE LOWER(p.message) LIKE :keyword
                ORDER BY p.timestamp ASC, p.id ASC
                """
            ),
            {"keyword": f"%{keyword.lower()}%"},
        )
        return _rows_to_dicts(rows)


def search_users(keyword: str) -> list[str]:
    init_db()
    with engine.begin() as connection:
        _ensure_board(connection, "general")
        rows = connection.execute(
            text(
                """
                SELECT u.username
                FROM users u
                WHERE LOWER(u.username) LIKE :keyword
                ORDER BY u.joined_at ASC, u.id ASC
                """
            ),
            {"keyword": f"%{keyword.lower()}%"},
        )
        return [str(row.username) for row in rows]


def get_profile(username: str) -> dict[str, object] | None:
    init_db()
    with engine.connect() as connection:
        profile = connection.execute(
            text(
                """
                SELECT u.username, u.joined_at, u.bio, COUNT(p.id) AS post_count
                FROM users u
                LEFT JOIN posts p ON p.user_id = u.id
                WHERE u.username = :username
                GROUP BY u.id, u.username, u.joined_at, u.bio
                """
            ),
            {"username": username},
        ).fetchone()
        return dict(profile._mapping) if profile is not None else None


def set_bio(username: str, bio: str) -> None:
    init_db()
    with engine.begin() as connection:
        result = connection.execute(
            text("UPDATE users SET bio = :bio WHERE username = :username"),
            {"bio": bio, "username": username},
        )
        if result.rowcount == 0:
            raise ValueError(f"User {username} does not exist.")


def get_user_posts(username: str, limit: int | None = None) -> list[dict[str, object]]:
    init_db()
    bounded_limit = _bounded_limit(limit)
    with engine.connect() as connection:
        if bounded_limit is None:
            rows = connection.execute(
                text(
                    """
                    SELECT
                        p.id,
                        u.username,
                    b.slug AS board_slug,
                    p.message,
                    p.timestamp,
                    p.parent_post_id,
                    CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_attachment
                FROM posts p
                JOIN users u ON u.id = p.user_id
                JOIN boards b ON b.id = p.board_id
                LEFT JOIN attachments a ON a.post_id = p.id
                WHERE u.username = :username
                ORDER BY p.id ASC
                """
            ),
            {"username": username},
        )
        else:
            rows = connection.execute(
                text(
                    """
                    WITH ranked_posts AS (
                        SELECT
                            p.id,
                            u.username,
                            b.slug AS board_slug,
                            p.message,
                            p.timestamp,
                            p.parent_post_id,
                            ROW_NUMBER() OVER (ORDER BY p.id ASC) AS user_seq,
                            CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_attachment
                        FROM posts p
                        JOIN users u ON u.id = p.user_id
                        JOIN boards b ON b.id = p.board_id
                        LEFT JOIN attachments a ON a.post_id = p.id
                        WHERE u.username = :username
                    ),
                    windowed_posts AS (
                        SELECT *
                        FROM ranked_posts
                        ORDER BY user_seq DESC
                        LIMIT :limit
                    )
                    SELECT
                        id,
                        username,
                        board_slug,
                        message,
                        timestamp,
                        parent_post_id,
                        has_attachment
                    FROM windowed_posts
                    ORDER BY user_seq ASC
                    """
                ),
                {"username": username, "limit": bounded_limit},
            )
        return _rows_to_dicts(rows)


def get_board_info(board_slug: str) -> dict[str, object] | None:
    init_db()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    b.slug,
                    b.name,
                    b.created_at,
                    COUNT(p.id) AS post_count,
                    COALESCE(
                        (SELECT u2.username
                         FROM posts p2
                         JOIN users u2 ON u2.id = p2.user_id
                         WHERE p2.board_id = b.id
                         ORDER BY p2.timestamp ASC, p2.id ASC
                         LIMIT 1),
                        ''
                    ) AS created_by
                FROM boards b
                LEFT JOIN posts p ON p.board_id = b.id
                WHERE b.slug = :slug
                GROUP BY b.id, b.slug, b.name, b.created_at
                """
            ),
            {"slug": board_slug},
        ).fetchone()
        return dict(row._mapping) if row is not None else None


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


def store_attachment(post_id: int, file_path: str) -> str:
    """Hash file, copy to uploads/, insert attachment row. Returns 16-char hex hash."""
    from app_paths import get_uploads_dir

    init_db()
    source = Path(file_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"File not found: {source}")

    ext = source.suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image format: {ext}")

    size = source.stat().st_size
    if size > MAX_ATTACHMENT_SIZE:
        raise ValueError(f"File too large: {size} bytes (max {MAX_ATTACHMENT_SIZE})")

    file_bytes = source.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]

    uploads_dir = get_uploads_dir()
    dest = uploads_dir / f"{file_hash}{ext}"
    if not dest.exists():
        shutil.copy2(str(source), str(dest))

    mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR REPLACE INTO attachments (post_id, hash, original_name, mime_type, size_bytes, created_at)
                VALUES (:post_id, :hash, :original_name, :mime_type, :size_bytes, :created_at)
                """
            ),
            {
                "post_id": post_id,
                "hash": file_hash,
                "original_name": source.name,
                "mime_type": mime_type,
                "size_bytes": size,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )
    return file_hash


def get_attachment(post_id: int) -> dict | None:
    """Return attachment info dict or None."""
    from app_paths import get_uploads_dir

    init_db()
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT hash, original_name, mime_type, size_bytes FROM attachments WHERE post_id = :pid"),
            {"pid": post_id},
        ).fetchone()
        if row is None:
            return None
        ext = Path(row.original_name).suffix.lower()
        return {
            "hash": str(row.hash),
            "original_name": str(row.original_name),
            "mime_type": str(row.mime_type),
            "size_bytes": int(row.size_bytes),
            "path": str(get_uploads_dir() / f"{row.hash}{ext}"),
        }
