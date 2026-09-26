"""
main.py
-------
Entry point for SnackStack.

Wraps the compiled LangGraph pipeline (graph.py) in a small, stateful
SnackStackAssistant class so callers interact with a plain chat()
method instead of dealing with thread_ids, graph.invoke() config, or
interrupt()/Command(resume=...) plumbing directly.
"""

import argparse
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph.types import Command

from graph import build_graph

logger = logging.getLogger("snackstack")


class SnackStackAssistant:
    """Stateful wrapper around the SnackStack LangGraph pipeline.

    Responsibilities:
      - Compile the graph in the requested dispatch mode ("parallel" or
        "sequential" -- see graph.py).
      - Own a thread_id so the MemorySaver checkpointer keeps multi-turn
        conversation memory across chat() calls.
      - Detect when a turn pauses on interrupt() (e.g. order_agent_node
        asking for a missing order ID/tracking ID/email), prompt for the
        missing information via input(), and resume the graph with
        Command(resume=answer) -- looping until the run completes, since
        a single query could in principle trigger more than one pause.

    NOTE: because this uses input()/print() directly, this ask()/chat()
    implementation is meant for a terminal/CLI context. For a web API or
    other non-terminal frontend, swap the input() call below for
    whatever collects the user's next message there (e.g. return the
    interrupt's question to the caller and let a follow-up request
    supply the answer, as an earlier version of this method did).
    """

    def __init__(self, mode: str = "parallel", thread_id: Optional[str] = None):
        """
        Args:
            mode: "parallel" (Command + Send fan-out) or "sequential"
                  (conditional-edge, one-agent-at-a-time routing).
            thread_id: reuse an existing conversation thread, or omit to
                       start a fresh one with a random id.
        """
        self.mode = mode
        self.graph = build_graph(mode=mode)
        self.thread_id = thread_id or str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}

    def chat(self, user_query: str) -> str:
        """Send one user message through the graph and return the
        assistant's final reply as plain text. Delegates to ask().
        """
        return self.ask(user_query)

    def ask(self, user_query: str) -> str:
        """Send one user message through the graph, resolving any
        interrupt() pause(s) synchronously before returning.

        Flow:
          1. Invoke the graph with the new user_query.
          2. Check graph.get_state() for a pending interrupt.
          3. While one is pending: print its question, collect the
             answer via input(), and resume with
             graph.invoke(Command(resume=answer), config=self.config).
          4. Once no interrupt remains, return final_response from state.
        """
        self.graph.invoke({"user_query": user_query}, config=self.config)
        snapshot = self.graph.get_state(self.config)

        while True:
            interrupt_payload = self._get_pending_interrupt(snapshot)
            if interrupt_payload is None:
                break

            question = interrupt_payload.get(
                "message", "I need a bit more information to continue."
            )
            answer = input(f"SnackStack: {question}\nYou: ").strip()

            self.graph.invoke(Command(resume=answer), config=self.config)
            snapshot = self.graph.get_state(self.config)

        return snapshot.values.get("final_response") or "Sorry, I couldn't come up with an answer."

    @staticmethod
    def _get_pending_interrupt(snapshot) -> Optional[Dict[str, Any]]:
        """Inspect a graph.get_state() StateSnapshot for a pending interrupt().

        When a node calls interrupt(), the graph halts before completing
        its superstep and snapshot.tasks contains a PregelTask for the
        paused node whose `.interrupts` attribute is a non-empty tuple of
        Interrupt objects. Each Interrupt's `.value` is exactly the
        payload that was passed to interrupt(...) inside the node.

        Returns that payload dict, or None if nothing is pending (i.e.
        the last run completed normally).
        """
        for task in snapshot.tasks:
            task_interrupts = getattr(task, "interrupts", None)
            if task_interrupts:
                return task_interrupts[0].value
        return None

    def get_history(self) -> List[Any]:
        """Return the accumulated LangChain message history (HumanMessage/
        AIMessage objects) for this assistant's conversation thread.
        """
        snapshot = self.graph.get_state(self.config)
        return snapshot.values.get("messages", [])

    def reset(self, thread_id: Optional[str] = None) -> str:
        """Start a brand-new conversation thread with fresh memory.

        Returns the new thread_id.
        """
        self.thread_id = thread_id or str(uuid.uuid4())
        self.config = {"configurable": {"thread_id": self.thread_id}}
        return self.thread_id


