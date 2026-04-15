"""Door games for the BBS.

Three classic BBS-style games: Trivia, Hangman, and Number Guesser.
High scores are saved to the database via services.save_score().
"""

import os
import random
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from db import engine
import services
import display

# ---------------------------------------------------------------------------
# Trivia question bank (CS/tech themed)
# ---------------------------------------------------------------------------

TRIVIA_POOL = [
    {"q": "What does SQL stand for?", "a": "Structured Query Language",
     "wrong": ["Simple Query Language", "Standard Question Language", "Sequential Query Logic"]},
    {"q": "Which data structure uses LIFO ordering?", "a": "Stack",
     "wrong": ["Queue", "Linked List", "Tree"]},
    {"q": "What HTTP status code means 'Not Found'?", "a": "404",
     "wrong": ["200", "500", "301"]},
    {"q": "What does 'git' stand for?", "a": "Nothing — Linus named it as British slang",
     "wrong": ["Global Information Tracker", "GNU Interactive Tool", "Graph Index Tree"]},
    {"q": "Which language was Python named after?", "a": "Monty Python's Flying Circus",
     "wrong": ["The snake", "A Greek myth", "A math theorem"]},
    {"q": "What is the time complexity of binary search?", "a": "O(log n)",
     "wrong": ["O(n)", "O(n log n)", "O(1)"]},
    {"q": "What does HTML stand for?", "a": "HyperText Markup Language",
     "wrong": ["High Tech Modern Language", "HyperTransfer Markup Logic", "Home Tool Markup Language"]},
    {"q": "Which command stages changes in Git?", "a": "git add",
     "wrong": ["git stage", "git commit", "git push"]},
    {"q": "What is the default port for HTTP?", "a": "80",
     "wrong": ["443", "8080", "21"]},
    {"q": "What does API stand for?", "a": "Application Programming Interface",
     "wrong": ["Advanced Program Interaction", "Application Process Integration", "Automated Programming Interface"]},
    {"q": "What is the smallest unit of data in computing?", "a": "Bit",
     "wrong": ["Byte", "Nibble", "Word"]},
    {"q": "Which of these is NOT a Python data type?", "a": "array",
     "wrong": ["list", "tuple", "dict"]},
    {"q": "What does CSS stand for?", "a": "Cascading Style Sheets",
     "wrong": ["Computer Style Sheets", "Creative Style System", "Colorful Style Sheets"]},
    {"q": "Which sorting algorithm has the best average-case complexity?", "a": "Merge Sort — O(n log n)",
     "wrong": ["Bubble Sort — O(n²)", "Selection Sort — O(n²)", "Insertion Sort — O(n²)"]},
    {"q": "What does the 'S' in HTTPS stand for?", "a": "Secure",
     "wrong": ["Simple", "Standard", "System"]},
    {"q": "Which operator is used for exponentiation in Python?", "a": "**",
     "wrong": ["^", "^^", "pow only"]},
    {"q": "What is the result of 0.1 + 0.2 in Python?", "a": "0.30000000000000004",
     "wrong": ["0.3", "0.30", "Error"]},
    {"q": "What does JSON stand for?", "a": "JavaScript Object Notation",
     "wrong": ["Java Standard Object Notation", "JavaScript Online Notation", "Java Source Object Network"]},
    {"q": "Which protocol does email sending typically use?", "a": "SMTP",
     "wrong": ["HTTP", "FTP", "TCP"]},
    {"q": "What year was Python first released?", "a": "1991",
     "wrong": ["1989", "1995", "2000"]},
]

# ---------------------------------------------------------------------------
# Hangman word list
# ---------------------------------------------------------------------------

HANGMAN_WORDS = [
    "python", "algorithm", "database", "function", "variable",
    "compiler", "terminal", "recursion", "boolean", "iterator",
    "debugger", "framework", "protocol", "encryption", "bandwidth",
    "repository", "interface", "exception", "parameter", "callback",
]

HANGMAN_ART = [
    """
  +---+
  |   |
      |
      |
      |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
      |
      |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
  |   |
      |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
 /|   |
      |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
 /|\\  |
      |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
 /|\\  |
 /    |
      |
=========
    """,
    """
  +---+
  |   |
  O   |
 /|\\  |
 / \\  |
      |
=========
    """,
]

# ---------------------------------------------------------------------------
# Trivia game
# ---------------------------------------------------------------------------

