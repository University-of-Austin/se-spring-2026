# Patrick README

I used Python 3, with sqlalchemy, and no other dependencies. 

My goal is to reach the silver tier.

The biggest difference in approach between JSON and SQL is that for JSON, all the search logic lives in Python, whereas SQL delegates the work to a database. When a user types in the search command, the JSON version loads the entire JSON file into memory as Python objects and loops through every post with an if check to see if the keyword is there, which is O(n). SQL sends SQLite to scan and return only matches in C. If there were a million posts, JSON would have to read hundreds of megabytes into memory per search, whereas SQL would basically stay at around four kilobytes.

Duplicate usernames get one "users" row. Existing users in bbs.db are reused by username. Posts are always inserted, because wiping the DB would destroy posts added via bbs_db.py after migration. Clean import = delete bbs.db first. Each user's joined date is set to the earliest post timestamp from the JSON.

I decided to build a user profile. The command python bbs_db.py profile <username> shows a user's join date, total post count, and bio, if the user exists; otherwise, it prints an error. The command python bbs_db.py bio <username> <text> sets or updates a user's bio as long as the user has already posted at least once. 
