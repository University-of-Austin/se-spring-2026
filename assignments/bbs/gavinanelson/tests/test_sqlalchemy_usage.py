import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_FILES = [
    REPO_ROOT / "tests" / "test_bbs_db.py",
    REPO_ROOT / "tests" / "test_migrate.py",
    REPO_ROOT / "tests" / "test_seed_fake_data.py",
]


class SqlalchemyUsageTests(unittest.TestCase):
    def test_sqlite_inspection_tests_do_not_import_sqlite3(self) -> None:
        for path in TEST_FILES:
            text = path.read_text()
            self.assertNotIn("import sqlite3", text, msg=f"{path.name} still imports sqlite3")
            self.assertNotIn("sqlite3.connect", text, msg=f"{path.name} still uses sqlite3.connect")


if __name__ == "__main__":
    unittest.main()
