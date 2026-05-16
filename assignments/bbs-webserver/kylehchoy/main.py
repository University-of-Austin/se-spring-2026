from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import init_db
from routers import posts as posts_router
from routers import reactions as reactions_router
from routers import users as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BBS Webserver", lifespan=lifespan)
app.include_router(users_router.router)
app.include_router(posts_router.router)
app.include_router(reactions_router.router)
