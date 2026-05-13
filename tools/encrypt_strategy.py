"""Encrypt the local strategy payload (rules + signal) for the public website.

Output: docs/data/strategy_payload.enc -- AES-256-GCM ciphertext, key derived
from STRATEGY_PASSWORD via PBKDF2-HMAC-SHA-256 (200k iterations).

This script is the only piece of the strategy that lives in the public repo.
It does not contain the password or any rule text; the secrets live in .env
and untracked files (docs/data/strategy_rules.txt, docs/data/strategy_signal.json).

Usage:
  python tools/encrypt_strategy.py            # uses STRATEGY_PASSWORD env var or .env
  python tools/encrypt_strategy.py --password Shi...
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "docs" / "data"
RULES_PATH = DATA_DIR / "strategy_rules.txt"
SIGNAL_PATH = DATA_DIR / "strategy_signal.json"
PAYLOAD_PATH = DATA_DIR / "strategy_payload.enc"

KDF_ITER = 200_000
SALT_LEN = 16
NONCE_LEN = 12


def _load_dotenv_password() -> str | None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("STRATEGY_PASSWORD="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _read_payload() -> dict:
    rules = RULES_PATH.read_text(encoding="utf-8") if RULES_PATH.exists() else ""
    signal: dict | None = None
    if SIGNAL_PATH.exists():
        try:
            signal = json.loads(SIGNAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            signal = None
    return {"rules": rules, "signal": signal}


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=KDF_ITER)
    return kdf.derive(password.encode("utf-8"))


def encrypt(password: str) -> Path:
    plaintext = json.dumps(_read_payload(), ensure_ascii=False).encode("utf-8")
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = derive_key(password, salt)
    ct = AESGCM(key).encrypt(nonce, plaintext, None)
    out = {
        "kdf": "PBKDF2-HMAC-SHA256",
        "iter": KDF_ITER,
        "cipher": "AES-256-GCM",
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PAYLOAD_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return PAYLOAD_PATH


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=None)
    args = parser.parse_args()
    pw = args.password or os.environ.get("STRATEGY_PASSWORD") or _load_dotenv_password()
    if not pw:
        print("[error] STRATEGY_PASSWORD not provided. Set it in .env or --password.")
        return 1
    path = encrypt(pw)
    print(f"[ok] encrypted payload -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
