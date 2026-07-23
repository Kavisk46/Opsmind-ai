from services.tools import Tool


class UnknownToolError(Exception):
    """Raised when the router picks a tool name that was never
    registered — a programming error (a typo in the router or a missing
    registration), not a user-facing condition, since tool names are
    internal implementation details never chosen by a client.
    """


class ToolRegistry:
    """A name -> Tool lookup, nothing more. This is the entire mechanism
    that lets a new tool be added without touching the orchestrator:
    build the tool, register() it under a name, and the orchestrator's
    routing logic can reference that name — the orchestrator's code for
    EXECUTING a tool (get() + await tool.run(...)) never changes no
    matter how many tools exist.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise UnknownToolError(name) from None

    def names(self) -> list[str]:
        return list(self._tools.keys())
