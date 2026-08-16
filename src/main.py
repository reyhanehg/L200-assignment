import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agents.coordinator import ConciergeCoordinator
from src.config import settings
from src.observability.tracing import metrics


def run_interactive_cli():
    """Run interactive terminal session with NutriConcierge."""
    print("=" * 70)
    print(f"🥗 Welcome to {settings.app_name} (v{settings.app_version})")
    print("Type 'exit' or 'quit' to end. Type 'metrics' to view telemetry.")
    print("=" * 70)

    coordinator = ConciergeCoordinator()
    session_id = "cli_session"
    user_id = "default_user"

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye! Stay healthy! 🥗")
                break
            if user_input.lower() == "metrics":
                print("\n📈 Observability Metrics:")
                print(metrics.get_summary())
                continue

            response = coordinator.run({
                "message": user_input,
                "session_id": session_id,
                "user_id": user_id,
            })

            print(f"\n🤖 NutriConcierge: {response.get('message', '')}")
            if "markdown_checklist" in response:
                print(f"\n{response['markdown_checklist']}")

        except (KeyboardInterrupt, EOFError):
            print("\nSession terminated.")
            break


def main():
    """Parse CLI arguments and run requested mode."""
    parser = argparse.ArgumentParser(description="NutriConcierge AI Agent Application")
    parser.add_argument("--cli", action="store_true", help="Run interactive CLI chat")
    parser.add_argument("--plan", type=int, default=None, help="Directly generate an N-day meal plan and print grocery list")
    parser.add_argument("--metrics", action="store_true", help="Display observability telemetry metrics")

    args = parser.parse_args()

    if args.plan:
        coordinator = ConciergeCoordinator()
        res = coordinator.run({"intent": "PLAN_MEALS", "num_days": args.plan})
        print(res.get("message"))
        print("\n" + res.get("markdown_checklist", ""))
    elif args.metrics:
        print(metrics.get_summary())
    else:
        run_interactive_cli()


if __name__ == "__main__":
    main()
