import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path


COOKIE_NAME = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PBKDF2_ITERATIONS = 600_000
MAX_PBKDF2_ITERATIONS = 1_000_000


class CredentialsFileError(Exception):
	pass


def credentials_file() -> Path:
	default_path = Path(__file__).with_name("teachers.json")
	return Path(os.environ.get("TEACHER_CREDENTIALS_FILE", str(default_path)))


def session_secret() -> bytes | None:
	secret = os.environ.get("SESSION_SECRET_KEY", "")
	if len(secret) < 32:
		return None
	return secret.encode("utf-8")


def hash_password(password: str, iterations: int = PBKDF2_ITERATIONS) -> str:
	salt = secrets.token_bytes(16)
	digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
	encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
	encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
	return f"pbkdf2_sha256${iterations}${encoded_salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
	try:
		algorithm, iterations_text, encoded_salt, encoded_digest = password_hash.split("$", 3)
		iterations = int(iterations_text)
		if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= MAX_PBKDF2_ITERATIONS:
			return False
		salt = base64.urlsafe_b64decode(encoded_salt + "=" * (-len(encoded_salt) % 4))
		expected = base64.urlsafe_b64decode(encoded_digest + "=" * (-len(encoded_digest) % 4))
		actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
		return hmac.compare_digest(actual, expected)
	except (ValueError, TypeError):
		return False


def load_teacher_credentials() -> dict[str, str]:
	path = credentials_file()
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except (OSError, UnicodeError, json.JSONDecodeError) as error:
		raise CredentialsFileError from error

	teachers = data.get("teachers") if isinstance(data, dict) else None
	if not isinstance(teachers, dict) or any(
		not isinstance(username, str) or not isinstance(password_hash, str)
		for username, password_hash in teachers.items()
	):
		raise CredentialsFileError
	return teachers


def create_session_token(username: str, expires_at: int | None = None) -> str:
	secret = session_secret()
	if secret is None:
		raise RuntimeError("SESSION_SECRET_KEY must contain at least 32 characters")

	payload = json.dumps(
		{
			"username": username,
			"expires_at": (
				int(time.time()) + SESSION_TTL_SECONDS if expires_at is None else expires_at
			),
		},
		separators=(",", ":"),
	).encode("utf-8")
	encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
	signature = hmac.new(secret, encoded_payload.encode("ascii"), hashlib.sha256).hexdigest()
	return f"{encoded_payload}.{signature}"


def get_session_username(token: str | None, now: int | None = None) -> str | None:
	secret = session_secret()
	if secret is None or not token:
		return None

	try:
		encoded_payload, signature = token.split(".", 1)
		expected_signature = hmac.new(
			secret, encoded_payload.encode("ascii"), hashlib.sha256
		).hexdigest()
		if not hmac.compare_digest(signature, expected_signature):
			return None

		payload_bytes = base64.urlsafe_b64decode(
			encoded_payload + "=" * (-len(encoded_payload) % 4)
		)
		payload = json.loads(payload_bytes)
		if not isinstance(payload, dict):
			return None
		username = payload.get("username")
		expires_at = payload.get("expires_at")
		if not isinstance(username, str) or not isinstance(expires_at, int):
			return None
		if expires_at <= (int(time.time()) if now is None else now):
			return None
		return username
	except (ValueError, TypeError, json.JSONDecodeError):
		return None


def main() -> None:
	parser = argparse.ArgumentParser(description="Add or update a teacher login.")
	parser.add_argument("username")
	username = parser.parse_args().username.strip()
	if not username:
		parser.error("username cannot be empty")

	password = getpass.getpass("Teacher password: ")
	confirmation = getpass.getpass("Confirm password: ")
	if not password or password != confirmation:
		parser.error("passwords must be non-empty and match")

	path = credentials_file()
	try:
		teachers = load_teacher_credentials() if path.exists() else {}
	except CredentialsFileError:
		parser.error(f"credentials file is invalid: {path}")
	teachers[username] = hash_password(password)
	path.parent.mkdir(parents=True, exist_ok=True)
	temporary_path = path.with_name(f"{path.name}.{secrets.token_hex(8)}.tmp")
	temporary_path.write_text(
		json.dumps({"teachers": teachers}, indent=2) + "\n", encoding="utf-8"
	)
	temporary_path.chmod(0o600)
	temporary_path.replace(path)
	print(f"Teacher login saved to {path}")


if __name__ == "__main__":
	main()
