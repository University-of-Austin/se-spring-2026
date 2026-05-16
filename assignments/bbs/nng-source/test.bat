@echo off
cd /d "%~dp0"
del /q bbs.json bbs_users.json bbs.db 2>nul

echo ============================================
echo   PART A: JSON BBS
echo ============================================
echo.
echo --- Posting to multiple boards ---
python bbs.py post alice general "Hello, is anyone out there?"
python bbs.py post bob general "Hey Alice! Welcome to the board."
python bbs.py post alice tech "Anyone tried SQLAlchemy?"
python bbs.py post charlie random "Just vibing on the BBS"
echo.
echo --- Threaded replies ---
python bbs.py reply 1 bob "Welcome aboard Alice!"
python bbs.py reply 5 alice "Thanks Bob!"
python bbs.py reply 1 charlie "Hey Alice, nice to meet you!"
echo.
echo --- Read all posts (threaded) ---
python bbs.py read
echo --- Read only the tech board ---
python bbs.py read tech
echo --- List all boards ---
python bbs.py boards
echo --- List all users ---
python bbs.py users
echo --- Search for "Hello" ---
python bbs.py search "Hello"
echo --- Search for "BBS" ---
python bbs.py search "BBS"
echo.
echo --- User profiles ---
python bbs.py bio alice "Retro computing enthusiast"
python bbs.py bio bob "I love databases"
python bbs.py profile alice
python bbs.py profile bob
python bbs.py profile charlie
echo.

echo ============================================
echo   PART B: SQLite BBS
echo ============================================
echo.
echo --- Posting to boards ---
python bbs_db.py post alice general "Hello from the DB side!"
python bbs_db.py post bob tech "SQL is cool"
python bbs_db.py post charlie general "Anyone home?"
python bbs_db.py post dave offtopic "First time here!"
echo.
echo --- Threaded replies ---
python bbs_db.py reply 1 bob "Hey Alice!"
python bbs_db.py reply 5 alice "Hi Bob, glad you're here!"
python bbs_db.py reply 3 dave "I'm home!"
echo.
echo --- Read all posts (threaded) ---
python bbs_db.py read
echo --- Read only general board ---
python bbs_db.py read general
echo --- List all boards ---
python bbs_db.py boards
echo --- List all users ---
python bbs_db.py users
echo --- Search for "cool" ---
python bbs_db.py search "cool"
echo.
echo --- User profiles ---
python bbs_db.py bio bob "Database enthusiast since 2020"
python bbs_db.py bio dave "Newbie explorer"
python bbs_db.py profile bob
python bbs_db.py profile dave
echo.

echo ============================================
echo   PART C: MIGRATION (additive)
echo ============================================
echo.
del /q bbs.db 2>nul
echo --- First migration: JSON to fresh DB ---
python migrate.py
echo.
echo --- Read after migration ---
python bbs_db.py read
echo --- Boards after migration ---
python bbs_db.py boards
echo --- Profile preserved ---
python bbs_db.py profile alice
echo.
echo --- Second migration: should skip all duplicates ---
python migrate.py
echo.
echo --- Add new post to JSON, migrate again ---
python bbs.py post dave tech "Joining from JSON!"
python migrate.py
echo.
echo --- DB now has the new post ---
python bbs_db.py read tech
echo.

echo ============================================
echo   ERROR HANDLING
echo ============================================
echo.
echo --- Reply to nonexistent post ---
python bbs_db.py reply 999 alice "This should fail"
echo.
echo --- Search with no results ---
python bbs_db.py search "xyznonexistent"
echo.
echo --- Profile of unknown user ---
python bbs_db.py profile nobody
echo.
echo --- No arguments (shows usage + Spheal) ---
python bbs_db.py
echo.

echo ============================================
echo   CLEANUP
echo ============================================
del /q bbs.json bbs_users.json bbs.db 2>nul
echo Done! All test artifacts cleaned up.
pause
