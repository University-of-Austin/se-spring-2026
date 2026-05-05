from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app_paths import get_db_path
from sqlalchemy import text

from db import engine, init_db


FIRST_NAMES = [
    "alice", "bob", "clara", "dante", "ella", "felix", "grace", "henry", "ivy", "jules",
    "kara", "leo", "mira", "niko", "olive", "piper", "quinn", "rosa", "sasha", "toby",
    "uma", "violet", "wren", "xena", "yara", "zane", "amber", "bram", "celia", "dev",
    "ezra", "flora", "gideon", "hazel", "isla", "jasper", "keira", "luca", "maren", "nova",
    "orion", "paige", "reed", "selene", "theo", "ursa", "val", "wyatt", "xavier", "zoe",
    "ava", "blake", "corin", "dax", "ember", "finn", "gia", "halo", "idris", "jade",
    "kai", "luna", "moss", "nyx", "onyx", "petra", "rune", "sage", "talia", "vex",
    "wynn", "zephyr", "ariel", "blaze", "circe", "dune", "echo", "fable", "grove", "hex",
    "ink", "juno", "kit", "lark", "maple", "nim", "oak", "pixel", "quill", "raven",
]
BOARD_NAMES = [
    "general", "announcements", "random", "projects", "support", "retro", "late-night", "build-log",
    "workshop", "showcase", "ops", "feedback", "design", "backend", "frontend", "infra",
    "mobile", "devops", "security", "data", "ml-experiments", "ux-research", "sprint-planning",
    "incident-reports", "book-club", "music", "gaming", "food", "pets", "fitness",
    "travel", "photography", "art", "memes", "hot-takes", "ship-it", "code-review",
    "pair-programming", "mentorship", "career", "interviews", "onboarding", "tooling",
    "automation", "monitoring", "testing", "documentation", "architecture", "rfc-drafts",
    "demos",
]
BIO_PARTS = [
    "loves terminal tools", "night owl", "ships side projects", "documents everything",
    "debugs first, talks later", "collects mechanical keyboards", "writes tiny scripts",
    "keeps the board tidy", "builds weird demos", "always testing edge cases",
    "automates everything", "vim enthusiast", "emacs convert", "linux from scratch survivor",
    "rust evangelist", "python whisperer", "sql wizard", "css magician",
    "full-stack generalist", "backend purist", "frontend perfectionist",
    "infra nerd", "open source contributor", "meetup organizer",
    "conference speaker", "blog writer", "podcast listener", "early adopter",
    "late bloomer", "perpetual learner",
]
OPENERS = [
    "Has anyone else noticed", "I've been thinking about", "Just spent 3 hours debugging",
    "Quick question about", "PSA:", "Heads up everyone,", "So I finally figured out",
    "Can someone explain why", "Hot take:", "Unpopular opinion:",
    "I just discovered", "Anyone else struggling with", "Pro tip:",
    "TIL that", "Friendly reminder:", "Update on", "Good news:",
    "Bad news:", "Not sure if this is the right board but", "Long time lurker, first time poster.",
    "I know this has been discussed before, but", "Just want to say thanks to everyone who",
    "Okay hear me out.", "Is it just me or", "Shoutout to",
    "I wrote a script that", "Finally shipped", "Working on a side project that",
    "Need some feedback on", "Does anyone have experience with",
]
MIDDLES = [
    "the new authentication flow", "our CI/CD pipeline", "the database migration from last week",
    "the search indexing strategy", "how we handle error boundaries", "the caching layer",
    "the API rate limiter", "our deployment rollback process", "the WebSocket reconnection logic",
    "the permission system", "how the feed algorithm works", "the notification queue",
    "the image processing pipeline", "our logging infrastructure", "the test harness",
    "the config management approach", "how we do feature flags", "the monitoring dashboard",
    "our incident response playbook", "the data export tool", "the onboarding flow",
    "the new dark mode implementation", "our accessibility audit results",
    "the performance regression from Tuesday", "the memory leak in the worker pool",
    "how TypeScript strict mode broke half our tests", "the Python 3.14 upgrade path",
    "our Docker image sizes", "the Kubernetes migration timeline",
    "the new team lead's coding standards",
]
CLOSERS = [
    "and I think we should revisit this next sprint.",
    "— thoughts?",
    "but I could be wrong about this.",
    "and it completely changed how I think about the problem.",
    "so if anyone has a better approach, I'm all ears.",
    "and honestly it was easier than I expected.",
    "which is why I'm posting at 2am.",
    "but the tradeoffs are worth discussing.",
    "and the results were surprising.",
    "so I documented everything in the wiki.",
    "and I'd love a second pair of eyes on the PR.",
    "because apparently nobody reads the README.",
    "and I think this affects more people than realize.",
    "but let's not bikeshed on this one.",
    "and I'll write up a proper RFC if there's interest.",
    "so keep an eye on your alerts this week.",
    "which is a huge win for developer experience.",
    "and I can't believe it took this long to fix.",
    "— link in thread.",
    "and I'm genuinely curious what others think.",
]
REPLY_OPENERS = [
    "Totally agree.", "Strong disagree.", "This is exactly what I was thinking.",
    "Wait, really?", "+1 on this.", "I ran into the same thing last week.",
    "Have you tried", "The docs actually say", "I think the issue is",
    "Good point, but", "FWIW,", "Interesting. In my experience,",
    "Counterpoint:", "This reminds me of", "Following up on this —",
    "Late to this thread but", "Just tested this and", "Can confirm.",
    "Hmm, not sure I agree.", "This is the way.",
]
REPLY_DETAILS = [
    "using a connection pool instead of individual connections.",
    "the root cause was a missing index on the timestamp column.",
    "we had a similar issue and ended up rewriting the whole module.",
    "I think the real question is whether we even need this feature.",
    "it works on my machine but fails in CI, classic.",
    "the fix is a one-liner but the test is 200 lines.",
    "I wrote a blog post about this exact problem last year.",
    "the Python docs are misleading on this point.",
    "we should pair on this tomorrow if you're free.",
    "I'll open a PR with a minimal repro.",
    "the real problem is the schema design, not the query.",
    "we discussed this in the architecture review and decided to defer.",
    "this is blocked on the infrastructure team's migration.",
    "let's timebox the investigation to 2 hours max.",
    "I'll add this to the retro agenda.",
]


