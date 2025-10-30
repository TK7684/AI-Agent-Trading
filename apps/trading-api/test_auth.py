#!/usr/bin/env python3
"""
Test authentication functionality
"""

from datetime import UTC, datetime, timedelta

import jwt

SECRET = "dev-secret-key-for-trading-dashboard-2024"
ALGO = "HS256"
ACCESS_EXPIRE_MIN = 60

def create_token(sub: str, minutes: int = ACCESS_EXPIRE_MIN) -> str:
    now = datetime.now(UTC)
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=minutes)).timestamp())}
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None
    except Exception as e:
        print(f"Token validation error: {str(e)}")
        return None

if __name__ == "__main__":
    print("Testing JWT authentication...")

    # Create a token
    email = "test@example.com"
    token = create_token(email)
    print(f"Created token: {token}")

    # Verify the token
    payload = verify_token(token)
    print(f"Verified payload: {payload}")

    if payload and payload.get("sub") == email:
        print("✅ Authentication test passed!")
    else:
        print("❌ Authentication test failed!")
