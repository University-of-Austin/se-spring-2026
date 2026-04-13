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
