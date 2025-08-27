#!/usr/bin/env python3
"""
Phase 2: 서비스 간 통합 테스트
AI Script Generator v3.0 - 동시 다중 서비스 기동 테스트
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx


class ServiceIntegrationTester:
    """통합 테스트 매니저"""

    def __init__(self):
        self.services = {
            "project-service": {
                "port": 8001,
                "path": "services/project-service",
                "main": "src.project_service.main:app",
                "health": "/api/v1/health",
                "process": None,
            },
            "generation-service": {
                "port": 8002,
                "path": "services/generation-service",
                "main": "src.generation_service.main:app",
                "health": "/api/v1/health",
                "process": None,
            },
        }

        self.base_path = "/Users/al02475493/Documents/ai-script-generator-v3"

    def setup_environment(self):
        """환경 변수 설정"""
        env_vars = {
            # Project Service
            "PROJECT_SERVICE_HOST": "0.0.0.0",
            "PROJECT_SERVICE_PORT": "8001",
            "PROJECT_SERVICE_RELOAD": "false",
            # Generation Service
            "GENERATION_SERVICE_HOST": "0.0.0.0",
            "GENERATION_SERVICE_PORT": "8002",
            "DEBUG": "false",
            "ENVIRONMENT": "development",
            # Database
            "DATABASE_URL": "sqlite:///./data/test_integration.db",
            # AI Providers (using dummy values for test)
            "OPENAI_API_KEY": "example-token",  # pragma: allowlist secret
            "ANTHROPIC_API_KEY": "example-token",  # pragma: allowlist secret
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        print("🔧 환경 변수 설정 완료")

    def start_service(self, service_name: str) -> bool:
        """개별 서비스 시작"""
        service = self.services[service_name]
        service_path = os.path.join(self.base_path, service["path"])

        print(f"🚀 {service_name} 시작 중 (포트: {service['port']})...")

        try:
            # Change to service directory and start with proper PYTHONPATH
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                service["main"],
                "--host",
                "0.0.0.0",
                "--port",
                str(service["port"]),
            ]

            # Set environment for this service
            service_env = os.environ.copy()
            if service_name == "generation-service":
                service_env["PORT"] = str(service["port"])

            service["process"] = subprocess.Popen(
                cmd,
                cwd=service_path,
                env=service_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait a moment for service to start
            time.sleep(3)

            # Check if process is still running
            if service["process"].poll() is None:
                print(f"✅ {service_name} 프로세스 시작됨")
                return True
            else:
                stdout, stderr = service["process"].communicate()
                print(f"❌ {service_name} 시작 실패")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False

        except Exception as e:
            print(f"❌ {service_name} 시작 중 오류: {e}")
            return False

    def stop_service(self, service_name: str):
        """개별 서비스 중지"""
        service = self.services[service_name]
        if service["process"]:
            try:
                service["process"].terminate()
                service["process"].wait(timeout=5)
                print(f"🛑 {service_name} 정상 종료")
            except subprocess.TimeoutExpired:
                service["process"].kill()
                print(f"🔴 {service_name} 강제 종료")
            except Exception as e:
                print(f"⚠️ {service_name} 종료 중 오류: {e}")

    async def check_service_health(self, service_name: str) -> dict:
        """개별 서비스 헬스체크"""
        service = self.services[service_name]
        url = f"http://localhost:{service['port']}{service['health']}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    health_data = response.json()
                    return {
                        "status": "healthy",
                        "service": service_name,
                        "port": service["port"],
                        "response": health_data,
                        "response_time": response.elapsed.total_seconds(),
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service": service_name,
                        "port": service["port"],
                        "error": f"HTTP {response.status_code}",
                        "response_time": response.elapsed.total_seconds(),
                    }

        except Exception as e:
            return {
                "status": "unreachable",
                "service": service_name,
                "port": service["port"],
                "error": str(e),
                "response_time": None,
            }

    async def test_all_health_endpoints(self) -> dict:
        """모든 서비스 헬스체크 동시 실행"""
        print("\n🔍 모든 서비스 헬스체크 실행...")

        tasks = [
            self.check_service_health(service_name)
            for service_name in self.services.keys()
        ]

        results = await asyncio.gather(*tasks)

        health_summary = {
            "timestamp": time.time(),
            "total_services": len(self.services),
            "healthy_services": 0,
            "services": {},
        }

        for result in results:
            service_name = result["service"]
            health_summary["services"][service_name] = result

            if result["status"] == "healthy":
                health_summary["healthy_services"] += 1
                print(
                    f"✅ {service_name}: HEALTHY (응답시간: {result['response_time']:.3f}s)"
                )
            else:
                print(
                    f"❌ {service_name}: {result['status'].upper()} - {result.get('error', 'N/A')}"
                )

        return health_summary

    def start_all_services(self) -> bool:
        """모든 서비스 동시 시작"""
        print("\n🚀 모든 서비스 동시 기동 시작...")

        success_count = 0
        with ThreadPoolExecutor(max_workers=len(self.services)) as executor:
            futures = {
                executor.submit(self.start_service, service_name): service_name
                for service_name in self.services.keys()
            }

            for future in futures:
                service_name = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    print(f"❌ {service_name} 기동 실패: {e}")

        print(f"\n📊 서비스 기동 결과: {success_count}/{len(self.services)} 성공")
        return success_count == len(self.services)

    def stop_all_services(self):
        """모든 서비스 중지"""
        print("\n🛑 모든 서비스 종료 중...")

        for service_name in self.services.keys():
            self.stop_service(service_name)

    async def test_port_conflicts(self) -> dict:
        """포트 충돌 확인"""
        print("\n🔍 포트 충돌 검사...")

        port_check = {}
        for service_name, service in self.services.items():
            port = service["port"]
            try:
                # Try to connect to port
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"http://localhost:{port}/", timeout=2.0
                    )
                    port_check[port] = {
                        "service": service_name,
                        "status": "occupied",
                        "response_code": response.status_code,
                    }
            except httpx.ConnectError:
                port_check[port] = {"service": service_name, "status": "available"}
            except Exception as e:
                port_check[port] = {
                    "service": service_name,
                    "status": "error",
                    "error": str(e),
                }

        return port_check

    async def run_integration_test(self) -> dict:
        """전체 통합 테스트 실행"""
        print("🎯 AI Script Generator v3.0 - Phase 2 통합 테스트 시작")
        print("=" * 60)

        test_results = {
            "phase": "Phase 2",
            "start_time": time.time(),
            "tests": {},
            "summary": {},
        }

        try:
            # 1. 환경 설정
            self.setup_environment()
            test_results["tests"]["environment_setup"] = {"status": "success"}

            # 2. 포트 충돌 검사
            port_conflicts = await self.test_port_conflicts()
            test_results["tests"]["port_conflicts"] = port_conflicts

            # 3. 서비스 동시 기동
            services_started = self.start_all_services()
            test_results["tests"]["service_startup"] = {"success": services_started}

            if services_started:
                # Wait for services to fully initialize
                print("\n⏳ 서비스 초기화 대기 중...")
                await asyncio.sleep(5)

                # 4. 헬스체크 테스트
                health_results = await self.test_all_health_endpoints()
                test_results["tests"]["health_checks"] = health_results

                # 5. 리소스 사용량 체크 (간단한 프로세스 체크)
                resource_check = self.check_resource_usage()
                test_results["tests"]["resource_usage"] = resource_check

        except Exception as e:
            test_results["tests"]["error"] = str(e)
            print(f"❌ 통합 테스트 중 오류: {e}")

        finally:
            # 정리
            self.stop_all_services()
            test_results["end_time"] = time.time()
            test_results["duration"] = (
                test_results["end_time"] - test_results["start_time"]
            )

        return test_results

    def check_resource_usage(self) -> dict:
        """리소스 사용량 간단 체크"""
        resource_info = {}

        for service_name, service in self.services.items():
            if service["process"]:
                try:
                    # Check if process is still running
                    poll_result = service["process"].poll()
                    resource_info[service_name] = {
                        "running": poll_result is None,
                        "pid": service["process"].pid if poll_result is None else None,
                    }
                except Exception as e:
                    resource_info[service_name] = {"error": str(e)}

        return resource_info


async def main():
    """메인 실행 함수"""
    tester = ServiceIntegrationTester()
    results = await tester.run_integration_test()

    # 결과 출력
    print("\n" + "=" * 60)
    print("🎯 Phase 2 통합 테스트 결과 요약")
    print("=" * 60)

    # 요약 생성
    total_tests = len(results["tests"])
    successful_tests = 0

    for test_name, test_result in results["tests"].items():
        if test_name == "health_checks":
            if test_result.get("healthy_services", 0) == test_result.get(
                "total_services", 0
            ):
                successful_tests += 1
                print(f"✅ {test_name}: 모든 서비스 정상")
            else:
                print(
                    f"❌ {test_name}: {test_result.get('healthy_services', 0)}/{test_result.get('total_services', 0)} 서비스만 정상"
                )
        elif test_name == "service_startup":
            if test_result.get("success"):
                successful_tests += 1
                print(f"✅ {test_name}: 성공")
            else:
                print(f"❌ {test_name}: 실패")
        elif test_name == "environment_setup":
            if test_result.get("status") == "success":
                successful_tests += 1
                print(f"✅ {test_name}: 성공")
        else:
            # 기타 테스트들
            print(f"ℹ️  {test_name}: 실행됨")

    print(f"\n📊 전체 결과: {successful_tests}/{total_tests} 테스트 성공")
    print(f"⏱️  실행 시간: {results['duration']:.2f}초")

    # JSON 결과 저장
    with open("integration_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print("📄 상세 결과가 integration_test_results.json에 저장되었습니다.")

    return successful_tests == total_tests


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 테스트가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        sys.exit(1)
