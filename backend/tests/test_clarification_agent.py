"""
Run this to verify the Clarification Agent runs and calls its tools.

From repo root:
  cd backend
  python -m scripts.test_clarification_agent

Or from backend folder:
  python -m scripts.test_clarification_agent

Requires .env with OPENROUTER_API_KEY. The script will run one turn and print
every event (agent_message_*, tool_call_*, ask_user, error, etc.). You should
see tool_call_start for check_spec_completeness within ~45–60s if the agent
and OpenRouter are working.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

# Ensure backend app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env from repo root (parent of backend)
from pathlib import Path
_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _env.exists():
    from dotenv import load_dotenv
    load_dotenv(_env)


async def main():
    from app.agent.agents.research import ClarificationAgent
    from app.agent.state import SharedState, Phase
    from app.models.project import Project

    project_id = "test-clarification-agent"
    state = SharedState(project_id=project_id, current_phase=Phase.RESEARCH)
    state.user_conversation = [
        {"role": "user", "content": "I want a simple bookstore API with books and authors."},
    ]

    project = Project(id=project_id, name="Test", description="Clarification test")
    agent = ClarificationAgent()

    print("Clarification Agent test – one turn (max ~120s)")
    print("Steps below show that OpenRouter is responding and the agent is using tools.")
    print("-" * 60)
    print("Step 1: Sending request to OpenRouter (wait for first response, max 45s)...")
    print()

    event_count = 0
    seen_tool_call = False
    seen_ask_user = False
    seen_error = False
    step = 1
    streamed_text = []  # what OpenRouter streamed (if any) before tool call

    try:
        async for event in agent.run(state=state, project=project, user_message=None):
            event_count += 1

            if event.type == "agent_message_delta":
                tok = event.data.get("token") or ""
                if tok:
                    streamed_text.append(tok)
            elif event.type == "tool_call_start":
                seen_tool_call = True
                step += 1
                tool_name = event.data.get("tool", "")
                args = event.data.get("arguments", {})
                print(f"Step {step}: OpenRouter returned a tool call: {tool_name}")
                print(f"    → Arguments from OpenRouter (what the model sent):")
                for k, v in args.items():
                    if k == "spec_json" and isinstance(v, str):
                        try:
                            parsed = json.loads(v)
                            print(f"       spec_json (parsed):")
                            print(json.dumps(parsed, indent=8))
                        except Exception:
                            print(f"       spec_json (raw): {v[:300]}{'...' if len(v) > 300 else ''}")
                    else:
                        print(f"       {k}: {v}")
            elif event.type == "tool_call_result":
                step += 1
                result = event.data.get("result") or ""
                print(f"Step {step}: Tool result from {event.data.get('tool')} (our backend ran the tool):")
                print(f"    → {result}")
            elif event.type == "ask_user":
                seen_ask_user = True
                step += 1
                print(f"Step {step}: OpenRouter asked the user: {event.data.get('question', '')[:80]!r}")
            elif event.type == "error":
                seen_error = True
                step += 1
                print(f"Step {step}: [ERROR] {event.data.get('message', '')[:250]}")
            elif event.type == "agent_message_start":
                step += 1
                print(f"Step {step}: OpenRouter responded (streaming text)...")
            elif event.type == "agent_message_end":
                if streamed_text:
                    print(f"    → OpenRouter streamed text: {''.join(streamed_text)!r}")
                print(f"         ...stream ended.")

            # Stop after we've seen a tool call or ask_user or error (enough to confirm agent works)
            if seen_tool_call or seen_ask_user or seen_error:
                if event.type in ("tool_call_result", "ask_user", "error"):
                    break
    except asyncio.CancelledError:
        print("  (cancelled)")
    except Exception as e:
        print(f"Step ?: [EXCEPTION] {e}")

    if streamed_text and not (seen_tool_call or seen_ask_user):
        print(f"    → OpenRouter streamed text: {''.join(streamed_text)!r}")

    print()
    print("-" * 60)
    if seen_tool_call or seen_ask_user:
        print("Done. OpenRouter successfully returned data and the agent used its tools.")
        print("Summary: OpenRouter chose the tool and sent the arguments above; our backend ran the tool and returned the result.")
        print("(Events seen: %d)" % event_count)
    elif seen_error:
        print("Done. Agent ran but hit an error – check message above and OPENROUTER_API_KEY / network.")
    else:
        print("Done. No tool/ask_user seen – OpenRouter may be slow or not calling tools. Check API key.")


if __name__ == "__main__":
    asyncio.run(main())
