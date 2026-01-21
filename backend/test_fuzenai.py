"""
Test script to generate smart questions for fuzenai and view research.
Run this after logging into the frontend to get your auth token.
"""
import asyncio
import httpx
import json

# Production API URL
API_URL = "http://answer-engine-alb-157996493.us-east-1.elb.amazonaws.com"

async def test_fuzenai():
    # First, you need to get your auth token from the browser
    # 1. Login to the frontend
    # 2. Open browser DevTools (F12) -> Application -> Local Storage
    # 3. Copy the 'token' value

    TOKEN = input("Enter your auth token from browser: ").strip()

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=300) as client:
        # 1. List brands to find fuzenai
        print("\n1. Finding fuzenai brand...")
        resp = await client.get(f"{API_URL}/api/brands", headers=headers)

        if resp.status_code != 200:
            print(f"Error listing brands: {resp.text}")
            return

        brands = resp.json()
        fuzenai = None

        for brand in brands.get("items", brands if isinstance(brands, list) else []):
            if "fuzen" in brand.get("name", "").lower():
                fuzenai = brand
                break

        if not fuzenai:
            print("fuzenai brand not found. Creating it...")
            resp = await client.post(
                f"{API_URL}/api/brands",
                headers=headers,
                json={
                    "name": "Fuzen AI",
                    "domain": "fuzen.ai",
                    "industry": "AI/ML Platform"
                }
            )
            if resp.status_code == 201:
                fuzenai = resp.json()
                print(f"Created brand: {fuzenai}")
            else:
                print(f"Error creating brand: {resp.text}")
                return

        brand_id = fuzenai["id"]
        print(f"Found brand: {fuzenai['name']} (ID: {brand_id})")

        # 2. Generate smart questions
        print("\n2. Generating smart questions with Perplexity research...")
        print("   This may take 1-2 minutes...")

        resp = await client.post(
            f"{API_URL}/api/questions/brand/{brand_id}/generate-smart",
            headers=headers,
            json={"num_questions": 20}
        )

        if resp.status_code != 201:
            print(f"Error generating questions: {resp.text}")
            return

        result = resp.json()

        print(f"\n✅ Generated {result['questions_generated']} questions!")
        print("\n=== RESEARCH SUMMARY ===")
        research = result.get("research_summary", {})
        print(json.dumps(research, indent=2))

        print("\n=== SAMPLE QUESTIONS ===")
        for i, q in enumerate(result.get("questions", [])[:10], 1):
            print(f"{i}. [{q.get('category', 'N/A')}] {q.get('question_text', q.get('text', 'N/A'))}")

        # 3. Get full research from database
        print("\n3. Fetching full research from database...")
        resp = await client.get(
            f"{API_URL}/api/questions/brand/{brand_id}/research",
            headers=headers
        )

        if resp.status_code == 200:
            full_research = resp.json()
            print("\n=== FULL STORED RESEARCH ===")
            print(json.dumps(full_research, indent=2))
        else:
            print(f"Error fetching research: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_fuzenai())
