"""Cryptographic utilities for password hashing and secure token generation."""

import hashlib
import hmac
import os
import secrets

# Argon2 / PBKDF2 standard parameters
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2:{PBKDF2_ALGORITHM}:{PBKDF2_ITERATIONS}:{salt.hex()}:{dk.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify plaintext password matches stored PBKDF2 hash using constant-time comparison."""
    try:
        parts = hashed_password.split(":")
        if len(parts) != 5 or parts[0] != "pbkdf2":
            return False
        algorithm = parts[1]
        iterations = int(parts[2])
        salt = bytes.fromhex(parts[3])
        expected_dk = bytes.fromhex(parts[4])

        computed_dk = hashlib.pbkdf2_hmac(
            algorithm,
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed_dk, expected_dk)
    except Exception:
        return False


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe random session token for browser cookie issuance."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Hash a session token with SHA-256 for secure database lookup and storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token(session_id: str, secret_key: str) -> str:
    """Generate a cryptographically signed double-submit CSRF token tied to the session ID."""
    nonce = secrets.token_hex(16)
    signature = hmac.new(
        secret_key.encode("utf-8"),
        f"{session_id}:{nonce}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{signature}"


def verify_csrf_token(session_id: str, csrf_token: str, secret_key: str) -> bool:
    """Validate that the submitted CSRF token carries a valid signature for the active session."""
    try:
        parts = csrf_token.split(".")
        if len(parts) != 2:
            return False
        nonce, signature = parts[0], parts[1]
        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            f"{session_id}:{nonce}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False