def run_text_loop(
    assistant: "SnackStackAssistant",
    voice_in: bool = False,
    voice_out: bool = False,
) -> None:
    """A simple REPL: read a line from stdin (or record from the mic if
    voice_in=True), send it to the assistant via ask(), print the reply
    (and speak it if voice_out=True), and log both sides of the exchange.

    Commands:
      quit / exit  -- end the session
      reset        -- start a brand-new conversation thread (fresh memory)

    voice/recorder.py and voice/speaker.py are imported lazily, only when
    voice_in/voice_out are actually requested, so text-only use of this
    file doesn't require the audio dependencies (sounddevice, soundfile,
    PortAudio) to be installed.
    """
    record_and_transcribe = None
    speak = None

    if voice_in:
        from voice.recorder import record_and_transcribe  # noqa: F401 (assigned above)

    if voice_out:
        from voice.speaker import speak  # noqa: F401 (assigned above)

    mode_notes = []
    if voice_in:
        mode_notes.append("voice input")
    if voice_out:
        mode_notes.append("voice output")
    mode_suffix = f" [{', '.join(mode_notes)}]" if mode_notes else ""

    print(
        f"SnackStack ready (mode={assistant.mode}, thread_id={assistant.thread_id}){mode_suffix}.\n"
        f"Type 'quit' to exit, 'reset' to start a new conversation."
        + (" Press Enter to start/stop recording your voice query." if voice_in else "")
        + "\n"
    )

    while True:
        try:
            if voice_in:
                user_input = record_and_transcribe(use_enter_to_stop=True).strip()
                if user_input:
                    print(f"You (voice): {user_input}")
            else:
                user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            logger.info("Session ended (EOF/KeyboardInterrupt).")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit"}:
            logger.info("Session ended by user command %r.", user_input)
            break

        if user_input.lower() == "reset":
            new_id = assistant.reset()
            logger.info("Conversation reset -- new thread_id=%s", new_id)
            print(f"(Started a new conversation: thread_id={new_id})\n")
            continue

        logger.info("User [thread=%s]: %s", assistant.thread_id, user_input)
        reply = assistant.ask(user_input)
        logger.info("Assistant [thread=%s]: %s", assistant.thread_id, reply)
        print(f"SnackStack: {reply}\n")

        if voice_out:
            try:
                speak(reply)
            except Exception as exc:  # keep the session alive if TTS/playback fails
                logger.warning("Voice output failed: %s", exc)
                print(f"(Voice playback failed: {exc})\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SnackStack multi-agent assistant (CLI)")
    parser.add_argument(
        "--mode",
        choices=["parallel", "sequential"],
        default=os.environ.get("SNACKSTACK_MODE", "parallel"),
        help="Agent dispatch strategy: parallel (Command+Send) or "
        "sequential (conditional edges). Default: parallel.",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Resume an existing conversation thread_id instead of "
        "starting a fresh one.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity for the session log. Default: INFO.",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Use the microphone for input instead of typing (records "
        "audio via voice/recorder.py, transcribed with OpenAI Whisper). "
        "Press Enter to start recording and Enter again to stop.",
    )
    parser.add_argument(
        "--voice-out",
        action="store_true",
        help="Speak the assistant's replies out loud via OpenAI TTS "
        "(voice/speaker.py) in addition to printing them.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    assistant = SnackStackAssistant(mode=args.mode, thread_id=args.thread_id)
    run_text_loop(assistant, voice_in=args.voice, voice_out=args.voice_out)


if __name__ == "__main__":
    main()
