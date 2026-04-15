"""
Tests for BBS Part A (JSON) and Part B (SQLite).

Run with: uv run pytest
"""

import os
import re
import subprocess

import pytest


def run_command(args: list[str]) -> str:
    """Run a BBS command and return stdout."""
    result = subprocess.run(
        ["uv", "run", "python"] + args,
        capture_output=True,
        text=True
    )
    return result.stdout


# === Fixtures ===

@pytest.fixture
def clean_json():
    """Ensure bbs.json is removed before and after each test."""
    if os.path.exists("bbs.json"):
        os.remove("bbs.json")
    yield
    if os.path.exists("bbs.json"):
        os.remove("bbs.json")


@pytest.fixture
def clean_db():
    """Ensure bbs.db is removed before and after each test."""
    if os.path.exists("bbs.db"):
        os.remove("bbs.db")
    yield
    if os.path.exists("bbs.db"):
        os.remove("bbs.db")


@pytest.fixture
def seeded_json(clean_json):
    """Seed JSON with two posts for testing."""
    run_command(["bbs.py", "post", "alice", "Hello, is anyone out there?"])
    run_command(["bbs.py", "post", "bob", "Hey Alice! Welcome to the board."])
    yield


@pytest.fixture
def seeded_db(clean_db):
    """Seed database with two posts for testing."""
    run_command(["bbs_db.py", "post", "fwd_deployed", "Every student says they're going for gold."])
    run_command(["bbs_db.py", "post", "dean_of_stem", "And every student learns what scope creep means by Sunday night."])
    yield


# === Part A Tests (JSON) ===

class TestPartAPost:
    def test_prints_confirmation(self, clean_json):
        output = run_command(["bbs.py", "post", "alice", "Hello, is anyone out there?"])
        assert output.strip() == "Posted."

    def test_creates_json_file(self, clean_json):
        run_command(["bbs.py", "post", "alice", "Hello, is anyone out there?"])
        assert os.path.exists("bbs.json")


class TestPartARead:
    def test_output_format_matches_spec(self, seeded_json):
        """Output should be: [YYYY-MM-DD HH:MM] username: message"""
        output = run_command(["bbs.py", "read"])
        pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \w+: .+"
        assert re.search(pattern, output), f"Output format incorrect: {output}"

    def test_shows_all_posts(self, seeded_json):
        output = run_command(["bbs.py", "read"])
        assert "alice: Hello, is anyone out there?" in output
        assert "bob: Hey Alice! Welcome to the board." in output

    def test_posts_appear_in_chronological_order(self, seeded_json):
        output = run_command(["bbs.py", "read"])
        alice_pos = output.index("alice")
        bob_pos = output.index("bob")
        assert alice_pos < bob_pos, "Posts should appear in order they were created"

    def test_empty_database_shows_nothing(self, clean_json):
        output = run_command(["bbs.py", "read"])
        assert output.strip() == ""


class TestPartAUsers:
    def test_lists_all_users(self, seeded_json):
        output = run_command(["bbs.py", "users"])
        lines = output.strip().split("\n")
        assert "alice" in lines
        assert "bob" in lines

    def test_no_duplicate_users(self, clean_json):
        """Same user posting twice should appear once."""
        run_command(["bbs.py", "post", "alice", "First post"])
        run_command(["bbs.py", "post", "alice", "Second post"])
        output = run_command(["bbs.py", "users"])
        assert output.strip().count("alice") == 1


class TestPartASearch:
    def test_finds_matching_posts(self, seeded_json):
        output = run_command(["bbs.py", "search", "Hello"])
        assert "alice: Hello, is anyone out there?" in output

    def test_excludes_non_matching_posts(self, seeded_json):
        """Search for 'Hello' should not return bob's 'Hey' message."""
        # (The assignment example shows bob too, but "Hey" != "Hello" - nice try, Andy!)
        output = run_command(["bbs.py", "search", "Hello"])
        assert "bob" not in output

    def test_case_insensitive(self, seeded_json):
        output = run_command(["bbs.py", "search", "hello"])
        assert "alice" in output

    def test_no_results_returns_empty(self, seeded_json):
        output = run_command(["bbs.py", "search", "nonexistent"])
        assert output.strip() == ""


# === Part B Tests (SQLite) ===

class TestPartBPost:
    def test_prints_confirmation(self, clean_db):
        output = run_command(["bbs_db.py", "post", "fwd_deployed", "Every student says they're going for gold."])
        assert output.strip() == "Posted."

    def test_creates_database_file(self, clean_db):
        run_command(["bbs_db.py", "post", "fwd_deployed", "Every student says they're going for gold."])
        assert os.path.exists("bbs.db")


class TestPartBRead:
    def test_output_format_matches_spec(self, seeded_db):
        """Output should be: [YYYY-MM-DD HH:MM] username: message"""
        output = run_command(["bbs_db.py", "read"])
        pattern = r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] \w+: .+"
        assert re.search(pattern, output), f"Output format incorrect: {output}"

    def test_shows_all_posts(self, seeded_db):
        output = run_command(["bbs_db.py", "read"])
        assert "fwd_deployed: Every student says they're going for gold." in output
        assert "dean_of_stem: And every student learns what scope creep means by Sunday night." in output

    def test_posts_appear_in_chronological_order(self, seeded_db):
        output = run_command(["bbs_db.py", "read"])
        fwd_pos = output.index("fwd_deployed")
        dean_pos = output.index("dean_of_stem")
        assert fwd_pos < dean_pos, "Posts should appear in order they were created"


