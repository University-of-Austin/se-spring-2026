"""Door games for the BBS -- classic text-based mini-games."""

import random
from datetime import datetime

from sqlalchemy import text

from db import engine
from display import paint, fmt_ok, fmt_err, fmt_dim, print_header, BOLD, BR_CYAN, BR_YELLOW, BR_GREEN, BR_RED, DIM, GREEN, CYAN, WHITE, BR_WHITE


# ── Trivia ──────────────────────────────────────────────────────

TRIVIA_POOL = [
    ("What does BBS stand for?",
     ["Bulletin Board System", "Binary Backup Service", "Basic Browser Shell", "Big Byte Storage"], 0),
    ("What year was the first BBS created?",
     ["1978", "1983", "1991", "1969"], 0),
    ("Which language was Python named after?",
     ["Monty Python", "A snake species", "A Greek myth", "A math term"], 0),
    ("What does SQL stand for?",
     ["Structured Query Language", "Simple Question Language", "System Quality Logic", "Sequential Query Lookup"], 0),
    ("What is the default port for HTTP?",
     ["80", "443", "8080", "21"], 0),
    ("Which data structure uses FIFO?",
     ["Queue", "Stack", "Tree", "Graph"], 0),
    ("What does JSON stand for?",
     ["JavaScript Object Notation", "Java System Object Network", "Joint Standard Open Node", "JSON Object Naming"], 0),
    ("What is the time complexity of binary search?",
     ["O(log n)", "O(n)", "O(n^2)", "O(1)"], 0),
    ("Which command shows git commit history?",
     ["git log", "git history", "git show", "git commits"], 0),
    ("What does API stand for?",
     ["Application Programming Interface", "Advanced Program Integration", "Automated Process Input", "Application Process Instance"], 0),
    ("In SQL, which clause filters rows?",
     ["WHERE", "HAVING", "GROUP BY", "ORDER BY"], 0),
    ("What is a foreign key?",
     ["A reference to another table's primary key", "An encrypted column", "A backup key", "A temporary index"], 0),
    ("What protocol do BBSes traditionally use?",
     ["Dial-up modem", "HTTP", "FTP", "SSH"], 0),
    ("Which of these is NOT a Python data type?",
     ["array", "list", "tuple", "dict"], 0),
    ("What does ORM stand for?",
     ["Object-Relational Mapping", "Online Resource Manager", "Open Record Model", "Output Read Module"], 0),
    ("What is SQLite?",
     ["An embedded database engine", "A cloud database", "A SQL linter", "A query optimizer"], 0),
    ("What does CRUD stand for?",
     ["Create Read Update Delete", "Copy Run Undo Deploy", "Cache Render Update Display", "Compile Run Upload Debug"], 0),
    ("Which HTTP method is used to create a resource?",
     ["POST", "GET", "PUT", "DELETE"], 0),
    ("What is a primary key?",
     ["A unique identifier for a row", "The first column in a table", "An encryption key", "A password hash"], 0),
    ("What year was SQLite first released?",
     ["2000", "1995", "2005", "2010"], 0),
]


def play_trivia(username):
    """Play a 10-question trivia game. Returns the score."""
    print_header("Door Game: Trivia Challenge")
    print(fmt_dim("Answer 10 questions. 10 points each. Good luck!\n"))

    questions = random.sample(TRIVIA_POOL, min(10, len(TRIVIA_POOL)))
    score = 0
    labels = ["A", "B", "C", "D"]

    for i, (question, choices, correct_idx) in enumerate(questions, 1):
        # Shuffle choices but track the correct answer
        indices = list(range(len(choices)))
        random.shuffle(indices)
        shuffled = [choices[j] for j in indices]
        new_correct = indices.index(correct_idx)

        print(f"  {paint(f'Q{i}.', BOLD, BR_CYAN)} {paint(question, WHITE)}")
        for j, choice in enumerate(shuffled):
            print(f"      {paint(labels[j], BOLD, BR_YELLOW)}) {choice}")

        while True:
            try:
                ans = input(f"  {paint('Your answer (A-D): ', DIM)}").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{fmt_dim('Game aborted.')}")
                return score
            if ans in labels[:len(choices)]:
                break
            print(fmt_err("Enter A, B, C, or D."))

        chosen = labels.index(ans)
        if chosen == new_correct:
            score += 10
            print(paint("  Correct!", BR_GREEN))
        else:
            print(paint(f"  Wrong! Answer: {labels[new_correct]}) {shuffled[new_correct]}", BR_RED))
        print()

    print(f"  {paint('Final Score:', BOLD, BR_WHITE)} {paint(str(score), BOLD, BR_YELLOW)}/100")
    _save_score(username, "trivia", score)
    return score


