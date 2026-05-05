"""Cross-layer constants.

Reaction kinds are referenced in three places:
  - router path-param validation (Enum)
  - service allowlist (zero-fill + contract surface)
  - repository SQL (per-kind aggregate column in the shared SELECT)

Keeping them in sync by hand means adding a new kind requires three
coordinated edits and missing any one is a silent bug. Declaring the
tuple here lets each layer derive what it needs from a single source.

Kinds must stay lowercase ASCII: the repository layer f-string-interpolates
them into SQL column aliases (safe because the values are closed and
developer-controlled), and the router exposes them literally as URL path
segments.
"""
from typing import Final

REACTION_KINDS: Final[tuple[str, ...]] = ("like", "laugh", "heart")