@dataclass(frozen=True)
class SeedConfig:
    users: int
    posts: int
    boards: int
    replies: int
    seed: int
    reset: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Seed fake SQLite BBS data")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--posts", type=int, default=500)
    parser.add_argument("--boards", type=int, default=12)
    parser.add_argument("--replies", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true")
    return parser


def validate_args(args: argparse.Namespace) -> SeedConfig:
    users = max(1, args.users)
    posts = max(1, args.posts)
    boards = max(1, args.boards)
    replies = min(max(0, args.replies), max(0, posts - 1))
    return SeedConfig(
        users=users,
        posts=posts,
        boards=boards,
        replies=replies,
        seed=args.seed,
        reset=args.reset,
    )


def database_has_data() -> bool:
    init_db()
    with engine.begin() as connection:
        return any(
            int(connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()) > 0
            for table in ("users", "boards", "posts")
        )


def clear_database() -> None:
    init_db()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM posts"))
        connection.execute(text("DELETE FROM users"))
        connection.execute(text("DELETE FROM boards"))


def generate_usernames(count: int, rng: random.Random) -> list[str]:
    usernames: list[str] = []
    source_size = len(FIRST_NAMES)
    for index in range(count):
        base = FIRST_NAMES[index % source_size]
        suffix = index // source_size
        usernames.append(base if suffix == 0 else f"{base}{suffix}")
    rng.shuffle(usernames)
    return usernames


def generate_boards(count: int) -> list[str]:
    names = ["general"]
    for board in BOARD_NAMES:
        if board == "general":
            continue
        if len(names) >= count:
            break
        names.append(board)
    while len(names) < count:
        names.append(f"board-{len(names) + 1}")
    return names


def generate_bios(usernames: list[str], rng: random.Random) -> dict[str, str]:
    bios: dict[str, str] = {}
    for username in usernames:
        bios[username] = f"{username} {rng.choice(BIO_PARTS)}."
    return bios


def generate_message(rng: random.Random) -> str:
    opener = rng.choice(OPENERS)
    middle = rng.choice(MIDDLES)
    closer = rng.choice(CLOSERS)
    # ~30% chance of a longer multi-sentence message
    if rng.random() < 0.3:
        extra_middle = rng.choice(MIDDLES)
        extra_closer = rng.choice(CLOSERS)
        return f"{opener} {middle} {closer} Also, {extra_middle} {extra_closer}"
    return f"{opener} {middle} {closer}"


def generate_reply_message(rng: random.Random) -> str:
    opener = rng.choice(REPLY_OPENERS)
    detail = rng.choice(REPLY_DETAILS)
    # ~20% chance of a longer reply
    if rng.random() < 0.2:
        extra = rng.choice(REPLY_DETAILS)
        return f"{opener} {detail} Also, {extra}"
    return f"{opener} {detail}"


def build_rows(config: SeedConfig) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    rng = random.Random(config.seed)
    base_time = datetime(2026, 3, 24, 14, 0, 0)

    usernames = generate_usernames(config.users, rng)
    boards = generate_boards(config.boards)
    bios = generate_bios(usernames, rng)

    board_rows = [
        {
            "id": index + 1,
            "slug": board,
            "name": board.replace("-", " ").title(),
            "created_at": (base_time + timedelta(minutes=index)).isoformat(timespec="seconds"),
        }
        for index, board in enumerate(boards)
    ]

    user_rows = [
        {
            "id": index + 1,
            "username": username,
            "joined_at": (base_time - timedelta(days=30 - min(index, 29))).isoformat(timespec="seconds"),
            "bio": bios[username],
            "pin": f"{rng.randint(0, 9999):04d}",
        }
        for index, username in enumerate(usernames)
    ]

    user_id_by_name = {row["username"]: row["id"] for row in user_rows}
    board_id_by_slug = {row["slug"]: row["id"] for row in board_rows}
    post_rows: list[dict[str, object]] = []
    posts_by_board: dict[str, list[int]] = {board: [] for board in boards}

    root_posts = max(1, config.posts - config.replies)
    reply_posts = config.posts - root_posts

    for index in range(root_posts):
        board = boards[index % len(boards)]
        username = usernames[index % len(usernames)]
        post_id = len(post_rows) + 1
        post_rows.append(
            {
                "id": post_id,
                "user_id": user_id_by_name[username],
                "board_id": board_id_by_slug[board],
                "parent_post_id": None,
                "message": generate_message(rng),
                "timestamp": (base_time + timedelta(minutes=index)).isoformat(timespec="seconds"),
            }
        )
        posts_by_board[board].append(post_id)

    for index in range(reply_posts):
        board = boards[index % len(boards)]
        if not posts_by_board[board]:
            board = "general"
        username = usernames[(index + root_posts) % len(usernames)]
        parent_post_id = rng.choice(posts_by_board[board])
        post_id = len(post_rows) + 1
        post_rows.append(
            {
                "id": post_id,
                "user_id": user_id_by_name[username],
                "board_id": board_id_by_slug[board],
                "parent_post_id": parent_post_id,
                "message": generate_reply_message(rng),
                "timestamp": (base_time + timedelta(minutes=root_posts + index)).isoformat(timespec="seconds"),
            }
        )
        posts_by_board[board].append(post_id)

    return user_rows, board_rows, post_rows


def seed_database(config: SeedConfig) -> None:
    if database_has_data():
        if not config.reset:
            raise SystemExit(f"{get_db_path()} already contains data; use --reset to replace it.")
        clear_database()

    user_rows, board_rows, post_rows = build_rows(config)

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users (id, username, joined_at, bio, pin)
                VALUES (:id, :username, :joined_at, :bio, :pin)
                """
            ),
            user_rows,
        )
        connection.execute(
            text(
                """
                INSERT INTO boards (id, slug, name, created_at)
                VALUES (:id, :slug, :name, :created_at)
                """
            ),
            board_rows,
        )
        connection.execute(
            text(
                """
                INSERT INTO posts (id, user_id, board_id, parent_post_id, message, timestamp)
                VALUES (:id, :user_id, :board_id, :parent_post_id, :message, :timestamp)
                """
            ),
            post_rows,
        )

    print(
        f"Seeded {len(user_rows)} users, {len(board_rows)} boards, and {len(post_rows)} posts into {get_db_path()}."
    )


def main() -> None:
    config = validate_args(build_parser().parse_args())
    init_db()
    seed_database(config)


if __name__ == "__main__":
    main()
