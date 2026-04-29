import asyncio
import os
import asyncpg
from dotenv import load_dotenv

async def test_rls():
    load_dotenv(dotenv_path="../.env")
    conn = await asyncpg.connect(os.environ["DIRECT_DATABASE_URL"])
    
    # Use a transaction so we can rollback and not pollute the DB
    tr = conn.transaction()
    await tr.start()
    
    try:
        print("Inserting caregivers and care_recipients...")
        
        # Insert two caregivers (as superuser)
        user_a_id = await conn.fetchval(
            "INSERT INTO caregivers (clerk_user_id, display_name, email) VALUES ('user_a', 'User A', 'a@example.com') RETURNING id"
        )
        user_b_id = await conn.fetchval(
            "INSERT INTO caregivers (clerk_user_id, display_name, email) VALUES ('user_b', 'User B', 'b@example.com') RETURNING id"
        )
        
        # Insert one care recipient for each (as superuser)
        await conn.execute(
            "INSERT INTO care_recipients (caregiver_id, display_name, date_of_birth, sex_at_birth, consent_basis) VALUES ($1, 'A Recipient', '1980-01-01', 'female', 'self')", user_a_id
        )
        await conn.execute(
            "INSERT INTO care_recipients (caregiver_id, display_name, date_of_birth, sex_at_birth, consent_basis) VALUES ($1, 'B Recipient', '1985-01-01', 'male', 'self')", user_b_id
        )
        
        # Switch to the authenticated role so RLS actually applies
        await conn.execute("SET LOCAL ROLE authenticated")
        
        # Test User A
        print("Testing User A context...")
        await conn.execute("SELECT set_config('request.jwt.claims', '{\"sub\": \"user_a\"}', true)")
        results = await conn.fetch("SELECT display_name FROM care_recipients")
        print(f"User A sees: {[r['display_name'] for r in results]}")
        assert len(results) == 1 and results[0]['display_name'] == 'A Recipient'
        
        # Test User B
        print("Testing User B context...")
        await conn.execute("SELECT set_config('request.jwt.claims', '{\"sub\": \"user_b\"}', true)")
        results = await conn.fetch("SELECT display_name FROM care_recipients")
        print(f"User B sees: {[r['display_name'] for r in results]}")
        assert len(results) == 1 and results[0]['display_name'] == 'B Recipient'

        # Test Unauthorized Context
        print("Testing Unauthorized Context...")
        await conn.execute("SELECT set_config('request.jwt.claims', '{\"sub\": \"unknown_user\"}', true)")
        results = await conn.fetch("SELECT display_name FROM care_recipients")
        print(f"No context sees: {[r['display_name'] for r in results]}")
        assert len(results) == 0

        print("RLS is working perfectly! Rolling back transaction.")
    finally:
        await tr.rollback()
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_rls())

