from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jingu.ai.client import ChatResponse
from jingu.ai.config import load_ai_config
from jingu.cli import main
from jingu.runtime.errors import JinguRuntimeError
from jingu.sandbox.flow import FlowWriter, tail_flow_events
from jingu.sandbox.runner import AiSandboxChatSession, AiSandboxRunner


class FakeChatClient:
    def __init__(self, content: str = "fake answer") -> None:
        self.content = content
        self.messages: list[str] = []

    def complete(self, message: str) -> ChatResponse:
        self.messages.append(message)
        return ChatResponse(content=self.content, raw={"ok": True})

    def complete_messages(self, messages: list[dict[str, str]]) -> ChatResponse:
        self.messages.append(messages[-1]["content"])
        return ChatResponse(content=f"{self.content} {len(messages)}", raw={"ok": True})


class AiSandboxChatTest(unittest.TestCase):
    def test_load_ai_config_from_local_file(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deepseek.local"
            path.write_text(
                "\n".join(
                    [
                        "DEEPSEEK_API_KEY=local-key",
                        "DEEPSEEK_BASE_URL=local-provider",
                        "DEEPSEEK_MODEL=local-model",
                        "DEEPSEEK_TIMEOUT_SECONDS=12",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_ai_config(path)

            self.assertEqual(config.api_key, "local-key")
            self.assertEqual(config.base_url, "local-provider")
            self.assertEqual(config.model, "local-model")
            self.assertEqual(config.timeout_seconds, 12.0)

    def test_missing_ai_config_fails_before_provider_request(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deepseek.local"
            path.write_text("DEEPSEEK_API_KEY=local-key\n", encoding="utf-8")

            with self.assertRaises(JinguRuntimeError):
                load_ai_config(path)

    def test_runner_returns_answer_and_deletes_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            client = FakeChatClient("answer only")

            answer = AiSandboxRunner(sandbox_path=sandbox, log_dir=log_dir, client=client).run("hello")

            self.assertEqual(answer, "answer only")
            self.assertFalse(sandbox.exists())
            self.assertEqual(client.messages, ["hello"])

    def test_runner_persists_diagnostic_log_with_input_and_output(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            client = FakeChatClient("diagnostic answer")

            AiSandboxRunner(sandbox_path=sandbox, log_dir=log_dir, client=client).run("diagnostic input")

            log_files = sorted(log_dir.glob("ai-run-*.jsonl"))
            self.assertEqual(len(log_files), 1)
            self.assertFalse(sandbox.exists())
            records = [
                json.loads(line)
                for line in log_files[0].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("user_input_recorded", event_types)
            self.assertIn("result_output_recorded", event_types)
            self.assertIn("sandbox_destroyed", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("diagnostic input", serialized)
            self.assertIn("diagnostic answer", serialized)
            self.assertNotIn("local-key", serialized)
            self.assertNotIn("Authorization", serialized)

    def test_flow_tail_reads_written_events(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            sandbox.mkdir()
            writer = FlowWriter(sandbox)
            writer.write("sandbox_created", "sandbox created")
            writer.write("run_finished", "run finished")

            events = list(tail_flow_events(sandbox, wait_seconds=0.1))

            self.assertEqual([event["event_type"] for event in events], ["sandbox_created", "run_finished"])

    def test_ai_run_cli_prints_only_answer(self) -> None:
        class FakeRunner:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def run(self, message: str) -> str:
                self.message = message
                return "answer only"

        output = StringIO()
        with patch("jingu.cli.AiSandboxRunner", FakeRunner), redirect_stdout(output):
            code = main(["ai", "run", "--message", "hello"])

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "answer only\n")

    def test_interactive_chat_session_keeps_context_and_cleans_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            client = FakeChatClient("chat answer")
            session = AiSandboxChatSession(sandbox_path=sandbox, log_dir=log_dir, client=client)

            session.start()
            first = session.ask("first task")
            second = session.ask("second decision")
            session.finish()

            self.assertEqual(first, "chat answer 1")
            self.assertEqual(second, "chat answer 3")
            self.assertFalse(sandbox.exists())
            log_files = sorted(log_dir.glob("ai-run-*.jsonl"))
            records = [
                json.loads(line)
                for line in log_files[0].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("user_input_recorded"), 2)
            self.assertEqual(event_types.count("result_output_recorded"), 2)
            self.assertIn("chat_session_finished", event_types)


if __name__ == "__main__":
    unittest.main()
