import asyncio
import httpx
import random
import string
import time
import sys

# 💀 API ANNIHILATOR: THE END OF DAYS

BASE_URL = "http://127.0.0.1:8000/api/v1"

def generate_garbage(length=1000):
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=length))

def generate_massive_payload():
    return {"data": "A" * 100000}  # 100KB payload

async def attack_endpoint(client, endpoint, method="GET", payload=None):
    try:
        url = f"{BASE_URL}{endpoint}"
        start = time.time()
        if method == "POST":
            resp = await client.post(url, json=payload, timeout=5.0)
        else:
            resp = await client.get(url, timeout=5.0)
        duration = time.time() - start
        return resp.status_code, duration
    except Exception as e:
        print(f"Request Error to {endpoint}: {e}")
        return "ERROR", 0

async def run_annihilation(concurrency=100, iterations=10):
    print(f"💀 LAUNCHING ANNIHILATION: {concurrency} threads, {iterations} waves")
    async with httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)) as client:
        for flame in range(iterations):
            tasks = []
            print(f"🔥 WAVE {flame+1}/{iterations} INCOMING...")
            
            # Mix of attacks
            for _ in range(concurrency):
                # 1. Scan Attack (POST /scan)
                tasks.append(attack_endpoint(client, "/scan", "POST", {"uid": generate_garbage(50)}))
                
                # 2. Login Attack (POST /auth/login) - URL Encoded manually handled by httpx if data passed, but we use json here which fails validation -> good test
                # Actually login expects form data, let's send garbage JSON to trigger validation parsers
                tasks.append(attack_endpoint(client, "/auth/login", "POST", {"username": "admin", "password": generate_garbage(100)}))
                
                # 3. Health Check DoS (GET /health)
                tasks.append(attack_endpoint(client, "/health", "GET"))
            
            results = await asyncio.gather(*tasks)
            
            # Analyze Wave
            codes = {}
            for code, _ in results:
                codes[code] = codes.get(code, 0) + 1
            
            print(f"   Results: {codes}")
            
            # Check for total collapse
            if codes.get(500, 0) > 0:
                print("🚨 CRITICAL: 500 ERROR DETECTED! SYSTEM BREECHED!")
            if codes.get("ERROR", 0) > 10:
                print("⚠️  WARNING: High connection failure rate (DoS successful?)")

if __name__ == "__main__":
    try:
        # Increase limit for Windows if needed
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_annihilation(concurrency=50, iterations=5))
    except KeyboardInterrupt:
        print("Annihilation aborted.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FATAL ERROR: {e}")
