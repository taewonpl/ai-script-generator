"""
Configuration management for specialized agents and advanced features
"""

import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional

from ..workflows.agents import AgentPriority
from ..workflows.quality import QualityDimension


class ConfigurationProfile(str, Enum):
    """Predefined configuration profiles"""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CREATIVE = "creative"
    TECHNICAL = "technical"


@dataclass
class AgentConfiguration:
    """Configuration for individual agents"""

    enabled: bool = True
    intensity: float = 0.7
    priority: AgentPriority = AgentPriority.MEDIUM
    max_tokens: int = 4000
    temperature: float = 0.7
    custom_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityConfiguration:
    """Configuration for quality assessment"""

    dimension_weights: dict[str, float] = field(
        default_factory=lambda: {
            QualityDimension.PLOT_STRUCTURE.value: 0.2,
            QualityDimension.CHARACTER_DEVELOPMENT.value: 0.18,
            QualityDimension.DIALOGUE_QUALITY.value: 0.15,
            QualityDimension.VISUAL_STORYTELLING.value: 0.12,
            QualityDimension.EMOTIONAL_IMPACT.value: 0.15,
            QualityDimension.PACING_AND_RHYTHM.value: 0.1,
            QualityDimension.ORIGINALITY.value: 0.05,
            QualityDimension.TECHNICAL_CRAFT.value: 0.05,
        }
    )
    quality_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "excellent": 0.85,
            "good": 0.7,
            "acceptable": 0.5,
            "needs_improvement": 0.0,
        }
    )
    minimum_content_length: int = 100
    assessment_confidence_threshold: float = 0.6


@dataclass
class CoordinatorConfiguration:
    """Configuration for agent coordinator"""

    max_agents_per_execution: int = 3
    min_confidence_threshold: float = 0.4
    parallel_execution_enabled: bool = True
    timeout_seconds: float = 300.0
    retry_failed_agents: bool = True
    agent_selection_strategy: str = "confidence_priority"


@dataclass
class FeedbackConfiguration:
    """Configuration for feedback learning system"""

    learning_rate: float = 0.1
    preference_decay: float = 0.95
    minimum_feedback_count: int = 5
    user_profile_refresh_days: int = 30
    implicit_feedback_weight: float = 0.3
    explicit_feedback_weight: float = 0.7


@dataclass
class AdvancedConfiguration:
    """Complete advanced configuration for the generation service"""

    agents: dict[str, AgentConfiguration] = field(
        default_factory=lambda: {
            "plot_twister": AgentConfiguration(
                intensity=0.7,
                priority=AgentPriority.HIGH,
                custom_config={
                    "twist_intensity": 0.7,
                    "max_twists": 2,
                    "preserve_ending": True,
                    "minimum_content_length": 500,
                },
            ),
            "flaw_generator": AgentConfiguration(
                intensity=0.6,
                priority=AgentPriority.MEDIUM,
                custom_config={
                    "max_flaws_per_character": 2,
                    "flaw_intensity": 0.6,
                    "preserve_likability": True,
                    "minimum_characters": 2,
                },
            ),
            "dialogue_enhancer": AgentConfiguration(
                intensity=0.8,
                priority=AgentPriority.HIGH,
                custom_config={
                    "humor_level": 0.7,
                    "naturalness_boost": 0.8,
                    "character_voice_strength": 0.9,
                    "minimum_dialogue_ratio": 0.3,
                },
            ),
            "scene_visualizer": AgentConfiguration(
                intensity=0.7,
                priority=AgentPriority.MEDIUM,
                custom_config={
                    "detail_level": 0.7,
                    "cinematic_style": True,
                    "sensory_enhancement": 0.8,
                    "atmosphere_boost": 0.9,
                },
            ),
            "tension_builder": AgentConfiguration(
                intensity=0.8,
                priority=AgentPriority.HIGH,
                custom_config={
                    "tension_intensity": 0.8,
                    "conflict_enhancement": 0.9,
                    "climax_strength": 0.9,
                    "minimum_conflict_scenes": 2,
                },
            ),
        }
    )

    quality: QualityConfiguration = field(default_factory=QualityConfiguration)
    coordinator: CoordinatorConfiguration = field(
        default_factory=CoordinatorConfiguration
    )
    feedback: FeedbackConfiguration = field(default_factory=FeedbackConfiguration)

    # System-wide settings
    ai_provider_preferences: list[str] = field(
        default_factory=lambda: ["openai", "anthropic", "ollama"]
    )
    default_temperature: float = 0.7
    max_total_tokens: int = 16000
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Feature flags
    enable_adaptive_workflows: bool = True
    enable_quality_assessment: bool = True
    enable_feedback_learning: bool = True
    enable_user_personalization: bool = True
    enable_parallel_execution: bool = True