# ── Hangman ─────────────────────────────────────────────────────

WORD_LIST = [
    "python", "database", "terminal", "modem", "bulletin", "server",
    "compile", "syntax", "binary", "socket", "kernel", "thread",
    "packet", "buffer", "router", "cipher", "schema", "query",
    "deploy", "branch", "commit", "cursor", "parser", "module",
]

HANGMAN_STAGES = [
    """
      +---+
      |   |
          |
          |
          |
          |
    =========""",
    """
      +---+
      |   |
      O   |
          |
          |
          |
    =========""",
    """
      +---+
      |   |
      O   |
      |   |
          |
          |
    =========""",
    """
      +---+
      |   |
      O   |
     /|   |
          |
          |
    =========""",
    """
      +---+
      |   |
      O   |
     /|\\  |
          |
          |
    =========""",
    """
      +---+
      |   |
      O   |
     /|\\  |
     /    |
          |
    =========""",
    """
      +---+
      |   |
      O   |
     /|\\  |
     / \\  |
          |
    =========""",
]


def play_hangman(username):
    """Play hangman. Returns score based on remaining lives."""
    print_header("Door Game: Hangman")
    print(fmt_dim("Guess the word one letter at a time. 6 wrong guesses and you're out!\n"))

    word = random.choice(WORD_LIST)
    guessed = set()
    wrong = 0
    max_wrong = len(HANGMAN_STAGES) - 1

    while wrong < max_wrong:
        # Display current state
        display = " ".join(c if c in guessed else "_" for c in word)
        print(HANGMAN_STAGES[wrong])
        print(f"\n  Word: {paint(display, BOLD, BR_CYAN)}")
        if guessed:
            missed = sorted(c for c in guessed if c not in word)
            if missed:
                print(f"  Missed: {paint(' '.join(missed), BR_RED)}")

        if all(c in guessed for c in word):
            break

        while True:
            try:
                guess = input(f"  {paint('Guess a letter: ', DIM)}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{fmt_dim('Game aborted.')}")
                return 0
            if len(guess) == 1 and guess.isalpha():
                if guess in guessed:
                    print(fmt_dim("Already guessed that letter."))
                    continue
                break
            print(fmt_err("Enter a single letter."))

        guessed.add(guess)
        if guess not in word:
            wrong += 1
            print(paint("  Miss!", BR_RED))
        else:
            print(paint("  Hit!", BR_GREEN))

    # End state
    if all(c in guessed for c in word):
        print(f"\n  {paint('You won!', BOLD, BR_GREEN)} The word was: {paint(word, BOLD, BR_CYAN)}")
        score = max(10, (max_wrong - wrong) * 15)
    else:
        print(HANGMAN_STAGES[wrong])
        print(f"\n  {paint('Game over!', BOLD, BR_RED)} The word was: {paint(word, BOLD, BR_CYAN)}")
        score = 0

    print(f"  {paint('Score:', BOLD, BR_WHITE)} {paint(str(score), BOLD, BR_YELLOW)}")
    _save_score(username, "hangman", score)
    return score


# ── Number Guessing ─────────────────────────────────────────────

