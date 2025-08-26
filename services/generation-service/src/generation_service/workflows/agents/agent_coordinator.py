"""
Agent Coordinator - Manages and coordinates specialized AI agents
"""

import asyncio
from datetime import datetime
from typing import Any, Optional, Dict, List, Tuple

# Import Core Module components
try:
    from ai_script_core import (
        get_service_logger,
        utc_now,
    )

    CORE_AVAILABLE = True
    logger = get_service_logger("generation-service.agent_coordinator")
except (ImportError, RuntimeError):
    CORE_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)

    # Fallback utility functions
    def utc_now() -> datetime:
        """Fallback UTC timestamp"""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)

    def generate_uuid() -> str:
        """Fallback UUID generation"""
        import uuid

        return str(uuid.uuid4())

    def generate_id() -> str:
        """Fallback ID generation"""
        import uuid

        return str(uuid.uuid4())[:8]

    # Fallback base classes
    class BaseDTO:
        """Fallback base DTO class"""

        pass

    class SuccessResponseDTO:
        """Fallback success response DTO"""

        pass

    class ErrorResponseDTO:
        """Fallback error response DTO"""

        pass


from generation_service.workflows.state import GenerationState

from .base_agent import AgentCapability, BaseSpecialAgent
from .dialogue_enhancer_agent import DialogueEnhancerAgent
from .flaw_generator_agent import FlawGeneratorAgent
from .plot_twister_agent import PlotTwisterAgent
from .scene_visualizer_agent import SceneVisualizerAgent
from .tension_builder_agent import TensionBuilderAgent


