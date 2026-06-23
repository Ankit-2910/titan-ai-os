import asyncio
import asyncpg
import redis.asyncio as aioredis
from qdrant_client import AsyncQdrantClient

async def test_all_memory():

    print("\n=============================")
    print("  TITAN Memory System Test")
    print("=============================\n")

    # ── Test 1: Redis Short-Term Memory ──────────────────
    print("Testing Redis (Short-Term Memory)...")
    try:
        r = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
        await r.set("titan:test:key", "Hello from TITAN!")
        val = await r.get("titan:test:key")
        await r.delete("titan:test:key")
        await r.aclose()
        print(f"  Redis → OK | Value: {val}")
    except Exception as e:
        print(f"  Redis → FAILED: {e}")

    # ── Test 2: PostgreSQL Long-Term Memory ──────────────
    print("\nTesting PostgreSQL (Long-Term Memory)...")
    try:
        conn = await asyncpg.connect(
            "postgresql://postgres:password@localhost:5432/titan_db"
        )
        result = await conn.fetchval("SELECT COUNT(*) FROM users")
        await conn.close()
        print(f"  PostgreSQL → OK | Users in DB: {result}")
    except Exception as e:
        print(f"  PostgreSQL → FAILED: {e}")

    # ── Test 3: Qdrant Semantic Memory ───────────────────
    print("\nTesting Qdrant (Semantic Memory)...")
    try:
        client = AsyncQdrantClient(host="localhost", port=6333)
        collections = await client.get_collections()
        names = [c.name for c in collections.collections]
        await client.close()
        print(f"  Qdrant → OK | Collections: {names if names else 'Empty (normal)'}")
    except Exception as e:
        print(f"  Qdrant → FAILED: {e}")

    print("\n=============================")
    print("  Memory Test Complete!")
    print("=============================\n")

asyncio.run(test_all_memory())