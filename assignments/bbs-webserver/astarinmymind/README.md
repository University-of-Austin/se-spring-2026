# BBS Webserver

## How to run

Create and activate a virtual environment, then install dependencies:

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Start the server:

```
uvicorn main:app --port 8000
```

Run the verifier (in a second terminal):

```
python verify_api.py
```

The database (`bbs.db`) is created automatically on first request. To start fresh, stop the server, delete `bbs.db`, and restart.

## Tier targeted

Bronze.