def play_trivia(username):
    print(display.paint("\n═══ TRIVIA CHALLENGE ═══", display.FG_CYAN, display.BOLD))
    print("Answer 10 questions. 10 points each.\n")

    questions = random.sample(TRIVIA_POOL, min(10, len(TRIVIA_POOL)))
    score = 0

    for i, q in enumerate(questions, 1):
        print(display.paint(f"Question {i}:", display.FG_YELLOW, display.BOLD))
        print(f"  {q['q']}\n")

        options = [q["a"]] + q["wrong"]
        random.shuffle(options)

        for j, opt in enumerate(options, 1):
            print(f"  {j}. {opt}")

        try:
            answer = input("\nYour answer (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGame aborted.")
            return

        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options) and options[idx] == q["a"]:
                print(display.paint("  Correct! +10 pts", display.FG_GREEN, display.BOLD))
                score += 10
            else:
                print(display.paint(f"  Wrong! Answer: {q['a']}", display.FG_RED))
        except (ValueError, IndexError):
            print(display.paint(f"  Invalid input. Answer: {q['a']}", display.FG_RED))

        print()

    print(display.paint(f"Final score: {score}/100", display.FG_YELLOW, display.BOLD))
    _save_score(username, "trivia", score)


# ---------------------------------------------------------------------------
# Hangman game
# ---------------------------------------------------------------------------

def play_hangman(username):
    print(display.paint("\n═══ HANGMAN ═══", display.FG_CYAN, display.BOLD))
    print("Guess the tech word. 6 wrong guesses and you're out!\n")

    word = random.choice(HANGMAN_WORDS)
    guessed = set()
    wrong = 0
    max_wrong = len(HANGMAN_ART) - 1

    while wrong < max_wrong:
        print(HANGMAN_ART[wrong])
        revealed = " ".join(c if c in guessed else "_" for c in word)
        print(f"  Word: {revealed}")
        print(f"  Guessed: {', '.join(sorted(guessed)) if guessed else 'none'}")

        if all(c in guessed for c in word):
            score = max(10, 100 - wrong * 15)
            print(display.paint(f"\n  You won! The word was '{word}'.", display.FG_GREEN, display.BOLD))
            print(display.paint(f"  Score: {score}", display.FG_YELLOW, display.BOLD))
            _save_score(username, "hangman", score)
            return

        try:
            guess = input("\nGuess a letter: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nGame aborted.")
            return

        if not guess or len(guess) != 1 or not guess.isalpha():
            print("  Enter a single letter.")
            continue

        if guess in guessed:
            print("  Already guessed that letter.")
            continue

        guessed.add(guess)
        if guess not in word:
            wrong += 1
            print(display.paint("  Miss!", display.FG_RED))
        else:
            print(display.paint("  Hit!", display.FG_GREEN))

    print(HANGMAN_ART[wrong])
    print(display.paint(f"\n  Game over! The word was '{word}'.", display.FG_RED, display.BOLD))
    _save_score(username, "hangman", 0)


# ---------------------------------------------------------------------------
# Number guesser game
# ---------------------------------------------------------------------------

def play_numguess(username):
    print(display.paint("\n═══ NUMBER GUESSER ═══", display.FG_CYAN, display.BOLD))
    print("I'm thinking of a number between 1 and 100.\n")

    target = random.randint(1, 100)
    attempts = 0

    while True:
        try:
            raw = input("Your guess: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGame aborted.")
            return

        try:
            guess = int(raw)
        except ValueError:
            print("  Enter a number.")
            continue

        attempts += 1

        if guess < target:
            print(display.paint("  Higher!", display.FG_YELLOW))
        elif guess > target:
            print(display.paint("  Lower!", display.FG_YELLOW))
        else:
            score = max(10, 100 - (attempts - 1) * 10)
            print(display.paint(f"\n  Correct! You got it in {attempts} attempts.", display.FG_GREEN, display.BOLD))
            print(display.paint(f"  Score: {score}", display.FG_YELLOW, display.BOLD))
            _save_score(username, "numguess", score)
            return


# ---------------------------------------------------------------------------
# Score saving and menu
# ---------------------------------------------------------------------------

def _save_score(username, game, score):
    """Save a game score to the database."""
    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        services.save_score(conn, uid, game, score)
        new_badges = services.check_achievements(conn, uid)
        for b in new_badges:
            print(display.paint(f"  🏆 New badge unlocked: [{b}]!", display.FG_YELLOW, display.BOLD))


def games_menu(username):
    """Interactive games menu."""
    while True:
        print(display.paint("\n═══ DOOR GAMES ═══", display.FG_CYAN, display.BOLD))
        print("  1. Trivia Challenge")
        print("  2. Hangman")
        print("  3. Number Guesser")
        print("  4. Back to BBS")

        try:
            choice = input("\nPick a game (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            play_trivia(username)
        elif choice == "2":
            play_hangman(username)
        elif choice == "3":
            play_numguess(username)
        elif choice == "4" or choice.lower() in ("q", "quit", "back"):
            break
        else:
            print("Pick 1-4.")
