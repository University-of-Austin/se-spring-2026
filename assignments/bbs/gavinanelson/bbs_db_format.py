from datetime import datetime


def escape_display_text(value: object) -> str:
    escaped: list[str] = []
    for character in str(value):
        if character == "\n":
            escaped.append(r"\n")
        elif character == "\r":
            escaped.append(r"\r")
        elif character == "\t":
            escaped.append(r"\t")
        elif ord(character) < 32 or ord(character) == 127:
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def format_post(post: dict[str, str]) -> str:
    timestamp = datetime.fromisoformat(post["timestamp"]).strftime("%Y-%m-%d %H:%M")
    return f"[{timestamp}] {escape_display_text(post['username'])}: {escape_display_text(post['message'])}"


def format_profile(profile: dict[str, object]) -> str:
    joined = datetime.fromisoformat(str(profile["joined_at"])).strftime("%Y-%m-%d %H:%M")
    return "\n".join(
        [
            f"Username: {escape_display_text(profile['username'])}",
            f"Joined: {joined}",
            f"Posts: {profile['post_count']}",
            f"Bio: {escape_display_text(profile['bio'])}",
        ]
    )


def _format_threaded_post(post: dict[str, object], depth: int) -> str:
    indent = "  " * depth
    timestamp = datetime.fromisoformat(str(post["timestamp"])).strftime("%Y-%m-%d %H:%M")
    return (
        f"{indent}[{timestamp}] (#{post['id']}) "
        f"{escape_display_text(post['username'])}: {escape_display_text(post['message'])}"
    )


def format_threaded_posts(posts: list[dict[str, object]]) -> list[str]:
    posts_by_id = {int(post["id"]): post for post in posts}
    children_by_parent: dict[int, list[dict[str, object]]] = {}
    root_posts: list[dict[str, object]] = []

    for post in posts:
        parent_post_id = post["parent_post_id"]
        if parent_post_id is None or int(parent_post_id) not in posts_by_id:
            root_posts.append(post)
            continue
        children_by_parent.setdefault(int(parent_post_id), []).append(post)

    lines: list[str] = []
    stack: list[tuple[dict[str, object], int]] = [
        (post, 0) for post in reversed(root_posts)
    ]
    while stack:
        post, depth = stack.pop()
        lines.append(_format_threaded_post(post, depth))
        children = children_by_parent.get(int(post["id"]), [])
        for child in reversed(children):
            stack.append((child, depth + 1))
    return lines
