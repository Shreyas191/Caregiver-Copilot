import asyncio
import os
import sys

import asyncpg
from dotenv import load_dotenv

async def apply_migrations():
    load_dotenv(dotenv_path="../.env")
    database_url = os.environ.get("DIRECT_DATABASE_URL")
    if not database_url:
        print("Error: DIRECT_DATABASE_URL is not set in .env")
        sys.exit(1)

    print("Connecting to database...")
    conn = await asyncpg.connect(database_url)
    print("Connected.")

    migrations_dir = "migrations"
    files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])

    for file in files:
        filepath = os.path.join(migrations_dir, file)
        print(f"Applying {file}...")
        with open(filepath, "r") as f:
            sql = f.read()
        try:
            await conn.execute(sql)
            print(f"Successfully applied {file}.")
        except asyncpg.exceptions.PostgresError as e:
            # If the error is 'type ... already exists', we can ignore it for enums
            # or 'table ... already exists'
            print(f"Warning/Error applying {file}: {e}")
            # we continue to try next files (or should we raise? The enums might exist)

    await conn.close()
    print("All done.")

if __name__ == "__main__":
    asyncio.run(apply_migrations())
