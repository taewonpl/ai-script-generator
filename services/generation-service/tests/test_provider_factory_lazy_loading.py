#!/usr/bin/env python3
"""
Unit tests for Provider Factory lazy loading implementation
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.generation_service.ai.providers.base_provider import ProviderStatus

# Import the classes to test
from src.generation_service.ai.providers.provider_factory import (
    ProviderFactory,
    ProviderType,
)


class TestProviderFactoryLazyLoading:
    """Test Provider Factory lazy loading functionality"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            "ai_providers": {
                "openai": {
                    "type": "openai",
                    "api_key": "test-key",
                    "model": "gpt-4",
                },  # pragma: allowlist secret
                "anthropic": {
                    "type": "anthropic",
                    "api_key": "test-key",  # pragma: allowlist secret
                    "model": "claude-3-5-sonnet-20241022",
                },
                "local": {"type": "local", "model_name": "llama-3.1-8b"},
            },
            "default_model": "gpt-4",
        }

    @pytest.fixture
    def factory(self, mock_config):
        """Create a factory instance for testing"""
        return ProviderFactory(mock_config)

    def test_factory_initialization(self, factory):
        """Test that factory initializes without importing providers"""
        assert factory is not None
        assert len(factory._import_failures) == 0
        assert len(factory._providers) == 0
        assert "ai_providers" in factory.config

    def test_provider_type_enum(self):
        """Test ProviderType enum values"""
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.ANTHROPIC == "anthropic"
        assert ProviderType.LOCAL == "local"

    @patch("src.generation_service.ai.providers.provider_factory.logger")
    def test_lazy_import_tracking(self, mock_logger, factory):
        """Test that import failures are properly tracked"""

        # Test with mock import failure
        with patch("builtins.__import__", side_effect=ImportError("Module not found")):
            available = factory.is_provider_available(ProviderType.OPENAI)

            assert not available
            assert ProviderType.OPENAI in factory._import_failures
            assert "Import test failed" in factory._import_failures[ProviderType.OPENAI]

    def test_get_available_provider_types(self, factory):
        """Test getting available provider types"""

        # Mock different availability scenarios
        with patch.object(factory, "is_provider_available") as mock_available:
            mock_available.side_effect = lambda pt: pt == ProviderType.LOCAL

            available_types = factory.get_available_provider_types()
            assert ProviderType.LOCAL in available_types
            assert len(available_types) == 1

    def test_get_import_failures(self, factory):
        """Test getting import failure details"""

        # Simulate some failures
        factory._import_failures[ProviderType.OPENAI] = "OpenAI not installed"
        factory._import_failures[ProviderType.ANTHROPIC] = "Anthropic not available"

        failures = factory.get_import_failures()
        assert failures[ProviderType.OPENAI] == "OpenAI not installed"
        assert failures[ProviderType.ANTHROPIC] == "Anthropic not available"
        assert ProviderType.LOCAL not in failures

    def test_provider_statistics(self, factory):
        """Test provider statistics with lazy loading info"""

        with patch.object(factory, "get_available_provider_types") as mock_available:
            mock_available.return_value = [ProviderType.LOCAL]

            stats = factory.get_provider_statistics()

            assert "lazy_loading" in stats
            assert stats["lazy_loading"] is True
            assert "available_provider_types" in stats
            assert "unavailable_provider_types" in stats
            assert stats["available_provider_types"] == ["local"]

    @patch("src.generation_service.ai.providers.provider_factory.logger")
    def test_create_provider_with_import_error(self, mock_logger, factory):
        """Test create_provider handles ImportError correctly"""

        # Mock ImportError for OpenAI by patching the specific import
        with patch(
            "builtins.__import__",
            side_effect=lambda name, *args: (
                ImportError("No module named 'openai'")
                if "openai_provider" in name
                else __import__(name, *args)
            ),
        ):
            with pytest.raises(ImportError) as exc_info:
                factory.create_provider(
                    ProviderType.OPENAI,
                    {"type": "openai", "api_key": "test"},  # pragma: allowlist secret
                )

            assert "OpenAI provider unavailable" in str(exc_info.value)
            assert "pip install openai" in str(exc_info.value)
            assert ProviderType.OPENAI in factory._import_failures

    def test_provider_failure_summary(self, factory):
        """Test comprehensive failure summary generation"""

        # Setup some mock failures
        factory._import_failures[ProviderType.OPENAI] = "openai module not found"

        with patch.object(factory, "get_available_provider_types") as mock_available:
            mock_available.return_value = [ProviderType.LOCAL]

            summary = factory.get_provider_failure_summary()

            assert "import_failures" in summary
            assert "available_types" in summary
            assert "configured_providers" in summary
            assert "recommendations" in summary

            # Check recommendations
            assert any("Install OpenAI" in rec for rec in summary["recommendations"])

    @pytest.mark.asyncio
    async def test_fallback_provider_selection(self, factory):
        """Test enhanced fallback provider selection"""

        # Mock provider creation and health check
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=ProviderStatus.HEALTHY)

        with (
            patch.object(factory, "get_available_provider_types") as mock_available,
            patch.object(factory, "create_provider") as mock_create,
        ):
            mock_available.return_value = [ProviderType.LOCAL]
            mock_create.return_value = mock_provider

            result = await factory._fallback_provider_selection()

            assert result == mock_provider
            # Don't check exact call count since fallback may try multiple strategies

    @pytest.mark.asyncio
    async def test_fallback_provider_all_fail(self, factory):
        """Test fallback when all strategies fail"""

        with (
            patch.object(factory, "get_available_provider_types") as mock_available,
            patch.object(factory, "get_default_model") as mock_default,
        ):
            mock_available.return_value = []
            mock_default.return_value = None

            result = await factory._fallback_provider_selection()
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_configuration(self, factory):
        """Test configuration validation"""

        # Mock provider availability and health
        with (
            patch.object(factory, "is_provider_available") as mock_available,
            patch.object(factory, "create_provider") as mock_create,
        ):
            mock_available.return_value = True
            mock_provider = Mock()
            mock_provider.health_check = Mock(return_value=ProviderStatus.HEALTHY)
            mock_create.return_value = mock_provider

            result = await factory.validate_configuration()

            assert "is_valid" in result
            assert "providers" in result
            assert "issues" in result
            assert "warnings" in result

    @pytest.mark.asyncio
    async def test_validate_configuration_no_config(self):
        """Test validation with empty configuration"""

        empty_factory = ProviderFactory({})
        result = await empty_factory.validate_configuration()

        assert not result["is_valid"]
        assert "No provider configurations found" in result["issues"]

    @pytest.mark.asyncio
    async def test_enhanced_load_balancer(self, factory):
        """Test enhanced load balancer with error handling"""

        # Mock provider that works
        mock_provider = Mock()
        mock_provider.health_check = AsyncMock(return_value=ProviderStatus.HEALTHY)

        with (
            patch.object(factory, "get_provider") as mock_get,
            patch.object(
                factory, "_fallback_provider_selection", return_value=None
            ) as mock_fallback,
        ):
            # First model fails, second succeeds
            mock_get.side_effect = [None, mock_provider]

            result = await factory.load_balancer_provider(["model1", "model2"])

            assert result == mock_provider
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_load_balancer_empty_models(self, factory):
        """Test load balancer with empty models list"""

        result = await factory.load_balancer_provider([])
        assert result is None

    @pytest.mark.asyncio
    async def test_get_best_provider_with_availability_check(self, factory):
        """Test get_best_provider with availability pre-check"""

        mock_provider = Mock()
        mock_provider.health_check = Mock(return_value=ProviderStatus.HEALTHY)

        with (
            patch.object(factory, "is_provider_available") as mock_available,
            patch.object(factory, "create_provider") as mock_create,
        ):
            # Only local provider available
            mock_available.side_effect = lambda pt: pt == ProviderType.LOCAL
            mock_create.return_value = mock_provider

            result = await factory.get_best_provider_for_task("general")

            # Should skip unavailable providers and use local
            assert result == mock_provider
            # Should have checked availability before creating
            assert mock_available.call_count >= 1

    def test_import_failure_error_messages(self, factory):
        """Test specific error messages for different providers"""

        test_cases = [
            (ProviderType.OPENAI, "pip install openai"),
            (ProviderType.ANTHROPIC, "pip install anthropic"),
            (ProviderType.LOCAL, "Check local model dependencies"),
        ]

        for provider_type, expected_msg in test_cases:

            def mock_import(name, *args, **kwargs):
                if provider_type.value in name:
                    raise ImportError("Module not found")
                return __import__(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ImportError) as exc_info:
                    factory.create_provider(
                        provider_type, {"type": provider_type.value}
                    )

                assert expected_msg in str(exc_info.value)

    def test_type_checking_imports_not_executed(self, factory):
        """Test that TYPE_CHECKING imports don't execute at runtime"""

        # This test verifies that providers are not imported during factory init
        # by checking that no providers are in the cache initially
        assert len(factory._providers) == 0

        # Factory should be usable even if all providers fail to import
        def mock_import(name, *args, **kwargs):
            if any(
                p in name
                for p in ["openai_provider", "anthropic_provider", "local_provider"]
            ):
                raise ImportError("All modules fail")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            # Factory should still function for availability checks
            available = factory.is_provider_available(ProviderType.OPENAI)
            assert not available
            assert ProviderType.OPENAI in factory._import_failures


