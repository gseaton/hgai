"""Hash a password with bcrypt, matching the scheme used for accounts.password_hash.

Usage:
    python scripts/hash_password.py [password]

If no password is given as an argument, you will be prompted for one.
"""

import getpass
import sys

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Password: ")
    hashed = hash_password(password)
    print(f"Hashed: {hashed}")
    print(f"Verifies: {verify_password(password, hashed)}")


if __name__ == "__main__":
    main()
