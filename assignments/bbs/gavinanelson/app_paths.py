from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


APP_NAME = "bbs"


def get_data_dir() -> Path:
    override = os.getenv("BBS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return (Path(xdg_data_home).expanduser() / APP_NAME).resolve()

    return (Path.home() / ".local" / "share" / APP_NAME).resolve()


def ensure_data_dir() -> Path:
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_json_path() -> Path:
    return get_data_dir() / "bbs.json"


def get_db_path() -> Path:
    return get_data_dir() / "bbs.db"


def get_backups_dir() -> Path:
    backups_dir = ensure_data_dir() / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    return backups_dir


def get_exports_dir() -> Path:
    exports_dir = ensure_data_dir() / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def get_uploads_dir() -> Path:
    uploads_dir = ensure_data_dir() / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def default_backup_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_backups_dir() / f"bbs-backup-{timestamp}.db"


def default_export_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return get_exports_dir() / f"bbs-export-{timestamp}.json"
