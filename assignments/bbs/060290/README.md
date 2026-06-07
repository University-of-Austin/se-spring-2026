
1.Clone the repository and navigate to the assignment folder:

cd assignments/bbs/060290

Install dependencies:

pip install sqlalchemy

Initialize the database by running any bbs_db.py command — it creates bbs.db automatically on first run.
To start with some data, post a few messages using bbs.py first, then run migrate.py to move them into the SQLite database:

python3 bbs.py post <username> <message>
python3 migrate.py

2. Gold 

3. The basic difference - In the JSON version the program loads into memory and sifts through every single input to find the username and their respective data, however the SQL version sifts through the natural ordering that is made by the B-tree structure where the steps taken are proportionate to the depth of the tree. How it works is that it starts with a sqlite master that acts like a  table of contents to locate the different types of tables in the database. This is ultimately faster because, the pages holding the information, which at each node the search elminates half of the data until it reaches it target.

If the database had 100 million users it would take a long time for the JSON to search through it, because it has to load in every data piece then search through the entire database. The SQL will take only about 27 steps to find that data point. 

4. In the case that the database is already made, the migrate program will go through the time stamp of the messages that are already on file so that the post is not duplicated. I found that in order to elminiate a possible duplicate post, the significant difference, besides the name, and message, between a duplicate post is the timestamp. If the program found that the time stamp of the post in bbs.db is the same in the SQLite database then I will skip over it, and if it isn't a duplicate in time stamp then I insert it into the SQLite database. I chose skipping over the duplicates over another method, like wiping the bbs.db file, firstly because it is more programically costly and secondly could lead to data being lost when certain data only lives on the bbs.db, and not the bbs.json file.





The program first checks if the user ID exists before inserting it. If it doesn’t, it inserts it. If it does, it skips it. The migration program checks the timestamp and user ID of the post to ensure that no post is re-added when the migration is run a second time. If the bbs.json file doesn’t exist, the program prints instructions for the user to post before calling the migrate program again. 
It’s not as computationally intensive for the migrate program to check the SQL database for existing users and posts based on their timestamp and user ID because SQL stores the data in specific pages that correlate with the index number, which is sorted by a specific key, making it easier to find than wiping the database entirely. Wiping the database before migrating would destroy any posts that were added directly through bbs_db.py after the original migration—data that exists only in bbs.db and not in bbs.json. Skipping duplicates instead preserves all existing data while still safely re-running the migration.


4. SILVER - 
A new bio column was added to the users table in db.py. This column is of type TEXT and is nullable, ensuring that existing users in the database are not affected while still allowing new users to set a bio.
Two new commands were introduced. The profile <username> command displays a user’s profile, including their join date, number of messages, and bio. The join date is determined by retrieving the earliest timestamp from the posts table, while the message count is calculated using a COUNT query on the same table. The bio is retrieved directly from the users table. The set_bio <username> <bio> command allows a user to update or set their bio.
Key design decisions include calculating the join date and message count dynamically rather than storing them, which avoids redundancy and keeps the data consistent. A unique constraint on usernames ensures that each user can be identified without duplication. For edge cases, if a user has not set a bio, the system returns a concise message indicating that no bio is available. 

GOLD - 
Every time a user runs bbs_db.py they are greeted by an ASCII art Wild West scene that sets the tone for the BBS. The scene features a cowboy, a horse, a coyote, and a desert landscape with a sunset background, displayed in the terminal before any commands run.
The frame is stored as a text file in the wild_west_backgrounds/ folder and is printed to the terminal on every run using the rich library for styled terminal output.
I chose this feature because a BBS is a retro terminal based system and a Wild West theme fits that aesthetic naturally. It gives the BBS personality and makes it feel like a real place rather than just a command line tool.