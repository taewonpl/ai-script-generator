#!/usr/bin/env python3
"""
Integration test for SSE-based Generation Service
"""

import asyncio
import json
import logging
import sys

import httpx
import sseclient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"


async def test_sse_generation_flow():
    """Test the complete SSE generation flow"""

    print("🔄 Testing SSE Generation Service Integration...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Start generation job
        print("\n🔄 Test 1: Start generation job...")
        try:
            generation_request = {
                "projectId": "test-project-sse",
                "episodeNumber": 1,
                "title": "SSE Test Episode",
                "description": "A test script for validating SSE implementation with multiple event types",
                "scriptType": "drama",
                "model": "gpt-4",
                "temperature": 0.7,
                "lengthTarget": 1000,
            }

            response = await client.post(
                f"{BASE_URL}/generations", json=generation_request
            )

            if response.status_code == 201:
                data = response.json()
                job_id = data["jobId"]
                sse_url = data["sseUrl"]
                cancel_url = data["cancelUrl"]

                print(f"✅ Generation started: {job_id}")
                print(f"   SSE URL: {sse_url}")
                print(f"   Cancel URL: {cancel_url}")

                return job_id, sse_url, cancel_url
            else:
                print(
                    f"❌ Failed to start generation: {response.status_code} - {response.text}"
                )
                return None, None, None

        except Exception as e:
            print(f"❌ Error starting generation: {e}")
            return None, None, None


def test_sse_events(sse_url: str, job_id: str):
    """Test SSE event stream"""
    print(f"\n🔄 Test 2: SSE Event Stream for job {job_id}...")

    event_counts = {
        "progress": 0,
        "preview": 0,
        "completed": 0,
        "failed": 0,
        "heartbeat": 0,
    }

    try:
        import requests

        # Connect to SSE stream
        response = requests.get(sse_url, stream=True, timeout=60)

        if response.status_code != 200:
            print(f"❌ Failed to connect to SSE: {response.status_code}")
            return False

        print("✅ Connected to SSE stream")

        client = sseclient.SSEClient(response)

        for event in client.events():
            if event.event and event.data:
                event_type = event.event
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

                try:
                    data = json.loads(event.data)
                    print(
                        f"📡 {event_type.upper()}: {format_event_data(event_type, data)}"
                    )

                    # Check if generation is complete
                    if event_type in ["completed", "failed"]:
                        print(f"🏁 Generation finished with event: {event_type}")
                        break

                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON in {event_type} event: {event.data}")

        # Print event summary
        print("\n📊 Event Summary:")
        for event_type, count in event_counts.items():
            if count > 0:
                print(f"   {event_type}: {count} events")

        # Validate we received the expected events
        if event_counts["progress"] > 0 and event_counts["completed"] > 0:
            print("✅ SSE test completed successfully")
            return True
        else:
            print("❌ Missing expected events")
            return False

    except Exception as e:
        print(f"❌ SSE test failed: {e}")
        return False


def format_event_data(event_type: str, data: dict) -> str:
    """Format event data for display"""
    if event_type == "progress":
        return f"{data.get('value', 0)}% - {data.get('currentStep', 'Unknown')}"
    elif event_type == "preview":
        content = data.get("markdown", "")
        word_count = data.get("wordCount", 0)
        return f"Content length: {len(content)} chars, Words: {word_count}"
    elif event_type == "completed":
        result = data.get("result", {})
        tokens = result.get("tokens", 0)
        return f"Final script: {tokens} tokens"
    elif event_type == "failed":
        error = data.get("error", {})
        return f"Error: {error.get('code', 'Unknown')} - {error.get('message', '')}"
    elif event_type == "heartbeat":
        return f"Timestamp: {data.get('timestamp', '')}"
    else:
        return str(data)


async def test_job_management(job_id: str):
    """Test job management endpoints"""
    print(f"\n🔄 Test 3: Job Management for {job_id}...")

    async with httpx.AsyncClient() as client:
        # Test job status
        try:
            response = await client.get(f"{BASE_URL}/generations/{job_id}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Job status: {data['status']} ({data['progress']}%)")
                print(f"   Current step: {data['currentStep']}")
                print(f"   Episode ID: {data.get('episodeId', 'Not created yet')}")
            else:
                print(f"❌ Failed to get job status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting job status: {e}")

        # Test active jobs list
        try:
            response = await client.get(f"{BASE_URL}/generations/active")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Active jobs: {data['total_active']}")
            else:
                print(f"❌ Failed to get active jobs: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting active jobs: {e}")

        # Test service stats
        try:
            response = await client.get(f"{BASE_URL}/generations/_stats")
            if response.status_code == 200:
                data = response.json()
                stats = data.get("job_statistics", {})
                print(f"✅ Service stats: {stats}")
            else:
                print(f"❌ Failed to get stats: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting stats: {e}")


async def test_cancellation():
    """Test job cancellation"""
    print("\n🔄 Test 4: Job Cancellation...")

    async with httpx.AsyncClient() as client:
        # Start a new job for cancellation test
        generation_request = {
            "projectId": "test-project-cancel",
            "title": "Cancellation Test",
            "description": "This job will be canceled for testing",
            "scriptType": "drama",
        }

        response = await client.post(f"{BASE_URL}/generations", json=generation_request)

        if response.status_code != 201:
            print("❌ Failed to start job for cancellation test")
            return

        data = response.json()
        cancel_job_id = data["jobId"]

        print(f"✅ Started job for cancellation: {cancel_job_id}")

        # Wait a moment then cancel
        await asyncio.sleep(1)

        cancel_response = await client.delete(f"{BASE_URL}/generations/{cancel_job_id}")

        if cancel_response.status_code == 204:
            print("✅ Job canceled successfully")

            # Test idempotent cancellation
            cancel_response2 = await client.delete(
                f"{BASE_URL}/generations/{cancel_job_id}"
            )
            if cancel_response2.status_code == 204:
                print("✅ Idempotent cancellation works")
            else:
                print(
                    f"❌ Idempotent cancellation failed: {cancel_response2.status_code}"
                )

        else:
            print(f"❌ Cancellation failed: {cancel_response.status_code}")


async def run_full_test():
    """Run the complete test suite"""
    print("🚀 Starting SSE Generation Service Tests")
    print("⚠️  Make sure the generation service is running on localhost:8000")
    print()

    # Test 1: Start generation and get SSE details
    job_id, sse_url, cancel_url = await test_sse_generation_flow()

    if not job_id:
        print("❌ Cannot continue tests without a valid job")
        return

    # Test 2: Monitor SSE events (this will run until completion)
    success = test_sse_events(sse_url, job_id)

    if not success:
        print("❌ SSE test failed, skipping remaining tests")
        return

    # Test 3: Job management endpoints
    await test_job_management(job_id)

    # Test 4: Cancellation functionality
    await test_cancellation()

    print("\n🎉 All tests completed!")
    print("\nExpected SSE Events Format:")
    print(
        """
    event: progress
    data: {"type":"progress","jobId":"job_xxx","value":25,"currentStep":"프롬프트 분석 중","estimatedTime":120}

    event: preview
    data: {"type":"preview","jobId":"job_xxx","markdown":"# My Drama - Ep. 1\\n\\nFADE IN:","isPartial":true}

    event: completed
    data: {"type":"completed","jobId":"job_xxx","result":{"markdown":"완성된 대본...","tokens":1250}}

    event: failed
    data: {"type":"failed","jobId":"job_xxx","error":{"code":"TOKEN_LIMIT_EXCEEDED","message":"토큰 한도 초과"}}

    event: heartbeat
    data: {"type":"heartbeat","timestamp":"2025-08-22T10:30:25Z"}
    """
    )


if __name__ == "__main__":
    # Check if sseclient is available
    try:
        import sseclient
    except ImportError:
        print("❌ Missing required dependency: sseclient-py")
        print("Install with: pip install sseclient-py")
        sys.exit(1)

    try:
        import requests
    except ImportError:
        print("❌ Missing required dependency: requests")
        print("Install with: pip install requests")
        sys.exit(1)

    asyncio.run(run_full_test())
