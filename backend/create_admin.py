"""Bootstrap an administrator account.

    python -m backend.create_admin --username admin --email admin@example.com
    python -m backend.create_admin --username admin --password secret123

If --password is omitted you are prompted securely (input is hidden).
Only the salted hash is stored — the password never appears in code or logs.
"""

import argparse
import getpass

from . import auth


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an admin account.")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--email", help="Admin email (default: username@localhost)")
    parser.add_argument("--password", help="Admin password (prompted if omitted)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password (min 8 characters): ")
    email = args.email or f"{args.username}@localhost"

    try:
        try:
            user = auth.promote_to_admin(args.username)
            print(f"Existing account promoted to admin: {user['username']}")
            print("Its existing password is unchanged.")
        except ValueError:
            user = auth.create_user(args.username, email, password, role="admin")
            print(f"Admin account created: {user['username']} ({user['email']})")
    except ValueError as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
