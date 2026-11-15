"""
AXON Agent — CLI entry point.
Run with: uv run python agent/main.py

Starts the agent loop and enters a REPL.
Type your request, press Enter, get a response.
Type 'exit' or 'quit' to stop.
Type 'clear' to reset conversation history.
"""

from agent.agent_loop import AgentLoop
from agent.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    """
    CLI chat loop for AXON agent.
    Initialises the agent once, then processes user messages in a loop.
    """
    print("\n╔══════════════════════════════╗")
    print("║   AXON — File System Agent   ║")
    print("║  Type 'exit' to quit         ║")
    print("╚══════════════════════════════╝\n")

    print("⚡ Starting AXON agent...")
    agent = AgentLoop.create()
    print("✅ Agent ready. MCP server connected.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if user_input.lower() == "clear":
            agent._session.clear()
            print("✅ Conversation cleared.\n")
            continue

        try:
            response = agent.run_turn(user_input)
            print(f"\nAXON: {response}\n")
        except Exception as e:
            logger.error("agent_turn_error", error=str(e))
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    main()