class TestPartBUsers:
    def test_lists_all_users(self, seeded_db):
        output = run_command(["bbs_db.py", "users"])
        lines = output.strip().split("\n")
        assert "fwd_deployed" in lines
        assert "dean_of_stem" in lines

    def test_users_listed_alphabetically(self, seeded_db):
        output = run_command(["bbs_db.py", "users"])
        lines = output.strip().split("\n")
        assert lines == sorted(lines), "Users should be in alphabetical order"

    def test_no_duplicate_users(self, clean_db):
        """Same user posting twice should appear once."""
        run_command(["bbs_db.py", "post", "fwd_deployed", "First post"])
        run_command(["bbs_db.py", "post", "fwd_deployed", "Second post"])
        output = run_command(["bbs_db.py", "users"])
        assert output.strip().count("fwd_deployed") == 1


class TestPartBSearch:
    def test_finds_matching_posts(self, seeded_db):
        output = run_command(["bbs_db.py", "search", "gold"])
        assert "fwd_deployed: Every student says they're going for gold." in output

    def test_excludes_non_matching_posts(self, seeded_db):
        output = run_command(["bbs_db.py", "search", "gold"])
        assert "dean_of_stem" not in output

    def test_no_results_returns_empty(self, seeded_db):
        output = run_command(["bbs_db.py", "search", "nonexistent"])
        assert output.strip() == ""


# === Part C Tests (Migration) ===

@pytest.fixture
def migration_setup(clean_json, clean_db):
    """Set up JSON with test data, ensure no database exists."""
    run_command(["bbs.py", "post", "fwd_deployed", "Every student says they're going for gold."])
    run_command(["bbs.py", "post", "dean_of_stem", "And every student learns what scope creep means by Sunday night."])
    run_command(["bbs.py", "post", "pierce", "Myles and I are going for gold together. Accountability buddy system."])
    run_command(["bbs.py", "post", "myles", "Pierce has mass texted me 47 times today."])
    run_command(["bbs.py", "post", "pierce", "48. Just sent another one."])
    run_command(["bbs.py", "post", "myles", "I'm turning off my phone."])
    yield


class TestMigration:
    def test_creates_database(self, migration_setup):
        """Migration should create bbs.db file."""
        run_command(["migrate.py"])
        assert os.path.exists("bbs.db")

    def test_creates_users_from_json(self, migration_setup):
        """Each unique username should become a row in users table."""
        run_command(["migrate.py"])
        output = run_command(["bbs_db.py", "users"])
        lines = output.strip().split("\n")
        assert "fwd_deployed" in lines
        assert "dean_of_stem" in lines
        assert "pierce" in lines
        assert "myles" in lines
        assert len(lines) == 4

    def test_handles_duplicate_usernames(self, migration_setup):
        """Users who post multiple times should only appear once in users table."""
        run_command(["migrate.py"])
        output = run_command(["bbs_db.py", "users"])
        # pierce and myles each post twice, but should only appear once
        assert output.count("pierce") == 1
        assert output.count("myles") == 1

    def test_creates_posts_from_json(self, migration_setup):
        """Each post should be migrated to the database."""
        run_command(["migrate.py"])
        output = run_command(["bbs_db.py", "read"])
        assert "Every student says they're going for gold." in output
        assert "And every student learns what scope creep means by Sunday night." in output
        assert "Accountability buddy system." in output
        assert "47 times today." in output
        assert "48. Just sent another one." in output
        assert "turning off my phone." in output

    def test_output_matches_after_migration(self, migration_setup):
        """bbs_db.py read should produce identical output to bbs.py read."""
        json_output = run_command(["bbs.py", "read"])
        run_command(["migrate.py"])
        db_output = run_command(["bbs_db.py", "read"])
        assert json_output == db_output

    def test_errors_if_db_exists(self, migration_setup):
        """Migration should fail if bbs.db already exists."""
        run_command(["migrate.py"])  # First migration succeeds
        result = subprocess.run(
            ["uv", "run", "python", "migrate.py"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        combined_output = result.stderr + result.stdout
        assert "bbs.db already exists" in combined_output
        assert "--force" in combined_output

    def test_force_flag_overwrites(self, migration_setup):
        """--force flag should allow overwriting existing database."""
        run_command(["migrate.py"])  # First migration
        result = subprocess.run(
            ["uv", "run", "python", "migrate.py", "--force"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Migrated" in result.stdout

    def test_empty_json_creates_empty_db(self, clean_json, clean_db):
        """Migration with no posts should create database with empty tables."""
        # Create empty bbs.json (no posts)
        with open("bbs.json", "w") as f:
            f.write("[]")
        run_command(["migrate.py"])
        assert os.path.exists("bbs.db")
        output = run_command(["bbs_db.py", "read"])
        assert output.strip() == ""

    def test_missing_json_errors(self, clean_db):
        """Migration should fail with clear message if bbs.json doesn't exist."""
        # Explicitly ensure bbs.json doesn't exist
        if os.path.exists("bbs.json"):
            os.remove("bbs.json")

        result = subprocess.run(
            ["uv", "run", "python", "migrate.py"],
            capture_output=True,
            text=True
        )
        assert result.returncode != 0
        combined_output = result.stderr + result.stdout
        assert "bbs.json not found" in combined_output
