import sys
import os
import asyncio
sys.path.append(os.getcwd())
from sqlalchemy import text
from app.db.session import async_session_factory
import random
import string

# 💀 DB OBLITERATOR: DATA CALAMITY

async def chaos_transaction():
    async with async_session_factory() as session:
        txn = await session.begin()
        try:
            # 1. Insert valid data
            await session.execute(text("INSERT INTO employees (name, rfid_uid, department) VALUES ('Chaos', 'CHAOS-001', 'Test')"))
            
            # 2. Inject massive invalid data (simulating SQLi attempt via raw SQL, though we use binding normally)
            # We try to break the syntax or constraints
            invalid_sql = "INSERT INTO employees (name, rfid_uid) VALUES ('Bad', 'CHAOS-001')" # Duplicate UID
            await session.execute(text(invalid_sql))
            
            await txn.commit()
            print("❌ CRITICAL: Transaction committed despite error!")
        except Exception as e:
            await txn.rollback()
            print(f"✅ Transaction cleanly rolled back: {e}")

async def mass_rollback_test():
    print("💀 LAUNCHING 100 CONCURRENT TRANSACTIONS (ALL DESTINED TO FAIL)...")
    tasks = [chaos_transaction() for _ in range(100)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(mass_rollback_test())
