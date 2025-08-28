#!/usr/bin/env python3
"""
RAG Worker Durable/Fallback 테스트 스크립트
USE_DURABLE_WORKER 플래그 ON/OFF 동작 검증
"""

import os
import sys
import asyncio
import requests
from pathlib import Path
from datetime import datetime

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "services/generation-service/src"))

from generation_service.workers.worker_adapter import should_use_durable_worker, get_worker_adapter
from generation_service.models.rag_jobs import RAGIngestRequest

class WorkerFallbackTester:
    """RAG Worker 플래그 전환 테스트"""
    
    def __init__(self):
        self.base_url = "http://localhost:8002"
        self.test_results = {}
        
    def test_flag_detection(self):
        """USE_DURABLE_WORKER 플래그 감지 테스트"""
        print("\n🔍 1. USE_DURABLE_WORKER 플래그 감지 테스트")
        
        # Test with flag OFF
        os.environ["USE_DURABLE_WORKER"] = "false"
        result_off = should_use_durable_worker()
        print(f"  USE_DURABLE_WORKER=false → {result_off}")
        
        # Test with flag ON
        os.environ["USE_DURABLE_WORKER"] = "true"
        result_on = should_use_durable_worker()
        print(f"  USE_DURABLE_WORKER=true → {result_on}")
        
        # Test edge cases
        os.environ["USE_DURABLE_WORKER"] = "TRUE"
        result_upper = should_use_durable_worker()
        print(f"  USE_DURABLE_WORKER=TRUE → {result_upper}")
        
        os.environ.pop("USE_DURABLE_WORKER", None)
        result_unset = should_use_durable_worker()
        print(f"  USE_DURABLE_WORKER=unset → {result_unset}")
        
        # Validate results
        assert result_off == False, "Flag OFF should return False"
        assert result_on == True, "Flag ON should return True"
        assert result_upper == True, "Flag TRUE should return True (case insensitive)"
        assert result_unset == False, "Unset flag should default to False"
        
        print("  ✅ 플래그 감지 테스트 통과")
        self.test_results["flag_detection"] = "PASS"
        
    def test_adapter_selection(self):
        """WorkerAdapter vs BackgroundTasks 선택 테스트"""
        print("\n🔧 2. WorkerAdapter 선택 테스트")
        
        # Test durable worker adapter
        os.environ["USE_DURABLE_WORKER"] = "true"
        adapter_on = get_worker_adapter()
        print(f"  DURABLE_WORKER=ON → {type(adapter_on).__name__}")
        
        # Test fallback (should still return adapter but will fallback in API)
        os.environ["USE_DURABLE_WORKER"] = "false"  
        adapter_off = get_worker_adapter()
        print(f"  DURABLE_WORKER=OFF → {type(adapter_off).__name__}")
        
        # Both should return WorkerAdapter instance
        from generation_service.workers.worker_adapter import WorkerAdapter
        assert isinstance(adapter_on, WorkerAdapter), "Should return WorkerAdapter"
        assert isinstance(adapter_off, WorkerAdapter), "Should return WorkerAdapter"
        
        print("  ✅ WorkerAdapter 선택 테스트 통과")
        self.test_results["adapter_selection"] = "PASS"
        
    async def test_api_fallback(self):
        """API 엔드포인트 fallback 테스트"""
        print("\n🌐 3. API 엔드포인트 fallback 테스트")
        
        # Test request payload
        test_request = {
            "project_id": "test-project",
            "file_id": "test-file-123",
            "chunk_size": 1024,
            "chunk_overlap": 128
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Ingest-Id": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        # Test with durable worker ON
        print("  Testing with USE_DURABLE_WORKER=true...")
        os.environ["USE_DURABLE_WORKER"] = "true"
        
        try:
            response_on = requests.post(
                f"{self.base_url}/api/generation/rag/ingest",
                json=test_request,
                headers=headers,
                timeout=10
            )
            
            if response_on.status_code == 200:
                data = response_on.json()
                print(f"    ✅ Durable worker response: {data.get('job_id', 'N/A')}")
                self.test_results["api_durable"] = "PASS"
            else:
                print(f"    ❌ Durable worker failed: {response_on.status_code}")
                print(f"       Response: {response_on.text}")
                self.test_results["api_durable"] = "FAIL"
                
        except Exception as e:
            print(f"    ❌ Durable worker error: {e}")
            self.test_results["api_durable"] = "ERROR"
        
        # Test with durable worker OFF (fallback to BackgroundTasks)
        print("  Testing with USE_DURABLE_WORKER=false...")
        os.environ["USE_DURABLE_WORKER"] = "false"
        
        # Update ingest ID to avoid idempotency conflicts
        headers["X-Ingest-Id"] = f"test-fallback-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        try:
            response_off = requests.post(
                f"{self.base_url}/api/generation/rag/ingest",
                json=test_request,
                headers=headers,
                timeout=10
            )
            
            if response_off.status_code == 200:
                data = response_off.json()
                print(f"    ✅ Fallback response: {data.get('job_id', 'N/A')}")
                self.test_results["api_fallback"] = "PASS"
            else:
                print(f"    ❌ Fallback failed: {response_off.status_code}")
                print(f"       Response: {response_off.text}")
                self.test_results["api_fallback"] = "FAIL"
                
        except Exception as e:
            print(f"    ❌ Fallback error: {e}")
            self.test_results["api_fallback"] = "ERROR"
            
    def test_environment_isolation(self):
        """환경 변수 격리 테스트"""
        print("\n🔒 4. 환경 변수 격리 테스트")
        
        # Store original state
        original_value = os.environ.get("USE_DURABLE_WORKER")
        
        try:
            # Test multiple rapid changes
            for i in range(5):
                os.environ["USE_DURABLE_WORKER"] = "true" if i % 2 == 0 else "false"
                result = should_use_durable_worker()
                expected = i % 2 == 0
                assert result == expected, f"Iteration {i}: expected {expected}, got {result}"
            
            print("  ✅ 환경 변수 격리 테스트 통과")
            self.test_results["env_isolation"] = "PASS"
            
        finally:
            # Restore original state
            if original_value is not None:
                os.environ["USE_DURABLE_WORKER"] = original_value
            else:
                os.environ.pop("USE_DURABLE_WORKER", None)
                
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 RAG Worker Durable/Fallback 테스트 시작")
        print("=" * 60)
        
        try:
            # Run synchronous tests
            self.test_flag_detection()
            self.test_adapter_selection() 
            self.test_environment_isolation()
            
            # Run async tests
            asyncio.run(self.test_api_fallback())
            
        except Exception as e:
            print(f"\n❌ 테스트 실행 중 오류: {e}")
            self.test_results["overall"] = "ERROR"
            return False
            
        # Print summary
        self.print_summary()
        return all(result in ["PASS", "SKIP"] for result in self.test_results.values())
        
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == "PASS" else "❌" if result == "FAIL" else "⚠️"
            print(f"{status_icon} {test_name}: {result}")
            
        passed = sum(1 for r in self.test_results.values() if r == "PASS")
        total = len(self.test_results)
        
        print(f"\n총 {passed}/{total} 테스트 통과")
        
        if passed == total:
            print("🎉 모든 테스트 통과! USE_DURABLE_WORKER 플래그가 정상 동작합니다.")
        else:
            print("⚠️  일부 테스트 실패. 설정을 확인해주세요.")

if __name__ == "__main__":
    tester = WorkerFallbackTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)