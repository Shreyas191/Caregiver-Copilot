import json
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import verify_clerk_token

settings = get_settings()

if not settings.database_url:
    raise ValueError("DATABASE_URL is not set in the environment.")

# Create the async engine with pgBouncer support
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

# Create the async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async SQLAlchemy session.
    
    Automatically extracts the Clerk JWT from the Authorization header (if present)
    and sets the Row-Level Security (RLS) context for the database transaction.
    """
    async with async_session_maker() as session:
        # Extract JWT from headers
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # To avoid verifying the token twice per request, we cache it on the request state.
                if not hasattr(request.state, "clerk_claims"):
                    claims = verify_clerk_token(token)
                    request.state.clerk_claims = claims
                else:
                    claims = request.state.clerk_claims
                
                sub = claims.get("sub")
                if sub:
                    # Set RLS context for this transaction
                    claims_json = json.dumps({"sub": sub})
                    await session.execute(
                        text("SELECT set_config('request.jwt.claims', :claims, true)"),
                        {"claims": claims_json}
                    )
            except Exception:
                # If token is invalid or expired, we don't set the RLS context.
                # The security dependency will catch and raise the 401 later.
                pass
        
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
