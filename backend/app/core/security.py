import functools
from typing import Annotated

import httpx
import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

security_scheme = HTTPBearer()


@functools.lru_cache(maxsize=1)
def fetch_clerk_jwks(issuer_url: str) -> dict:
    """Fetch and cache the Clerk JWKS."""
    if not issuer_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWT issuer is not configured.",
        )
    jwks_url = f"{issuer_url.rstrip('/')}/.well-known/jwks.json"
    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch JWKS from identity provider.",
        ) from e


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return its decoded claims."""
    settings = get_settings()
    issuer_url = settings.clerk_jwt_issuer

    if not issuer_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWT issuer is not configured.",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.DecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header.",
        ) from e

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'kid' in header.",
        )

    jwks = fetch_clerk_jwks(issuer_url)

    # Find the matching key
    rsa_key = {}
    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break

    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key to verify token.",
        )

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(rsa_key)

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=issuer_url,
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        ) from e
    except jwt.InvalidIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token issuer is invalid.",
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        ) from e


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(security_scheme)],
) -> str:
    """FastAPI dependency to extract and verify the Clerk user ID."""
    token = credentials.credentials
    claims = verify_clerk_token(token)
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing 'sub' claim.",
        )
    return sub
