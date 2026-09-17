"""Create local credentials once, without printing or overwriting them."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if path.exists():
    print(".env already exists; unchanged.")
else:
    template = (root / ".env.example").read_text(encoding="utf-8")
    value = template.replace("replace-with-a-local-password", secrets.token_urlsafe(32))
    with path.open("x", encoding="utf-8") as handle:
        handle.write(value)
    print("Created .env with a random local PostgreSQL password.")
