import os
import json
import tempfile
import time
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request

from src.app import (
    TeacherLogin,
    activities,
    get_activities,
    login_teacher,
    signup_for_activity,
    unregister_from_activity,
)
from src.auth import (
    COOKIE_NAME,
    create_session_token,
    get_session_username,
    hash_password,
    verify_password,
)


def make_request(token: str | None = None) -> Request:
    headers = []
    if token is not None:
        headers.append((b"cookie", f"{COOKIE_NAME}={token}".encode("ascii")))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


class TeacherAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = patch.dict(os.environ, {"SESSION_SECRET_KEY": "test-session-secret-" * 3})
        self.secret.start()
        self.original_participants = list(activities["Chess Club"]["participants"])

    def tearDown(self) -> None:
        activities["Chess Club"]["participants"][:] = self.original_participants
        self.secret.stop()

    def test_public_activity_list_does_not_require_authentication(self) -> None:
        self.assertIn("Chess Club", get_activities())

    def test_password_hash_verifies_without_storing_plaintext(self) -> None:
        password_hash = hash_password("correct horse battery staple", iterations=100_000)
        self.assertNotIn("correct horse battery staple", password_hash)
        self.assertTrue(verify_password("correct horse battery staple", password_hash))
        self.assertFalse(verify_password("incorrect", password_hash))

    def test_tampered_and_expired_sessions_are_rejected(self) -> None:
        valid_token = create_session_token("teacher")
        self.assertEqual(get_session_username(valid_token), "teacher")
        self.assertIsNone(get_session_username(valid_token + "tampered"))
        expired_token = create_session_token("teacher", expires_at=int(time.time()) - 1)
        self.assertIsNone(get_session_username(expired_token))

    def test_login_checks_hashed_credentials_and_sets_http_only_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            credentials_path = Path(directory) / "teachers.json"
            credentials_path.write_text(
                json.dumps({"teachers": {"teacher": hash_password("correct", 100_000)}}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"TEACHER_CREDENTIALS_FILE": str(credentials_path)}):
                response = Response()
                result = login_teacher(
                    TeacherLogin(username="teacher", password="correct"), response
                )
                cookie = SimpleCookie()
                cookie.load(response.headers["set-cookie"])
                self.assertEqual(result["username"], "teacher")
                self.assertEqual(get_session_username(cookie[COOKIE_NAME].value), "teacher")
                self.assertIn("httponly", response.headers["set-cookie"].lower())

                with self.assertRaises(HTTPException) as error:
                    login_teacher(
                        TeacherLogin(username="teacher", password="incorrect"), Response()
                    )
                self.assertEqual(error.exception.status_code, 401)

    def test_anonymous_signup_is_rejected_without_mutating_participants(self) -> None:
        with self.assertRaises(HTTPException) as error:
            signup_for_activity("Chess Club", "new-student@mergington.edu", make_request())
        self.assertEqual(error.exception.status_code, 401)
        self.assertEqual(activities["Chess Club"]["participants"], self.original_participants)

    def test_teacher_can_sign_up_and_unregister(self) -> None:
        request = make_request(create_session_token("teacher"))
        signup_for_activity("Chess Club", "new-student@mergington.edu", request)
        self.assertIn("new-student@mergington.edu", activities["Chess Club"]["participants"])
        unregister_from_activity("Chess Club", "new-student@mergington.edu", request)
        self.assertNotIn("new-student@mergington.edu", activities["Chess Club"]["participants"])

    def test_anonymous_unregister_is_rejected(self) -> None:
        existing_participant = self.original_participants[0]
        with self.assertRaises(HTTPException) as error:
            unregister_from_activity("Chess Club", existing_participant, make_request())
        self.assertEqual(error.exception.status_code, 401)
        self.assertIn(existing_participant, activities["Chess Club"]["participants"])


if __name__ == "__main__":
    unittest.main()