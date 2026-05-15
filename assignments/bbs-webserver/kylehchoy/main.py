from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from routers import posts as posts_router
from routers import reactions as reactions_router
from routers import users as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BBS Webserver", lifespan=lifespan)

# CORS for the A4 frontend at localhost:5173 (Vite dev server).
# expose_headers is required because the frontend reads Location from
# POST /posts (for created-resource navigation) and ETag from GET
# /posts/{id} (for conditional refetches). Browsers hide unlisted
# response headers from JS even on same-origin reads, so they must be
# explicitly exposed across origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location", "ETag"],
)

app.include_router(users_router.router)
app.include_router(posts_router.router)
app.include_router(reactions_router.router)
