"""Simple web interface for BBS posting."""

from flask import Flask, request, redirect
from datetime import datetime
from sqlalchemy import text
from db import engine, init_db
from printer import print_post

app = Flask(__name__)

MAX_MESSAGE_LENGTH = 140

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Angela's BBS</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: system-ui; max-width: 400px; margin: 40px auto; padding: 20px; }}
        h1 {{ margin-bottom: 20px; }}
        input, textarea {{ width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box; font-size: 16px; }}
        button {{ width: 100%; padding: 12px; background: #333; color: white; border: none; font-size: 16px; cursor: pointer; }}
        button:hover {{ background: #555; }}
        .success {{ color: green; margin-bottom: 20px; }}
        .error {{ color: red; margin-bottom: 20px; }}
        .counter {{ text-align: right; font-size: 14px; color: #666; }}
        .counter.over {{ color: red; }}
        .flair-picker {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }}
        .flair-picker label {{ cursor: pointer; font-size: 24px; padding: 4px; border: 2px solid transparent; border-radius: 4px; }}
        .flair-picker input {{ display: none; }}
        .flair-picker input:checked + span {{ border: 2px solid #333; border-radius: 4px; }}
        .flair-picker span {{ padding: 4px; display: inline-block; }}
    </style>
</head>
<body>
    <h1>Angela's BBS</h1>
    {message}
    <form method="POST">
        <input name="username" placeholder="Your name" required maxlength="20">
        <div class="flair-picker">
            <label><input type="radio" name="flair" value="🐱" required><span>🐱</span></label>
            <label><input type="radio" name="flair" value="🐶"><span>🐶</span></label>
            <label><input type="radio" name="flair" value="🐰"><span>🐰</span></label>
            <label><input type="radio" name="flair" value="🦄"><span>🦄</span></label>
            <label><input type="radio" name="flair" value="🐮"><span>🐮</span></label>
        </div>
        <textarea name="message" placeholder="Your message" rows="3" required maxlength="140" id="msg"></textarea>
        <div class="counter"><span id="count">0</span>/140</div>
        <button type="submit">Post</button>
    </form>
    <script>
        const msg = document.getElementById('msg');
        const count = document.getElementById('count');
        msg.addEventListener('input', () => {{
            count.textContent = msg.value.length;
            count.parentElement.className = msg.value.length > 140 ? 'counter over' : 'counter';
        }});
    </script>
</body>
</html>
"""

def get_or_create_user(conn, username: str) -> int:
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    )
    row = result.fetchone()
    if row:
        return row[0]
    result = conn.execute(
        text("INSERT INTO users (username) VALUES (:username)"),
        {"username": username}
    )
    conn.commit()
    return result.lastrowid


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        username = request.form["username"].strip()
        msg = request.form["message"].strip()
        flair = request.form.get("flair", "").strip()

        if len(username) > 20:
            return HTML_TEMPLATE.format(message='<p class="error">Name too long (max 20 chars)</p>')

        if len(msg) > MAX_MESSAGE_LENGTH:
            return HTML_TEMPLATE.format(message='<p class="error">Message too long (max 140 chars)</p>')

        if username and msg:
            with engine.connect() as conn:
                user_id = get_or_create_user(conn, username)
                # Update flair if provided
                if flair:
                    conn.execute(
                        text("UPDATE users SET flair = :flair WHERE id = :user_id"),
                        {"flair": flair, "user_id": user_id}
                    )
                timestamp = datetime.now().isoformat(timespec="seconds")
                conn.execute(
                    text("INSERT INTO posts (user_id, message, timestamp) VALUES (:user_id, :message, :timestamp)"),
                    {"user_id": user_id, "message": msg, "timestamp": timestamp}
                )
                conn.commit()

            # Print it with flair
            formatted_time = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
            display_name = f"{username} {flair}" if flair else username
            print_post(display_name, msg, formatted_time)

            message = '<p class="success">Posted!</p>'

    return HTML_TEMPLATE.format(message=message)


if __name__ == "__main__":
    init_db()
    print("\n" + "="*40)
    print("Share this URL with classmates:")
    print("  http://<your-ip>:8080")
    print("="*40 + "\n")
    app.run(host="0.0.0.0", port=8080, debug=False)
