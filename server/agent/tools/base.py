"""
Base Tool Classes for Agent System

Defines the interface for all agent tools and the tool registry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Type
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories for organizing tools."""
    SEARCH = "search"
    GRAPH = "graph"
    ARTIFACT = "artifact"
    COMPARISON = "comparison"


@dataclass
class ParameterSpec:
    """Specification for a tool parameter."""
    name: str
    type: str  # "str", "int", "float", "bool", "list", "dict"
    description: str
    required: bool = True
    default: Any = None
    enum: List[Any] = None  # For constrained values


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.

    Each tool must implement:
    - name: Unique tool identifier
    - description: What the tool does (for LLM)
    - category: Tool category
    - parameters: Parameter specifications
    - execute(): Tool execution logic
    """

    # Class attributes to be defined by subclasses
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.SEARCH
    parameters: Dict[str, ParameterSpec] = {}

    # Timeout in seconds
    timeout: float = 30.0

    def __init__(self):
        """Initialize the tool."""
        if not self.name:
            raise ValueError(f"Tool must define a name")
        if not self.description:
            raise ValueError(f"Tool {self.name} must define a description")

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolResult with success status and data
        """
        pass

    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate parameters against specifications.

        Returns:
            Tuple of (is_valid, error_message)
        """
        for param_name, spec in self.parameters.items():
            value = kwargs.get(param_name)

            # Check required
            if spec.required and value is None and spec.default is None:
                return False, f"Missing required parameter: {param_name}"

            # Check type if value provided
            if value is not None:
                if spec.type == "str" and not isinstance(value, str):
                    return False, f"Parameter {param_name} must be string"
                elif spec.type == "int" and not isinstance(value, int):
                    return False, f"Parameter {param_name} must be integer"
                elif spec.type == "float" and not isinstance(value, (int, float)):
                    return False, f"Parameter {param_name} must be number"
                elif spec.type == "bool" and not isinstance(value, bool):
                    return False, f"Parameter {param_name} must be boolean"
                elif spec.type == "list" and not isinstance(value, list):
                    return False, f"Parameter {param_name} must be list"
                elif spec.type == "dict" and not isinstance(value, dict):
                    return False, f"Parameter {param_name} must be dict"

                # Check enum constraints
                if spec.enum and value not in spec.enum:
                    return False, f"Parameter {param_name} must be one of: {spec.enum}"

        return True, None

    def run(self, **kwargs) -> ToolResult:
        """
        Run the tool with validation and timing.

        This is the main entry point for tool execution.
        """
        # Validate parameters
        is_valid, error = self.validate_params(**kwargs)
        if not is_valid:
            return ToolResult(
                success=False,
                data=None,
                error=error
            )

        # Apply defaults
        for param_name, spec in self.parameters.items():
            if param_name not in kwargs or kwargs[param_name] is None:
                if spec.default is not None:
                    kwargs[param_name] = spec.default

        # Execute with timing
        start_time = time.time()
        try:
            result = self.execute(**kwargs)
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def get_schema(self) -> Dict:
        """
        Get the tool schema for LLM function calling.

        Returns OpenAI function calling format.
        """
        properties = {}
        required = []

        for param_name, spec in self.parameters.items():
            prop = {
                "type": self._map_type(spec.type),
                "description": spec.description
            }
            if spec.enum:
                prop["enum"] = spec.enum
            properties[param_name] = prop

            if spec.required:
                required.append(param_name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def _map_type(self, type_str: str) -> str:
        """Map internal type to JSON Schema type."""
        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object"
        }
        return type_map.get(type_str, "string")


class ToolRegistry:
    """
    Registry for all agent tools.

    Provides:
    - Tool registration and lookup
    - Schema generation for LLM
    - Tool execution by name
    """

    def __init__(self):
        """Initialize empty registry."""
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool instance."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_class(self, tool_class: Type[BaseTool]):
        """Register a tool by class (instantiates it)."""
        tool = tool_class()
        self.register(tool)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool not found: {name}"
            )
        return tool.run(**kwargs)

    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get tools filtered by category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_tool_schemas(self) -> List[Dict]:
        """Get schemas for all tools (for LLM)."""
        return [tool.get_schema() for tool in self._tools.values()]

    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for prompts."""
        lines = []
        for tool in self._tools.values():
            params = ", ".join([
                f"{name}: {spec.type}" + ("?" if not spec.required else "")
                for name, spec in tool.parameters.items()
            ])
            lines.append(f"- {tool.name}({params}): {tool.description}")
        return "\n".join(lines)

    def list_tools(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())


# Global registry instance
_global_registry = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry, initializing if needed."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _register_all_tools(_global_registry)
    return _global_registry


def _register_all_tools(registry: ToolRegistry):
    """Register all 17 available tools."""
    # Import and register graph tools (6)
    from .graph_tools import (
        GetNodeNeighborsTool,
        GetConceptPathTool,
        GetCausalChainTool,
        GetClusterSubgraphTool,
        GetSpeakerContributionGraphTool,
        TraceConceptToSourceTool
    )

    registry.register_class(GetNodeNeighborsTool)
    registry.register_class(GetConceptPathTool)
    registry.register_class(GetCausalChainTool)
    registry.register_class(GetClusterSubgraphTool)
    registry.register_class(GetSpeakerContributionGraphTool)
    registry.register_class(TraceConceptToSourceTool)

    # Import and register search tools (5)
    from .search_tools import (
        SearchTranscriptChunksTool,
        SearchConceptNodesTool,
        SearchConceptClustersTool,
        SearchSessionsTool,
        SearchSpeakersTool
    )

    registry.register_class(SearchTranscriptChunksTool)
    registry.register_class(SearchConceptNodesTool)
    registry.register_class(SearchConceptClustersTool)
    registry.register_class(SearchSessionsTool)
    registry.register_class(SearchSpeakersTool)

    # Import and register artifact tools (4)
    from .artifact_tools import (
        GetFullConceptMapTool,
        Get7CAnalysisTool,
        GetLIWCMetricsTool,
        GetTranscriptContextTool
    )

    registry.register_class(GetFullConceptMapTool)
    registry.register_class(Get7CAnalysisTool)
    registry.register_class(GetLIWCMetricsTool)
    registry.register_class(GetTranscriptContextTool)

    # Import and register comparison tools (2)
    from .comparison_tools import (
        CompareSessionsTool,
        CompareSpeakersTool
    )

    registry.register_class(CompareSessionsTool)
    registry.register_class(CompareSpeakersTool)

    logger.info(f"Registered {len(registry.list_tools())} tools")
