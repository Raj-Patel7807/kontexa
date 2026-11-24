"""Unit tests for cryptographic security utilities: PBKDF2 hashing, session tokens, and CSRF."""

from kontexa.core.security import (
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_csrf_token,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    """Verify passwords hash uniquely with random salt and verify accurately."""
    password = "SuperSecretPassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Different salts must yield different hashes
    assert hash1 != hash2
    assert hash1.startswith("pbkdf2:sha256:100000:")

    # Accurate verification
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True
    assert verify_password("WrongPassword!", hash1) is False


def test_password_verification_fails_gracefully_on_malformed_hash() -> None:
    """Verify corrupted hashes reject gracefully without crashing."""
    assert verify_password("pass", "malformed_hash_without_colons") is False
    assert verify_password("pass", "pbkdf2:invalid:parts") is False
    assert verify_password("pass", "") is False


def test_session_token_generation_and_hashing() -> None:
    """Verify session tokens are random and SHA-256 hashes are deterministic."""
    token1 = generate_session_token()
    token2 = generate_session_token()

    assert token1 != token2
    assert len(token1) >= 32

    hash1 = hash_session_token(token1)
    hash1_repeat = hash_session_token(token1)
    assert hash1 == hash1_repeat
    assert len(hash1) == 64  # SHA-256 hex string


def test_csrf_token_signing_and_verification() -> None:
    """Verify CSRF tokens are signed with HMAC and tied to a specific session."""
    session_id = "sess-uuid-1234"
    secret = "test-secret-key-for-hmac"

    csrf_token = generate_csrf_token(session_id, secret)
    assert "." in csrf_token

    # Valid token verification
    assert verify_csrf_token(session_id, csrf_token, secret) is True

    # Reject if bound to different session ID
    assert verify_csrf_token("different-session-id", csrf_token, secret) is False

    # Reject if secret key does not match
    assert verify_csrf_token(session_id, csrf_token, "wrong-secret-key") is False

    # Reject tampered token
    tampered = csrf_token[:-4] + "abcd"
    assert verify_csrf_token(session_id, tampered, secret) is False
    assert verify_csrf_token(session_id, "invalid_format", secret) is False
