"""FTS5 query-operator safety. If _fts_phrase is wrong, user input containing
FTS operators (:, ^, AND, OR, NEAR, quotes) can crash the parser or leak
query syntax."""
from repositories import posts as posts_repo
from repositories import users as users_repo
from repositories.posts import _fts_phrase


def test_fts_phrase_wraps_in_double_quotes():
    assert _fts_phrase("hello") == '"hello"'


def test_fts_phrase_escapes_embedded_double_quotes():
    # Embedded " must be doubled so the wrapper is not closed prematurely.
    assert _fts_phrase('he said "hi"') == '"he said ""hi"""'


def _seed():
    alice = users_repo.create("alice")
    bob = users_repo.create("bob")
    posts_repo.create(alice["id"], "hello world")
    posts_repo.create(alice["id"], "100% fine")
    posts_repo.create(bob["id"], "snake_case naming")
    posts_repo.create(bob["id"], "nothing special")


def test_search_finds_matching_posts():
    _seed()
    rows = posts_repo.search_posts(q="hello")
    assert len(rows) == 1
    assert rows[0]["message"] == "hello world"
    assert "snippet" in rows[0]


def test_search_rejects_operator_injection_by_treating_as_phrase():
    # "OR" as an FTS operator would broaden the match. Wrapped as a phrase
    # it's just a literal token search — no matches because nothing contains
    # the literal word "OR".
    _seed()
    rows = posts_repo.search_posts(q="hello OR nothing")
    assert rows == []  # phrase "hello OR nothing" matches nothing


def test_search_tolerates_special_chars():
    # Colons, quotes, parens are FTS5 operators. Phrase wrapping neutralizes
    # them — no parser error, just zero matches (nothing contains the phrase).
    _seed()
    rows = posts_repo.search_posts(q='col:on "quote" (paren)')
    assert rows == []


def test_search_top_level_only_excludes_replies():
    """The main feed path (GET /posts) shows only top-level posts; replies
    live under /posts/{id}/replies. Search on the main feed must honor the
    same boundary — otherwise ?q= silently changes what /posts returns."""
    alice = users_repo.create("alice")
    parent = posts_repo.create(alice["id"], "top level hello")
    posts_repo.create(alice["id"], "reply hello", parent_id=parent["id"])

    top = posts_repo.search_posts(q="hello", top_level_only=True)
    assert [r["id"] for r in top] == [parent["id"]]

    both = posts_repo.search_posts(q="hello", top_level_only=False)
    assert len(both) == 2