def play_numguess(username):
    """Guess a number 1-100. Fewer attempts = higher score."""
    print_header("Door Game: Number Guesser")
    print(fmt_dim("I'm thinking of a number between 1 and 100."))
    print(fmt_dim("Guess it in as few tries as possible!\n"))

    target = random.randint(1, 100)
    attempts = 0
    max_attempts = 10

    while attempts < max_attempts:
        try:
            raw = input(f"  {paint(f'Guess ({max_attempts - attempts} left): ', DIM)}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{fmt_dim('Game aborted.')}")
            return 0

        try:
            guess = int(raw)
        except ValueError:
            print(fmt_err("Enter a number."))
            continue

        attempts += 1

        if guess < target:
            print(paint("  Too low!", BR_YELLOW))
        elif guess > target:
            print(paint("  Too high!", BR_YELLOW))
        else:
            print(f"\n  {paint('Correct!', BOLD, BR_GREEN)} You got it in {attempts} tries!")
            score = max(10, 100 - (attempts - 1) * 10)
            print(f"  {paint('Score:', BOLD, BR_WHITE)} {paint(str(score), BOLD, BR_YELLOW)}")
            _save_score(username, "numguess", score)
            return score

    print(f"\n  {paint('Out of guesses!', BOLD, BR_RED)} The number was {paint(str(target), BOLD, BR_CYAN)}.")
    _save_score(username, "numguess", 0)
    return 0


# ── Score Management ────────────────────────────────────────────

def _save_score(username, game, score):
    """Save a high score to the database."""
    with engine.begin() as conn:
        uid = conn.execute(
            text("SELECT id FROM users WHERE username = :u"), {"u": username},
        ).fetchone()
        if not uid:
            return
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            text("INSERT INTO high_scores (user_id, game, score, timestamp) "
                 "VALUES (:uid, :game, :score, :ts)"),
            {"uid": uid[0], "game": game, "score": score, "ts": ts},
        )


def show_leaderboard(game=None):
    """Show high scores. If game is None, show all games."""
    with engine.connect() as conn:
        if game:
            rows = conn.execute(
                text(
                    "SELECT u.username, h.game, h.score, h.timestamp "
                    "FROM high_scores h JOIN users u ON h.user_id = u.id "
                    "WHERE h.game = :g "
                    "ORDER BY h.score DESC LIMIT 10"
                ),
                {"g": game},
            ).fetchall()
            print_header(f"Leaderboard: {game}")
        else:
            rows = conn.execute(
                text(
                    "SELECT u.username, h.game, MAX(h.score) as best, h.timestamp "
                    "FROM high_scores h JOIN users u ON h.user_id = u.id "
                    "GROUP BY u.username, h.game "
                    "ORDER BY best DESC LIMIT 15"
                ),
            ).fetchall()
            print_header("Leaderboard: All Games")

    if not rows:
        print(fmt_dim("No scores yet. Play a game!"))
        return

    for i, row in enumerate(rows, 1):
        user, gname, sc = row[0], row[1], row[2]
        medal = {1: paint("[#1]", BOLD, BR_YELLOW), 2: paint("[#2]", DIM, WHITE), 3: paint("[#3]", DIM, BR_RED)}.get(i, f"  {i}.")
        print(f"  {medal} {paint(user, BOLD, BR_CYAN)}  {paint(gname, DIM)}  {paint(str(sc), BOLD, BR_YELLOW)} pts")
    print()


def games_menu(username):
    """Show the door games menu and let the user pick a game."""
    while True:
        print_header("Door Games")
        print(f"  {paint('1', BOLD, BR_YELLOW)}) Trivia Challenge  {paint('- test your CS knowledge', DIM)}")
        print(f"  {paint('2', BOLD, BR_YELLOW)}) Hangman            {paint('- classic word guessing', DIM)}")
        print(f"  {paint('3', BOLD, BR_YELLOW)}) Number Guesser     {paint('- guess 1-100', DIM)}")
        print(f"  {paint('4', BOLD, BR_YELLOW)}) Leaderboard        {paint('- view high scores', DIM)}")
        print(f"  {paint('q', BOLD, BR_YELLOW)}) Back")
        print()

        try:
            choice = input(f"  {paint('Pick a game: ', DIM)}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if choice == "1":
            play_trivia(username)
        elif choice == "2":
            play_hangman(username)
        elif choice == "3":
            play_numguess(username)
        elif choice == "4":
            show_leaderboard()
        elif choice in ("q", "quit", "back"):
            return
        else:
            print(fmt_err("Pick 1-4 or q."))
