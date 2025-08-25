#!/usr/bin/env python3
"""
Generation Service - Entry Point Wrapper

This is a thin wrapper that delegates to the actual Generation Service
in src/generation_service/main.py for proper module structure.

Use this only for development. In production, use:
uvicorn generation_service.main:app --host 0.0.0.0 --port 8000
"""

import os
import sys
from pathlib import Path

import uvicorn

# Add src to path for proper imports
current_dir = Path(__file__).parent
src_path = current_dir / "src"
sys.path.insert(0, str(src_path))


def main():
    """Main entry point - delegates to actual service"""

    print("🔥 Generation Service - Entry Point Wrapper")
    print("🎯 Delegating to generation_service.main:app")
    print("📝 For production, use: uvicorn generation_service.main:app")

    # Environment configuration
    host = os.getenv("GENERATION_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("GENERATION_SERVICE_PORT", "8000"))
    reload = os.getenv("GENERATION_SERVICE_RELOAD", "true").lower() == "true"

    print(f"🌐 Host: {host}")
    print(f"🚪 Port: {port}")
    print(f"🔄 Reload: {reload}")
    print("=" * 50)

    # Run the actual service
    uvicorn.run(
        "generation_service.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