class ConfigurationManager:
    """
    Manages configuration for specialized agents and advanced features

    Features:
    - Profile-based configurations
    - Environment variable overrides
    - Runtime configuration updates
    - Configuration validation
    - Export/import capabilities
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        profile: ConfigurationProfile = ConfigurationProfile.BALANCED,
    ):
        self.config_file = config_file or os.getenv(
            "AGENTS_CONFIG_FILE", "agents_config.json"
        )
        self.profile = profile
        self.config = self._load_or_create_config()

        # Apply environment variable overrides
        self._apply_env_overrides()

    def _load_or_create_config(self) -> AdvancedConfiguration:
        """Load configuration from file or create default"""

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file) as f:
                    config_dict = json.load(f)
                return self._dict_to_config(config_dict)
            except Exception as e:
                print(f"Failed to load config file {self.config_file}: {e}")
                print("Using default configuration")

        # Create default configuration based on profile
        return self._create_profile_config(self.profile)

    def _create_profile_config(
        self, profile: ConfigurationProfile
    ) -> AdvancedConfiguration:
        """Create configuration based on profile"""

        base_config = AdvancedConfiguration()

        if profile == ConfigurationProfile.CONSERVATIVE:
            # Conservative settings - lower intensity, fewer agents
            for agent_config in base_config.agents.values():
                agent_config.intensity *= 0.7
            base_config.coordinator.max_agents_per_execution = 2
            base_config.coordinator.min_confidence_threshold = 0.6

        elif profile == ConfigurationProfile.AGGRESSIVE:
            # Aggressive settings - higher intensity, more agents
            for agent_config in base_config.agents.values():
                agent_config.intensity = min(agent_config.intensity * 1.3, 1.0)
            base_config.coordinator.max_agents_per_execution = 5
            base_config.coordinator.min_confidence_threshold = 0.3

        elif profile == ConfigurationProfile.CREATIVE:
            # Creative settings - emphasize plot and originality
            base_config.agents["plot_twister"].intensity = 0.9
            base_config.agents["plot_twister"].priority = AgentPriority.CRITICAL
            base_config.quality.dimension_weights[
                QualityDimension.ORIGINALITY.value
            ] = 0.15
            base_config.quality.dimension_weights[
                QualityDimension.PLOT_STRUCTURE.value
            ] = 0.25

        elif profile == ConfigurationProfile.TECHNICAL:
            # Technical settings - emphasize craft and structure
            base_config.quality.dimension_weights[
                QualityDimension.TECHNICAL_CRAFT.value
            ] = 0.15
            base_config.quality.dimension_weights[
                QualityDimension.DIALOGUE_QUALITY.value
            ] = 0.2
            base_config.coordinator.min_confidence_threshold = 0.7

        # BALANCED is the default, no modifications needed

        return base_config

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides"""

        # Agent-specific overrides
        for agent_name in self.config.agents.keys():
            env_prefix = f"AGENT_{agent_name.upper()}_"

            if os.getenv(f"{env_prefix}ENABLED"):
                self.config.agents[agent_name].enabled = (
                    os.getenv(f"{env_prefix}ENABLED").lower() == "true"
                )

            if os.getenv(f"{env_prefix}INTENSITY"):
                try:
                    self.config.agents[agent_name].intensity = float(
                        os.getenv(f"{env_prefix}INTENSITY")
                    )
                except ValueError:
                    pass

        # System-wide overrides
        if os.getenv("MAX_AGENTS_PER_EXECUTION"):
            try:
                self.config.coordinator.max_agents_per_execution = int(
                    os.getenv("MAX_AGENTS_PER_EXECUTION")
                )
            except ValueError:
                pass

        if os.getenv("ENABLE_ADAPTIVE_WORKFLOWS"):
            self.config.enable_adaptive_workflows = (
                os.getenv("ENABLE_ADAPTIVE_WORKFLOWS").lower() == "true"
            )

        if os.getenv("ENABLE_FEEDBACK_LEARNING"):
            self.config.enable_feedback_learning = (
                os.getenv("ENABLE_FEEDBACK_LEARNING").lower() == "true"
            )

    def get_agent_config(self, agent_name: str) -> AgentConfiguration:
        """Get configuration for a specific agent"""
        return self.config.agents.get(agent_name, AgentConfiguration())

    def get_quality_config(self) -> QualityConfiguration:
        """Get quality assessment configuration"""
        return self.config.quality

    def get_coordinator_config(self) -> CoordinatorConfiguration:
        """Get coordinator configuration"""
        return self.config.coordinator

    def get_feedback_config(self) -> FeedbackConfiguration:
        """Get feedback system configuration"""
        return self.config.feedback

    def update_agent_config(
        self, agent_name: str, config_updates: dict[str, Any]
    ) -> None:
        """Update configuration for a specific agent"""

        if agent_name not in self.config.agents:
            self.config.agents[agent_name] = AgentConfiguration()

        agent_config = self.config.agents[agent_name]

        for key, value in config_updates.items():
            if hasattr(agent_config, key):
                setattr(agent_config, key, value)
            else:
                agent_config.custom_config[key] = value

    def update_quality_weights(self, dimension_weights: dict[str, float]) -> None:
        """Update quality dimension weights"""

        # Validate weights sum to approximately 1.0
        total_weight = sum(dimension_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            # Normalize weights
            dimension_weights = {
                k: v / total_weight for k, v in dimension_weights.items()
            }

        self.config.quality.dimension_weights.update(dimension_weights)

    def save_config(self, file_path: Optional[str] = None) -> None:
        """Save current configuration to file"""

        save_path = file_path or self.config_file
        config_dict = self._config_to_dict(self.config)

        try:
            with open(save_path, "w") as f:
                json.dump(config_dict, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration to {save_path}: {e}") from e

    def export_config(self) -> dict[str, Any]:
        """Export configuration as dictionary"""
        return self._config_to_dict(self.config)

    def import_config(self, config_dict: dict[str, Any]) -> None:
        """Import configuration from dictionary"""
        self.config = self._dict_to_config(config_dict)

    def reset_to_profile(self, profile: ConfigurationProfile) -> None:
        """Reset configuration to a specific profile"""
        self.profile = profile
        self.config = self._create_profile_config(profile)

    def validate_config(self) -> list[str]:
        """Validate current configuration and return any issues"""

        issues = []

        # Validate agent configurations
        for agent_name, agent_config in self.config.agents.items():
            if not 0.0 <= agent_config.intensity <= 1.0:
                issues.append(
                    f"Agent {agent_name} intensity must be between 0.0 and 1.0"
                )

            if agent_config.max_tokens <= 0:
                issues.append(f"Agent {agent_name} max_tokens must be positive")

        # Validate quality weights
        total_weight = sum(self.config.quality.dimension_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            issues.append(
                f"Quality dimension weights sum to {total_weight:.2f}, should be close to 1.0"
            )

        # Validate coordinator settings
        if self.config.coordinator.max_agents_per_execution <= 0:
            issues.append("Coordinator max_agents_per_execution must be positive")

        if not 0.0 <= self.config.coordinator.min_confidence_threshold <= 1.0:
            issues.append(
                "Coordinator min_confidence_threshold must be between 0.0 and 1.0"
            )

        # Validate feedback settings
        if not 0.0 <= self.config.feedback.learning_rate <= 1.0:
            issues.append("Feedback learning_rate must be between 0.0 and 1.0")

        return issues

    def get_config_summary(self) -> dict[str, Any]:
        """Get a summary of current configuration"""

        enabled_agents = [
            name for name, config in self.config.agents.items() if config.enabled
        ]
        avg_intensity = sum(
            config.intensity for config in self.config.agents.values()
        ) / len(self.config.agents)

        return {
            "profile": self.profile.value,
            "enabled_agents": enabled_agents,
            "total_agents": len(self.config.agents),
            "average_intensity": round(avg_intensity, 2),
            "max_agents_per_execution": self.config.coordinator.max_agents_per_execution,
            "adaptive_workflows_enabled": self.config.enable_adaptive_workflows,
            "feedback_learning_enabled": self.config.enable_feedback_learning,
            "quality_assessment_enabled": self.config.enable_quality_assessment,
        }

    def _config_to_dict(self, config: AdvancedConfiguration) -> dict[str, Any]:
        """Convert configuration object to dictionary"""

        config_dict = asdict(config)

        # Convert enum values to strings
        for agent_name, agent_config in config_dict["agents"].items():
            if "priority" in agent_config:
                agent_config["priority"] = (
                    agent_config["priority"].name
                    if hasattr(agent_config["priority"], "name")
                    else str(agent_config["priority"])
                )

        return config_dict

    def _dict_to_config(self, config_dict: dict[str, Any]) -> AdvancedConfiguration:
        """Convert dictionary to configuration object"""

        # Handle enum conversions
        if "agents" in config_dict:
            for agent_name, agent_config in config_dict["agents"].items():
                if "priority" in agent_config and isinstance(
                    agent_config["priority"], str
                ):
                    try:
                        agent_config["priority"] = AgentPriority[
                            agent_config["priority"]
                        ]
                    except KeyError:
                        agent_config["priority"] = AgentPriority.MEDIUM

        # Create configuration objects
        agents = {}
        if "agents" in config_dict:
            for agent_name, agent_data in config_dict["agents"].items():
                agents[agent_name] = AgentConfiguration(**agent_data)

        quality = QualityConfiguration(**config_dict.get("quality", {}))
        coordinator = CoordinatorConfiguration(**config_dict.get("coordinator", {}))
        feedback = FeedbackConfiguration(**config_dict.get("feedback", {}))

        # Create main config
        main_config_data = {
            k: v
            for k, v in config_dict.items()
            if k not in ["agents", "quality", "coordinator", "feedback"]
        }

        return AdvancedConfiguration(
            agents=agents,
            quality=quality,
            coordinator=coordinator,
            feedback=feedback,
            **main_config_data,
        )


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        profile_name = os.getenv("AGENTS_CONFIG_PROFILE", "balanced")
        try:
            profile = ConfigurationProfile(profile_name)
        except ValueError:
            profile = ConfigurationProfile.BALANCED

        _config_manager = ConfigurationManager(profile=profile)

    return _config_manager


def initialize_config_manager(
    config_file: Optional[str] = None,
    profile: ConfigurationProfile = ConfigurationProfile.BALANCED,
) -> ConfigurationManager:
    """Initialize global configuration manager with specific settings"""
    global _config_manager
    _config_manager = ConfigurationManager(config_file, profile)
    return _config_manager
