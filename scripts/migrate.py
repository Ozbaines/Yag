"""Run DB migrations (create all tables)."""
import asyncio
from shared.db import init_db

if __name__ == "__main__":
    asyncio.run(init_db())
    print("✅ Tables created.")