class TestProviderFactoryIntegration:
    """Integration tests for lazy loading with mocked providers"""

    @pytest.fixture
    def factory_with_config(self):
        config = {
            "ai_providers": {
                "test_openai": {
                    "type": "openai",
                    "api_key": "test",
                },  # pragma: allowlist secret
                "test_local": {"type": "local", "model_name": "test"},
            }
        }
        return ProviderFactory(config)

    @pytest.mark.asyncio
    async def test_end_to_end_lazy_loading(self, factory_with_config):
        """Test complete lazy loading workflow"""

        factory = factory_with_config

        # Step 1: Check initial state (no imports yet)
        assert len(factory._providers) == 0

        # Step 2: Check availability (triggers lazy import attempt)
        def mock_import(name, *args, **kwargs):
            if "openai_provider" in name:
                raise ImportError("Mock import failure")
            return __import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            openai_available = factory.is_provider_available(ProviderType.OPENAI)
            assert not openai_available
            assert ProviderType.OPENAI in factory._import_failures

        # Step 3: Try to create provider (should fail gracefully)
        # Since the import failure was already tracked, creating should fail
        if ProviderType.OPENAI in factory._import_failures:
            # Factory knows this provider failed to import, so creation should fail
            with pytest.raises(ImportError):
                with patch("builtins.__import__", side_effect=mock_import):
                    factory.create_provider(
                        ProviderType.OPENAI,
                        {
                            "type": "openai",
                            "api_key": "test",
                        },  # pragma: allowlist secret
                    )
        else:
            # If not tracked as failed, skip this specific test
            pass

        # Step 4: Get failure summary
        summary = factory.get_provider_failure_summary()
        assert len(summary["import_failures"]) > 0
        assert "recommendations" in summary
        assert len(summary["recommendations"]) > 0

        # Step 5: Validate configuration
        validation = await factory.validate_configuration()
        assert not validation["is_valid"]  # Should fail due to import errors


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