class AgentExecutionPlan:
    """Plan for agent execution with dependencies and ordering"""

    def __init__(self) -> None:
        self.agents: list[tuple[BaseSpecialAgent, dict[str, Any]]] = []
        self.execution_order: list[str] = []
        self.parallel_groups: list[list[str]] = []
        self.dependencies: dict[str, list[str]] = {}
        self.estimated_duration: float = 0.0
        self.confidence_score: float = 0.0

    def add_agent(
        self,
        agent: BaseSpecialAgent,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """Add an agent to the execution plan"""
        self.agents.append((agent, config or {}))
        if dependencies:
            self.dependencies[agent.agent_name] = dependencies

    def optimize_execution_order(self) -> None:
        """Optimize execution order based on dependencies and priorities"""
        # Sort by priority (higher priority first) and dependencies
        agent_priorities = [
            (agent.agent_name, agent.priority.value) for agent, _ in self.agents
        ]
        agent_priorities.sort(key=lambda x: x[1], reverse=True)

        # Create execution order respecting dependencies
        executed = set()
        self.execution_order = []

        while len(executed) < len(self.agents):
            for agent_name, _ in agent_priorities:
                if agent_name in executed:
                    continue

                # Check if dependencies are satisfied
                deps = self.dependencies.get(agent_name, [])
                if all(dep in executed for dep in deps):
                    self.execution_order.append(agent_name)
                    executed.add(agent_name)

        # Identify parallel execution opportunities
        self._identify_parallel_groups()

    def _identify_parallel_groups(self) -> None:
        """Identify agents that can be executed in parallel"""
        self.parallel_groups = []
        remaining = set(self.execution_order)

        while remaining:
            # Find agents with no remaining dependencies
            parallel_group = []
            for agent_name in list(remaining):
                deps = self.dependencies.get(agent_name, [])
                if not any(dep in remaining for dep in deps):
                    parallel_group.append(agent_name)

            if parallel_group:
                self.parallel_groups.append(parallel_group)
                remaining -= set(parallel_group)
            else:
                # Handle circular dependencies by taking highest priority
                highest_priority = max(
                    remaining,
                    key=lambda x: next(
                        agent.priority.value
                        for agent, _ in self.agents
                        if agent.agent_name == x
                    ),
                )
                self.parallel_groups.append([highest_priority])
                remaining.remove(highest_priority)


class AgentCoordinator:
    """
    Coordinates specialized AI agents based on content analysis and user preferences

    Features:
    - Adaptive agent selection based on content analysis
    - Intelligent execution planning and optimization
    - Parallel execution of independent agents
    - Quality assessment and feedback loops
    - Configuration management for agent behavior
    """

    def __init__(self, provider_factory: Optional[Any] = None, config: Optional[Dict[str, Any]] = None) -> None:
        self.provider_factory = provider_factory
        self.config = config or {}

        # Initialize specialized agents
        self.agents: dict[str, BaseSpecialAgent] = {
            "plot_twister": PlotTwisterAgent(
                provider_factory, self.config.get("plot_twister", {})
            ),
            "flaw_generator": FlawGeneratorAgent(
                provider_factory, self.config.get("flaw_generator", {})
            ),
            "dialogue_enhancer": DialogueEnhancerAgent(
                provider_factory, self.config.get("dialogue_enhancer", {})
            ),
            "scene_visualizer": SceneVisualizerAgent(
                provider_factory, self.config.get("scene_visualizer", {})
            ),
            "tension_builder": TensionBuilderAgent(
                provider_factory, self.config.get("tension_builder", {})
            ),
        }

        # Agent capability mappings
        self.capability_agents = {
            AgentCapability.PLOT_ENHANCEMENT: ["plot_twister"],
            AgentCapability.CHARACTER_DEVELOPMENT: ["flaw_generator"],
            AgentCapability.DIALOGUE_IMPROVEMENT: ["dialogue_enhancer"],
            AgentCapability.VISUAL_ENHANCEMENT: ["scene_visualizer"],
            AgentCapability.TENSION_BUILDING: ["tension_builder"],
            AgentCapability.PACING_OPTIMIZATION: ["tension_builder"],
        }

        # Execution metrics
        self.total_executions = 0
        self.successful_executions = 0
        self.agent_performance = {}

        if CORE_AVAILABLE:
            logger.info(
                "AgentCoordinator initialized",
                extra={
                    "agent_count": len(self.agents),
                    "capabilities": list(self.capability_agents.keys()),
                },
            )

    async def analyze_content_needs(self, state: GenerationState) -> Dict[str, Any]:
        """
        Analyze content to determine which agents should be applied
        """

        content = state.get("styled_script") or state.get("draft_script", "")
        if not content:
            return {"suitable_agents": [], "analysis_confidence": 0.0}

        # Analyze content with each agent
        agent_analyses = {}
        for agent_name, agent in self.agents.items():
            try:
                analysis = await agent.analyze_content(state)
                agent_analyses[agent_name] = analysis
            except Exception as e:
                logger.warning(f"Failed to analyze with {agent_name}: {e}")
                agent_analyses[agent_name] = {"should_enhance": False, "error": str(e)}

        # Determine suitable agents
        suitable_agents = []
        total_confidence = 0.0

        for agent_name, analysis in agent_analyses.items():
            if analysis.get("should_enhance", False):
                confidence = analysis.get("enhancement_confidence", 0.5)
                suitable_agents.append(
                    {
                        "agent_name": agent_name,
                        "confidence": confidence,
                        "analysis": analysis,
                        "priority": self.agents[agent_name].priority.value,
                    }
                )
                total_confidence += confidence

        # Sort by confidence and priority
        suitable_agents.sort(
            key=lambda x: (x["confidence"], x["priority"]), reverse=True
        )

        analysis_result = {
            "suitable_agents": suitable_agents,
            "analysis_confidence": (
                total_confidence / len(self.agents) if self.agents else 0.0
            ),
            "agent_analyses": agent_analyses,
            "content_length": len(content),
            "content_quality_estimate": self._estimate_initial_quality(content),
        }

        return analysis_result

    async def create_execution_plan(
        self, state: GenerationState, preferences: Optional[Dict[str, Any]] = None
    ) -> AgentExecutionPlan:
        """
        Create optimized execution plan for agents
        """

        preferences = preferences or {}
        content_analysis = await self.analyze_content_needs(state)

        plan = AgentExecutionPlan()

        # Apply preferences and filters
        max_agents = preferences.get("max_agents", 3)
        min_confidence = preferences.get("min_confidence", 0.4)
        required_capabilities = preferences.get("required_capabilities", [])
        excluded_agents = preferences.get("excluded_agents", [])

        # Select agents based on analysis and preferences
        selected_agents = []
        for agent_info in content_analysis["suitable_agents"]:
            agent_name = agent_info["agent_name"]

            # Apply filters
            if (
                len(selected_agents) >= max_agents
                or agent_info["confidence"] < min_confidence
                or agent_name in excluded_agents
            ):
                continue

            selected_agents.append(agent_info)

        # Ensure required capabilities are included
        for capability in required_capabilities:
            if capability in self.capability_agents:
                for agent_name in self.capability_agents[capability]:
                    if agent_name not in [a["agent_name"] for a in selected_agents]:
                        if agent_name not in excluded_agents:
                            selected_agents.append(
                                {
                                    "agent_name": agent_name,
                                    "confidence": 0.5,  # Default confidence for required agents
                                    "analysis": {},
                                    "priority": self.agents[agent_name].priority.value,
                                }
                            )

        # Add selected agents to plan
        for agent_info in selected_agents:
            agent = self.agents[agent_info["agent_name"]]
            config = self._create_agent_config(agent_info, preferences)
            dependencies = self._determine_dependencies(
                agent_info["agent_name"], selected_agents
            )

            plan.add_agent(agent, config, dependencies)

        # Optimize execution order
        plan.optimize_execution_order()
        plan.estimated_duration = self._estimate_execution_duration(plan)
        plan.confidence_score = content_analysis["analysis_confidence"]

        return plan

    async def execute_plan(
        self, state: GenerationState, plan: AgentExecutionPlan
    ) -> GenerationState:
        """
        Execute the agent plan with optimization and error handling
        """

        self.total_executions += 1
        start_time = utc_now() if CORE_AVAILABLE else datetime.now()

        try:
            enhanced_state = state.copy()
            execution_results = []

            # Execute agents in parallel groups
            for group in plan.parallel_groups:
                if len(group) == 1:
                    # Single agent execution
                    agent_name = group[0]
                    agent = self.agents[agent_name]

                    result = await agent.execute(enhanced_state)
                    enhanced_state = result

                    execution_results.append(
                        {
                            "agent_name": agent_name,
                            "status": (
                                "completed"
                                if not result.get("has_errors")
                                else "failed"
                            ),
                            "execution_time": 0.0,  # Will be calculated by agent
                        }
                    )

                else:
                    # Parallel execution
                    tasks = []
                    for agent_name in group:
                        agent = self.agents[agent_name]
                        task = asyncio.create_task(agent.execute(enhanced_state))
                        tasks.append((agent_name, task))

                    # Wait for all tasks in the group
                    group_results = await asyncio.gather(
                        *[task for _, task in tasks], return_exceptions=True
                    )

                    # Process results
                    for i, (agent_name, _) in enumerate(tasks):
                        result = group_results[i]

                        if isinstance(result, Exception):
                            logger.error(f"Agent {agent_name} failed: {result}")
                            execution_results.append(
                                {
                                    "agent_name": agent_name,
                                    "status": "failed",
                                    "error": str(result),
                                }
                            )
                        else:
                            # Merge successful results
                            enhanced_state = self._merge_agent_results(
                                enhanced_state, result
                            )
                            execution_results.append(
                                {"agent_name": agent_name, "status": "completed"}
                            )

            # Calculate execution metrics
            end_time = utc_now() if CORE_AVAILABLE else datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            # Update coordination metadata
            enhanced_state["coordination_metadata"] = {
                "coordinator": "AgentCoordinator",
                "execution_plan": {
                    "agents_executed": [r["agent_name"] for r in execution_results],
                    "parallel_groups": plan.parallel_groups,
                    "total_duration": total_duration,
                    "estimated_duration": plan.estimated_duration,
                },
                "execution_results": execution_results,
                "overall_success": all(
                    r["status"] == "completed" for r in execution_results
                ),
            }

            self.successful_executions += 1

            if CORE_AVAILABLE:
                logger.info(
                    "Agent coordination completed",
                    extra={
                        "generation_id": state["generation_id"],
                        "agents_executed": len(execution_results),
                        "total_duration": total_duration,
                        "success_rate": self.successful_executions
                        / self.total_executions,
                    },
                )

            return enhanced_state

        except Exception as e:
            logger.error(f"Agent coordination failed: {e}")

            # Return state with error information
            error_state = state.copy()
            error_state["has_errors"] = True
            error_state["error_messages"] = error_state.get("error_messages", [])
            error_state["error_messages"].append(f"Agent coordination failed: {e!s}")

            return error_state

    async def execute_adaptive_workflow(
        self, state: GenerationState, preferences: Optional[Dict[str, Any]] = None
    ) -> GenerationState:
        """
        Execute complete adaptive workflow: analyze, plan, and execute
        """

        # Create execution plan
        plan = await self.create_execution_plan(state, preferences)

        if not plan.agents:
            logger.info("No agents selected for execution")
            return state

        # Execute the plan
        return await self.execute_plan(state, plan)

    def get_agent_recommendations(self, state: GenerationState) -> Optional[Dict[str, Any]]:
        """
        Get agent recommendations without executing them
        """

        # This would typically be async, but we'll make it sync for convenience
        # In practice, you might want to cache analyses
        return None

    def _estimate_initial_quality(self, content: str) -> float:
        """Estimate initial content quality"""

        if not content:
            return 0.0

        # Simple quality estimation based on content characteristics
        factors = [
            (len(content) > 500, 0.2),  # Sufficient length
            (content.count("\n") > 10, 0.2),  # Proper formatting
            ('"' in content, 0.2),  # Has dialogue
            (
                any(word in content.lower() for word in ["ext.", "int."]),
                0.2,
            ),  # Script format
            (len(content.split()) > 100, 0.2),  # Adequate word count
        ]

        quality = 0.0
        for condition, weight in factors:
            if condition:
                quality += weight

        return quality

    def _create_agent_config(
        self, agent_info: Dict[str, Any], preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create configuration for an agent based on analysis and preferences"""

        base_config = self.config.get(agent_info["agent_name"], {})

        # Apply preference overrides
        agent_preferences = preferences.get("agent_configs", {}).get(
            agent_info["agent_name"], {}
        )
        config = {**base_config, **agent_preferences}

        # Adjust based on confidence
        confidence = agent_info["confidence"]
        if confidence < 0.6:
            # Lower intensity for low confidence
            config["intensity"] = config.get("intensity", 0.7) * 0.8

        return config

    def _determine_dependencies(
        self, agent_name: str, selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """Determine execution dependencies for an agent"""

        # Define dependency rules
        dependency_rules = {
            "plot_twister": [],  # Can run independently
            "flaw_generator": [],  # Can run independently
            "dialogue_enhancer": [
                "flaw_generator"
            ],  # Better after character development
            "scene_visualizer": [],  # Can run independently
            "tension_builder": [
                "plot_twister",
                "flaw_generator",
            ],  # Benefits from plot and character work
        }

        agent_dependencies = dependency_rules.get(agent_name, [])
        selected_agent_names = [a["agent_name"] for a in selected_agents]

        # Only include dependencies that are actually selected
        return [dep for dep in agent_dependencies if dep in selected_agent_names]

    def _estimate_execution_duration(self, plan: AgentExecutionPlan) -> float:
        """Estimate total execution duration for the plan"""

        # Base execution times (in seconds) - these could be learned from metrics
        base_times = {
            "plot_twister": 30.0,
            "flaw_generator": 25.0,
            "dialogue_enhancer": 35.0,
            "scene_visualizer": 20.0,
            "tension_builder": 30.0,
        }

        total_time = 0.0

        # Calculate time for each parallel group
        for group in plan.parallel_groups:
            group_time = max(base_times.get(agent_name, 30.0) for agent_name in group)
            total_time += group_time

        return total_time

    def _merge_agent_results(
        self, base_state: GenerationState, agent_result: GenerationState
    ) -> GenerationState:
        """Merge results from parallel agent execution"""

        merged_state = base_state.copy()

        # Merge enhanced content (use the latest)
        if "enhanced_script" in agent_result:
            merged_state["enhanced_script"] = agent_result["enhanced_script"]

        # Merge metadata
        if "generation_metadata" in agent_result:
            if "generation_metadata" not in merged_state:
                merged_state["generation_metadata"] = {}
            merged_state["generation_metadata"].update(
                agent_result["generation_metadata"]
            )

        # Merge execution logs
        if "execution_log" in agent_result:
            if "execution_log" not in merged_state:
                merged_state["execution_log"] = []
            merged_state["execution_log"].extend(agent_result["execution_log"])

        # Update quality score (take the maximum improvement)
        current_quality = merged_state.get("current_quality_score", 0.0)
        agent_quality = agent_result.get("current_quality_score", 0.0)
        merged_state["current_quality_score"] = max(current_quality, agent_quality)

        return merged_state

    def get_coordinator_metrics(self) -> Dict[str, Any]:
        """Get coordinator performance metrics"""

        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0
                else 0.0
            ),
            "available_agents": list(self.agents.keys()),
            "agent_performance": {
                agent_name: agent.get_agent_metrics()
                for agent_name, agent in self.agents.items()
            },
        }
