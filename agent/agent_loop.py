from __future__ import annotations

from agent.llm.base_llm_adapter import BaseLLMAdapter
from agent.tool_bridge import ToolBridge
from agent.chat_session import ChatSession
from agent.logger import get_logger

_MAX_TOOL_ROUNDS = 10  # prevent infinite loops


class AgentLoop:
    """
    Core agentic loop: send message → get tool calls → execute → repeat.
    Stops when LLM returns a plain text response with no tool calls,
    or when _MAX_TOOL_ROUNDS is reached.

    Flow per user message:
      1. Add user message to session
      2. Call LLM with full history + tool schemas
      3. If response has tool_calls:
           a. Execute each tool via ToolBridge
           b. Add assistant message + tool results to session
           c. Call LLM again with updated history
      4. If response has no tool_calls: return final answer

    Single responsibility: orchestrate one turn of the agent loop.
    """

    def __init__(
        self,
        llm     : BaseLLMAdapter,
        bridge  : ToolBridge,
        session : ChatSession,
    ) -> None:
        self._llm     = llm
        self._bridge  = bridge
        self._session = session
        self._logger  = get_logger(__name__)

    @classmethod
    def create(cls) -> "AgentLoop":
        """
        Factory method: create a fully wired AgentLoop.
        Loads tools from MCP server and registers them with the LLM.
        """
        from agent.llm.llm_factory import LLMFactory

        bridge  = ToolBridge.create()
        bridge.load()

        llm = LLMFactory.create()
        llm.register_tools(bridge.get_schemas())

        session = ChatSession()

        return cls(llm=llm, bridge=bridge, session=session)

    def run_turn(self, user_input: str) -> str:
        """
        Process one user message through the full agent loop.
        Returns the final plain-text response from the LLM.
        """
        self._session.add_user(user_input)
        self._logger.info("agent_turn_started", input_length=len(user_input))

        for round_num in range(1, _MAX_TOOL_ROUNDS + 1):
            self._logger.info("agent_loop_round", round=round_num)

            response = self._llm.generate(
                messages = self._session.get_history(),
                tools    = self._bridge.get_schemas(),
            )

            if not response.has_tool_calls:
                # LLM gave a final answer — done
                self._session.add_assistant(response.content)
                self._logger.info(
                    "agent_turn_complete",
                    rounds          = round_num,
                    response_length = len(response.content),
                )
                return response.content

            # LLM wants to call tools — execute each one
            self._logger.info(
                "agent_tool_calls",
                round = round_num,
                tools = [tc["name"] for tc in response.tool_calls],
            )
            self._session.add_assistant(
                text       = response.content,
                tool_calls = response.tool_calls,
            )

            for tc in response.tool_calls:
                result = self._bridge.execute(tc["name"], tc["arguments"])
                self._session.add_tool_result(
                    tool_call_id = tc["id"],
                    result       = result,
                )
                self._logger.info(
                    "agent_tool_executed",
                    tool          = tc["name"],
                    result_length = len(result),
                )

        # Exceeded max rounds — return a safe fallback
        self._logger.warning("agent_max_rounds_exceeded", rounds=_MAX_TOOL_ROUNDS)
        return "I reached the maximum number of tool-call rounds. Please try rephrasing your request."
