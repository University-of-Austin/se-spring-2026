from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


def bbs_test_env(workdir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["BBS_DATA_DIR"] = str(workdir)
    return env


@contextmanager
def use_bbs_data_dir(workdir: Path):
    with mock.patch.dict(os.environ, {"BBS_DATA_DIR": str(workdir)}, clear=False):
        yield
