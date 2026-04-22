"""Reaction kinds live in constants.REACTION_KINDS and must flow into each
consumer: the router Enum allowlist and the repository's aggregate-counts
SQL. These checks guarantee the wiring stays live — if someone re-hardcodes
the list at any layer, the corresponding assertion below starts failing."""
from constants import REACTION_KINDS
from repositories import posts as posts_repo
from repositories import reactions as reactions_repo
from repositories import users as users_repo
from routers.reactions import ReactionKind


def test_router_enum_matches_constants():
    assert tuple(k.value for k in ReactionKind) == REACTION_KINDS


def test_repository_aggregate_includes_every_kind():
    """The shared SELECT's reaction_counts dict must contain exactly the
    keys in REACTION_KINDS, zero-filled when no reactions exist."""
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "hi")
    fetched = posts_repo.get_by_id(post["id"])
    assert set(fetched["reaction_counts"].keys()) == set(REACTION_KINDS)
    assert all(v == 0 for v in fetched["reaction_counts"].values())


def test_repository_counts_add_up_per_kind():
    """Every kind in REACTION_KINDS must produce a distinct counter in the
    aggregate — guard against collisions in the generated SQL aliases."""
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "hi")
    for kind in REACTION_KINDS:
        # Each kind needs a distinct user to avoid the (user, post, kind)
        # primary-key collision; but we can reuse alice since kind differs.
        reactions_repo.add(alice["id"], post["id"], kind)
    fetched = posts_repo.get_by_id(post["id"])
    assert all(fetched["reaction_counts"][k] == 1 for k in REACTION_KINDS)
