## How to Run 
1. Install Dependencies: 
```pip3 install -r requirements.txt```

2. Start the server: 
```python3 -m uvicorn main:app --port 8000```
The database is created automatically on the first run.

## Tier Targeted
Bronze 

## Design decisions 
I nested posts under users because posts belong to a user — the URL reflects that relationship. It makes it clear you're getting posts that belong to a specific user.
Chose /posts over /messages because the bulletin board system uses the word 'post' rather than 'message' making it more conventional to use. 
Chose hard delete for DELETE /posts/{id} because it was under the table of REST commands, and for a simple BBS there's no need to recover deleted posts.
Kept raw SQL with text() from A1 because it makes the database queries transparent and easy to debug. The ORM would hide the SQL, making it harder to verify correct behavior.

## Schema Changes 

**Users table:** Added `created_at TEXT NOT NULL` to track when a user was created, since the API response requires it. Removed `bio TEXT` because it was not needed for bronze tier.

**Posts table:** Renamed `timestamp` to `created_at` to match the API response spec. Added `created_at TEXT NOT NULL`.

**Behavior change:** Removed auto-create-user logic from A1. In A1, posting as an unknown user would silently create them. In A2, users must be created explicitly via `POST /users` first. If a user does not exist when `POST /posts` is called, the API returns 404. This change moves user creation logic out of the database layer and into the API layer in `main.py`. 

##Reason behind the tests
These are the three things that the `run_delete_checks` checks: deleting a post that exists seeing if it returns 204 for "no content", getting that same post after deleting it seeing if it returns 404 for "not found", deleting a post id that was never there which should return 404 for "not found".
There are three things that the `run_pagination_checks` checks: limited responses based on number of arguments, if you ask for 2 posts, you get at most 2 back, offset works — if you skip the first item, the results start from the second one, invalid values are rejected — limit of 0, limit of 500, or negative offset all return 422 for "unprocessable entity". 
There are two things that the `run_field_shapes_checks` checks: the user response has exactly username and created_at — no extra fields, nothing missing and that a post response has exactly id, username, message, and created_at — no extra fields, nothing missing.

## X-Username and Authentication

The `X-Username` header is not real authentication it simply matches the name provided to a username in the database without verifying that the person making the request is actually that user. Anyone could send `X-Username: alice` and the server would accept it.

For real authentication, users would need to log in with a username and password. The server would verify that the credentials match what is stored for that user before allowing them to post. This ensures that only the real alice can post as alice. Also there could be some communication between the user's device and the server to determine if the device belongs to that user specifically so that someone couldn't just copy the person's username and password on their own machine. Although this is not the most ideal and secure solution but it is definitely a better start comparatively to the `X-Username` used in this context. 



