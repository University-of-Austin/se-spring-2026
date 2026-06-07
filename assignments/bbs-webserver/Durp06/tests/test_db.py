"""Test that db.init_db creates exactly the users and posts tables."""
from sqlalchemy import inspect
from db import get_engine, init_db


def test_init_db_creates_correct_tables():
    engine = get_engine("sqlite:///:memory:")
    init_db(engine)
    table_names = set(inspect(engine).get_table_names())
    assert table_names == {"users", "posts"}, f"Expected {{users, posts}}, got {table_names}"
