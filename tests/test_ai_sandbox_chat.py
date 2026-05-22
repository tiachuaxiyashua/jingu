from __future__ import annotations

import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from jingu.ai.client import ChatClient, ChatResponse
from jingu.ai.config import AiConfig, load_ai_config
from jingu.cli import main
from jingu.runtime.errors import JinguRuntimeError
from jingu.sandbox.flow import (
    FlowWriter,
    format_readable_event,
    input_provenance_fields,
    tail_flow_events,
)
from jingu.sandbox.method import load_method_context
from jingu.sandbox.paths import latest_readable_log_pointer_path
from jingu.sandbox.runner import (
    AiSandboxChatSession,
    AiSandboxRunner,
    parse_acceptance_routing_judgment,
)


def write_method_file(base: Path, content: str | None = None) -> Path:
    path = base / "method.md"
    path.write_text(
        content
        or "\n".join(
            [
                "---",
                "name: test-method",
                "---",
                "# Test Method",
                "Use this method to preserve the original wish and produce evidence.",
            ]
        ),
        encoding="utf-8",
    )
    return path


def method_review_json(summary: str = "used method") -> str:
    return json.dumps(
        {
            "method_use_summary": summary,
            "evidence": ["method context was present"],
            "gaps": [],
            "observed_failure_modes": [],
            "method_update_candidates": [],
        },
        ensure_ascii=False,
    )


def split_proposals_json(proposals: list[dict] | None = None) -> str:
    return json.dumps({"proposals": proposals or []}, ensure_ascii=False)


def acceptance_continue_json(reason: str = "no routing child job needed") -> str:
    return json.dumps(
        {
            "route_action": "continue",
            "feedback_job_kind": "none",
            "feedback_job_summary": "",
            "required_context_gaps": [],
            "repair_instruction": "",
            "reason": reason,
            "evidence": ["candidate can continue without extra routing"],
        },
        ensure_ascii=False,
    )


def acceptance_feedback_json(
    *,
    kind: str = "directional",
    summary: str = "Clarify the next direction before continuing.",
    gaps: list[str] | None = None,
    reason: str = "the turn exposes a routing decision",
) -> str:
    return json.dumps(
        {
            "route_action": "feedback",
            "feedback_job_kind": kind,
            "feedback_job_summary": summary,
            "required_context_gaps": gaps or ["next direction"],
            "repair_instruction": "",
            "reason": reason,
            "evidence": ["routing evidence"],
        },
        ensure_ascii=False,
    )


def acceptance_repair_json(instruction: str = "Rewrite the candidate with the missing concrete detail.") -> str:
    return json.dumps(
        {
            "route_action": "repair",
            "feedback_job_kind": "none",
            "feedback_job_summary": "",
            "required_context_gaps": [],
            "repair_instruction": instruction,
            "reason": "the issue is repairable by the executor",
            "evidence": ["acceptance role found a repairable issue"],
        },
        ensure_ascii=False,
    )


class FakeChatClient:
    def __init__(self, content: str = "fake answer", responses: list[str] | None = None) -> None:
        self.content = content
        self.responses = responses
        self.messages: list[str] = []
        self.message_batches: list[list[dict[str, str]]] = []

    def complete(self, message: str) -> ChatResponse:
        self.messages.append(message)
        return ChatResponse(content=self.content, raw={"ok": True})

    def complete_messages(self, messages: list[dict[str, str]], **kwargs) -> ChatResponse:
        self.message_batches.append(messages)
        self.messages.append(messages[-1]["content"])
        if self.responses:
            index = len(self.message_batches) - 1
            content = self.responses[index] if index < len(self.responses) else self.responses[-1]
            return ChatResponse(content=content, raw={"ok": True})
        system_text = "\n".join(
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        )
        latest_payload = messages[-1].get("content", "") if messages else ""
        if "分业申请提议位" in system_text or "available_method_catalog" in latest_payload:
            return ChatResponse(content=split_proposals_json(), raw={"ok": True})
        if "验收路由位" in system_text or "routing_contract" in latest_payload:
            return ChatResponse(content=acceptance_continue_json(), raw={"ok": True})
        if "feedback job" in system_text:
            return ChatResponse(
                content=json.dumps(
                    {
                        "needs_feedback_job": False,
                        "feedback_job_kind": "none",
                        "feedback_job_summary": "",
                        "required_context_gaps": [],
                        "reason": "no feedback job needed",
                    },
                    ensure_ascii=False,
                ),
                raw={"ok": True},
            )
        return ChatResponse(content=self.content, raw={"ok": True})


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
                        "DEEPSEEK_STREAM_IDLE_TIMEOUT_SECONDS=34",
                        'DEEPSEEK_EXTRA_BODY_JSON={"custom_provider_option":"enabled"}',
                    ]
                ),
                encoding="utf-8",
            )

            config = load_ai_config(path)

            self.assertEqual(config.api_key, "local-key")
            self.assertEqual(config.base_url, "local-provider")
            self.assertEqual(config.model, "local-model")
            self.assertEqual(config.timeout_seconds, 12.0)
            self.assertTrue(config.stream)
            self.assertEqual(config.stream_idle_timeout_seconds, 34.0)
            self.assertEqual(config.extra_body, {"custom_provider_option": "enabled"})

    def test_ai_config_rejects_extra_body_runtime_overrides(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deepseek.local"
            path.write_text(
                "\n".join(
                    [
                        "DEEPSEEK_API_KEY=local-key",
                        "DEEPSEEK_BASE_URL=local-provider",
                        "DEEPSEEK_MODEL=local-model",
                        'DEEPSEEK_EXTRA_BODY_JSON={"stream":false}',
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaises(JinguRuntimeError):
                load_ai_config(path)

    def test_chat_client_streams_reasoning_and_content_deltas(self) -> None:
        class FakeStreamingResponse:
            def __init__(self) -> None:
                self.lines = iter(
                    [
                        b'data: {"choices":[{"delta":{"reasoning_content":"think "}}]}\n',
                        b'data: {"choices":[{"delta":{"content":"answer"}}]}\n',
                        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
                        b"data: [DONE]\n",
                        b"",
                    ]
                )

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def readline(self):
                return next(self.lines)

        captured = {}

        def fake_urlopen(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeStreamingResponse()

        config = AiConfig(
            api_key="local-key",
            base_url="https:" + "//provider.example",
            model="local-model",
            timeout_seconds=12,
            stream=True,
            stream_idle_timeout_seconds=34,
            extra_body={"custom_provider_option": "enabled"},
        )
        events = []
        with patch("urllib.request.urlopen", fake_urlopen):
            response = ChatClient(config).complete_messages(
                [{"role": "user", "content": "hello"}],
                on_stream_event=events.append,
            )

        self.assertEqual(response.content, "answer")
        self.assertEqual(response.reasoning_content, "think ")
        self.assertEqual(captured["timeout"], 34)
        self.assertTrue(captured["body"]["stream"])
        self.assertEqual(captured["body"]["custom_provider_option"], "enabled")
        self.assertEqual(
            [event["event"] for event in events],
            ["stream_delta", "stream_delta", "stream_finished"],
        )
        self.assertEqual(events[0]["provider_delta_kind"], "reasoning")
        self.assertEqual(events[1]["provider_delta_kind"], "content")

    def test_missing_ai_config_fails_before_provider_request(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deepseek.local"
            path.write_text("DEEPSEEK_API_KEY=local-key\n", encoding="utf-8")

            with self.assertRaises(JinguRuntimeError):
                load_ai_config(path)

    def test_method_context_loads_from_repository_pointer(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            method_path = write_method_file(workspace)
            (workspace / "jingu-method-source.txt").write_text(
                method_path.name,
                encoding="utf-8",
            )

            method = load_method_context(workspace=workspace)

            self.assertEqual(method.name, "test-method")
            self.assertEqual(method.path, method_path.resolve())
            self.assertIn("original wish", method.content)
            self.assertGreaterEqual(len(method.fragments), 1)
            self.assertIn("Test Method", method.fragments[0].content)

    def test_runner_returns_answer_and_deletes_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient("answer only")

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("hello")

            self.assertEqual(answer, "answer only")
            self.assertFalse(sandbox.exists())
            self.assertEqual(client.messages[0], "hello")
            first_batch = client.message_batches[0]
            self.assertGreaterEqual(len(first_batch), 3)
            self.assertIn("Method manifest", first_batch[0]["content"])
            self.assertIn("Method law id", first_batch[1]["content"])
            self.assertIn("Method law content", first_batch[1]["content"])
            self.assertNotIn("Method content:", first_batch[0]["content"])
            self.assertIn("Test Method", first_batch[0]["content"])

    def test_runner_persists_diagnostic_log_with_input_and_output(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient("diagnostic answer")

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("diagnostic input")

            log_files = sorted(log_dir.glob("ai-run-*.jsonl"))
            self.assertEqual(len(log_files), 1)
            readable_files = sorted(log_dir.glob("ai-run-*.md"))
            self.assertEqual(len(readable_files), 1)
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
            self.assertIn("job_tree_management_recorded", event_types)
            self.assertIn("job_tree_snapshot_recorded", event_types)
            self.assertIn("process_step_recorded", event_types)
            self.assertIn("input_provenance_recorded", event_types)
            self.assertIn("provider_messages_recorded", event_types)
            self.assertIn("method_law_fragment_loaded", event_types)
            self.assertIn("method_law_fragment_bound", event_types)
            self.assertIn("method_call_frame_opened", event_types)
            self.assertIn("split_proposal_requested", event_types)
            self.assertIn("split_proposal_received", event_types)
            self.assertIn("split_proposal_skipped", event_types)
            self.assertIn("verification_job_created", event_types)
            self.assertIn("verification_tool_started", event_types)
            self.assertIn("verification_result_recorded", event_types)
            self.assertIn("verification_evidence_submitted", event_types)
            self.assertIn("parent_verification_evidence_submitted", event_types)
            self.assertIn("acceptance_routing_requested", event_types)
            self.assertIn("acceptance_routing_received", event_types)
            self.assertIn("acceptance_routing_evidence_submitted", event_types)
            self.assertIn("acceptance_routing_skipped", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("diagnostic input", serialized)
            self.assertIn("diagnostic answer", serialized)
            self.assertIn("candidate_attached", serialized)
            self.assertIn("verification_child_created", serialized)
            self.assertIn("candidate_verification_report", serialized)
            self.assertIn("candidate_verification_summary", serialized)
            self.assertIn("acceptance_routing_judgment", serialized)
            self.assertIn("acceptance_routing_evidence", serialized)
            self.assertIn("does_not_auto_accept_or_reject", serialized)
            self.assertIn("tree_snapshot", serialized)
            provenance = next(
                record for record in records if record["event_type"] == "input_provenance_recorded"
            )
            self.assertEqual(provenance["data"]["input_source"], "ai_run_message")
            self.assertEqual(provenance["data"]["input_character_count"], str(len("diagnostic input")))
            self.assertEqual(provenance["data"]["input_line_count"], "1")
            self.assertEqual(provenance["data"]["input_has_markdown_heading"], "false")
            self.assertEqual(provenance["data"]["input_has_fenced_block"], "false")
            self.assertIn("input_sha256", provenance["data"])
            process_steps = [
                record["data"]["process_step"]
                for record in records
                if record["event_type"] == "process_step_recorded"
            ]
            self.assertIn("input.record", process_steps)
            self.assertIn("method.load", process_steps)
            self.assertIn("provider.request", process_steps)
            self.assertIn("candidate.submit", process_steps)
            self.assertIn("evidence.submit", process_steps)
            self.assertIn("candidate.verify.create", process_steps)
            self.assertIn("candidate.verify.run", process_steps)
            self.assertIn("candidate.verify.result", process_steps)
            self.assertIn("candidate.verify.evidence", process_steps)
            self.assertIn("candidate.verify.parent_evidence", process_steps)
            self.assertIn("candidate.verify.acceptance_route.request", process_steps)
            self.assertIn("candidate.verify.acceptance_route.receive", process_steps)
            self.assertIn("candidate.verify.acceptance_route.evidence", process_steps)
            self.assertIn("candidate.verify.acceptance_route.continue", process_steps)
            self.assertIn("output.record", process_steps)
            provider_messages = [
                record for record in records if record["event_type"] == "provider_messages_recorded"
            ]
            self.assertEqual(
                [record["data"]["provider_call_kind"] for record in provider_messages],
                [
                    "candidate_generation",
                    "method_self_review",
                    "split_proposal_extraction",
                    "acceptance_routing",
                ],
            )
            self.assertIn("system,user", provider_messages[0]["data"]["provider_message_roles"])
            self.assertIn("Test Method", provider_messages[0]["data"]["provider_messages"])
            self.assertIn("diagnostic input", provider_messages[0]["data"]["provider_messages"])
            self.assertIn("method_context_loaded", event_types)
            self.assertIn("method_context_injected", event_types)
            self.assertIn("method_self_review_received", event_types)
            self.assertIn("method_update_candidate_recorded", event_types)
            self.assertIn("split_proposal_extraction", serialized)
            self.assertIn("method_law_fragment_count", serialized)
            self.assertIn("method_law_appearance_refs", serialized)
            self.assertIn("method_call_frame", serialized)
            self.assertIn("Test Method", serialized)
            self.assertNotIn("local-key", serialized)
            self.assertNotIn("Authorization", serialized)
            readable_text = readable_files[0].read_text(encoding="utf-8-sig")
            self.assertIn("金箍 AI 沙盒可读日志", readable_text)
            self.assertIn(str(log_files[0]), readable_text)
            self.assertIn("diagnostic input", readable_text)
            self.assertIn("diagnostic answer", readable_text)
            self.assertIn("Test Method", readable_text)
            self.assertIn("输入内容（input）", readable_text)
            self.assertIn("法片段内容（method_law_content）", readable_text)
            self.assertIn("法片段清单（method_law_manifest）", readable_text)
            self.assertIn("法片段已绑定（method_law_fragment_bound）", readable_text)
            self.assertIn("法调用帧已打开（method_call_frame_opened）", readable_text)
            self.assertIn("法调用帧（method_call_frame）", readable_text)
            self.assertIn("分业申请已请求（split_proposal_requested）", readable_text)
            self.assertIn("分业登记已跳过（split_proposal_skipped）", readable_text)
            self.assertIn("业树快照（tree_snapshot）", readable_text)
            self.assertIn("候选结果已挂载（candidate_attached）", readable_text)
            self.assertIn("运行步骤已记录（process_step_recorded）", readable_text)
            self.assertIn("输入来源已记录（input_provenance_recorded）", readable_text)
            self.assertIn("输入来源（input_source）: ai_run_message", readable_text)
            self.assertIn("输入 SHA-256（input_sha256）", readable_text)
            self.assertIn("Provider 请求消息已记录（provider_messages_recorded）", readable_text)
            self.assertIn("Provider 请求消息（provider_messages）", readable_text)
            self.assertIn("候选校验业已创建（verification_job_created）", readable_text)
            self.assertIn("候选校验结果已记录（verification_result_recorded）", readable_text)
            self.assertIn("父业校验证据已回流（parent_verification_evidence_submitted）", readable_text)
            self.assertIn("验收路由已请求（acceptance_routing_requested）", readable_text)
            self.assertIn("验收路由已收到（acceptance_routing_received）", readable_text)
            self.assertIn("验收路由证据已提交（acceptance_routing_evidence_submitted）", readable_text)
            self.assertIn("校验报告（verification_report）", readable_text)
            self.assertIn("校验子业已创建（verification_child_created）", readable_text)
            self.assertTrue(latest_readable_log_pointer_path(log_dir).exists())

    def test_runner_registers_ai_split_proposals_through_gatekeeper(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            child_method = workspace / ".agents" / "skills" / "child-method" / "SKILL.md"
            child_method.parent.mkdir(parents=True)
            child_method.write_text(
                "\n".join(
                    [
                        "---",
                        "name: child-method",
                        "description: Child method for split registration tests.",
                        "---",
                        "# Child Method",
                        "Produce a local child result package.",
                    ]
                ),
                encoding="utf-8",
            )
            split_payload = split_proposals_json(
                [
                    {
                        "target": "make protagonist vivid",
                        "blocking_reason": "parent cannot continue without a protagonist card",
                        "output_contract": "protagonist card with evidence",
                        "acceptance_criteria": "card has traits and scene evidence",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "this child needs the selected local method",
                        "method_return_point": "return protagonist card to parent",
                    },
                    {
                        "target": "unknown method child",
                        "blocking_reason": "parent cannot validate unknown method behavior",
                        "output_contract": "should be rejected",
                        "acceptance_criteria": "unknown method must not create child",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": str(workspace / "missing-method.md"),
                        "method_binding_reason": "bad method reference",
                        "method_return_point": "return nowhere",
                    },
                ]
            )
            client = FakeChatClient(
                responses=[
                    "candidate that needs a protagonist child job",
                    method_review_json("checked method use"),
                    split_payload,
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Use the method and split blocked story work into child jobs.")

            self.assertEqual(answer, "candidate that needs a protagonist child job")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("split_proposal_accepted"), 1)
            self.assertEqual(event_types.count("split_proposal_rejected"), 1)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("child-method", serialized)
            self.assertIn("make protagonist vivid", serialized)
            self.assertIn("split proposal method is not in catalog", serialized)
            self.assertIn("split_proposal_child_created", serialized)
            self.assertIn("method_call_frames", serialized)
            readable_text = next(log_dir.glob("ai-run-*.md")).read_text(encoding="utf-8-sig")
            self.assertIn("分业申请已登记（split_proposal_accepted）", readable_text)
            self.assertIn("分业申请已拒绝（split_proposal_rejected）", readable_text)

    def test_runner_repairs_failed_verification_candidate(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            short_candidate = "字" * 2600
            repaired_candidate = "字" * 4500
            client = FakeChatClient(
                responses=[
                    short_candidate,
                    method_review_json("checked method use"),
                    split_proposals_json(),
                    repaired_candidate,
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_repair_attempts=1,
            ).run("请输出4500到6000汉字。")

            self.assertEqual(answer, repaired_candidate)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("repair_job_created"), 1)
            self.assertEqual(event_types.count("repair_candidate_submitted"), 1)
            self.assertEqual(event_types.count("verification_job_created"), 2)
            self.assertIn("repair_loop_finished", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("candidate_repair", serialized)
            self.assertIn("candidate_repair_loop_summary", serialized)
            self.assertIn("repair_child_created", serialized)
            self.assertIn("verification_passed", serialized)
            self.assertIn("acceptance_routing_requested", event_types)
            self.assertIn("acceptance_routing_skipped", event_types)
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)

    def test_runner_creates_feedback_decision_job_when_repair_is_exhausted(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            short_candidate = "字" * 2600
            still_short_candidate = "字" * 2700
            client = FakeChatClient(
                responses=[
                    short_candidate,
                    method_review_json("checked method use"),
                    split_proposals_json(),
                    still_short_candidate,
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_repair_attempts=1,
            ).run("请输出4500到6000汉字。")

            self.assertEqual(answer, still_short_candidate)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("repair_job_created"), 1)
            self.assertEqual(event_types.count("verification_feedback_job_created"), 1)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("attempt_limit_exhausted", serialized)
            self.assertIn("verification_feedback_child_created", serialized)
            self.assertIn("verification_feedback_decision_context", serialized)
            self.assertIn("acceptance_routing_requested", event_types)
            self.assertIn("acceptance_routing_skipped", event_types)
            self.assertIn("does_not_auto_accept_or_reject", serialized)
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)

    def test_runner_acceptance_router_creates_feedback_job(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient(
                responses=[
                    "candidate with a visible direction question",
                    method_review_json("checked method use"),
                    split_proposals_json(),
                    acceptance_feedback_json(
                        kind="high_value",
                        summary="Expose the unresolved direction before continuing.",
                        gaps=["direction choice"],
                        reason="the candidate changes the direction of the work",
                    ),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Produce a candidate and surface important unresolved direction choices.")

            self.assertEqual(answer, "candidate with a visible direction question")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("acceptance_routing_requested"), 1)
            self.assertEqual(event_types.count("acceptance_routing_received"), 1)
            self.assertEqual(event_types.count("feedback_job_created"), 1)
            self.assertNotIn("acceptance_routing_skipped", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("high_value", serialized)
            self.assertIn("Expose the unresolved direction before continuing.", serialized)
            self.assertIn("acceptance_routing_judgment", serialized)
            self.assertIn("acceptance_routing_evidence", serialized)
            self.assertIn("does_not_auto_accept_or_reject", serialized)
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)

    def test_runner_acceptance_router_creates_executor_repair(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient(
                responses=[
                    "draft candidate",
                    method_review_json("checked method use"),
                    split_proposals_json(),
                    acceptance_repair_json("Add the missing concrete evidence and return the full result."),
                    "repaired candidate",
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Produce a candidate that can be revised if acceptance finds a repairable issue.")

            self.assertEqual(answer, "repaired candidate")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("acceptance_routing_requested"), 1)
            self.assertEqual(event_types.count("repair_job_created"), 1)
            self.assertEqual(event_types.count("repair_candidate_submitted"), 1)
            self.assertEqual(event_types.count("verification_job_created"), 2)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("acceptance_routing", serialized)
            self.assertIn("acceptance_repair", serialized)
            self.assertIn("Add the missing concrete evidence", serialized)
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)

    def test_acceptance_routing_normalizes_text_evidence(self) -> None:
        judgment = parse_acceptance_routing_judgment(
            json.dumps(
                {
                    "route_action": "feedback",
                    "feedback_job_kind": "high_value",
                    "feedback_job_summary": "Expose the unresolved human direction choice.",
                    "required_context_gaps": [],
                    "repair_instruction": "",
                    "reason": "candidate contains an unresolved owner decision",
                    "evidence": "candidate names the unresolved direction and does not decide it",
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(
            judgment["evidence"],
            ["candidate names the unresolved direction and does not decide it"],
        )
        self.assertTrue(judgment["does_not_auto_accept_or_reject"])

    def test_runner_preserves_existing_saved_logs_in_log_dir(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            old_log = log_dir / "ai-run-existing.jsonl"
            old_readable = log_dir / "ai-run-existing.md"
            log_dir.mkdir()
            old_log.write_text("old-jsonl\n", encoding="utf-8")
            old_readable.write_text("old-readable\n", encoding="utf-8")

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=FakeChatClient("first answer"),
            ).run("first input")
            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=FakeChatClient("second answer"),
            ).run("second input")

            self.assertEqual(old_log.read_text(encoding="utf-8"), "old-jsonl\n")
            self.assertEqual(old_readable.read_text(encoding="utf-8"), "old-readable\n")
            self.assertGreaterEqual(len(list(log_dir.glob("ai-run-*.jsonl"))), 3)
            self.assertGreaterEqual(len(list(log_dir.glob("ai-run-*.md"))), 3)

    def test_runner_fails_before_provider_when_method_is_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            client = FakeChatClient("should not be called")

            with self.assertRaises(JinguRuntimeError):
                AiSandboxRunner(
                    sandbox_path=sandbox,
                    log_dir=log_dir,
                    method_path=Path(tmp) / "missing-method.md",
                    client=client,
                ).run("hello")

            self.assertEqual(client.message_batches, [])
            self.assertFalse(sandbox.exists())

    def test_readable_log_preserves_chinese_text(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(
                Path(tmp),
                "\n".join(
                    [
                        "---",
                        "name: 中文方法",
                        "---",
                        "# 中文方法",
                        "保留中文输入、输出和自验。",
                    ]
                ),
            )
            client = FakeChatClient("中文回答已保存。")

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("验证中文日志是否正常显示。")

            readable_files = sorted(log_dir.glob("ai-run-*.md"))
            self.assertEqual(len(readable_files), 1)
            readable_text = readable_files[0].read_text(encoding="utf-8-sig")
            self.assertIn("验证中文日志是否正常显示。", readable_text)
            self.assertIn("中文回答已保存。", readable_text)
            self.assertIn("中文方法", readable_text)

    def test_flow_tail_reads_written_events(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            sandbox.mkdir()
            writer = FlowWriter(sandbox)
            writer.write("sandbox_created", "sandbox created")
            writer.write("run_finished", "run finished")

            events = list(tail_flow_events(sandbox, wait_seconds=0.1))

            self.assertEqual([event["event_type"] for event in events], ["sandbox_created", "run_finished"])

    def test_input_provenance_flags_embedded_markdown_without_domain_assumptions(self) -> None:
        text = "# 标题\n\n正文\n```text\n片段\n```"

        fields = input_provenance_fields(text, input_source="manual-test")

        self.assertEqual(fields["input_source"], "manual-test")
        self.assertEqual(fields["input_character_count"], str(len(text)))
        self.assertEqual(fields["input_line_count"], "6")
        self.assertEqual(fields["input_has_markdown_heading"], "true")
        self.assertEqual(fields["input_has_fenced_block"], "true")
        self.assertEqual(len(fields["input_sha256"]), 64)

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
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient(
                responses=[
                    "chat answer 1",
                    method_review_json(),
                    split_proposals_json(),
                    "```json\n"
                    + acceptance_feedback_json(
                        summary="Clarify the next direction before continuing.",
                        gaps=["next direction"],
                        reason="the turn needs direction before more work",
                    )
                    + "\n```",
                    "chat answer 2",
                    method_review_json("used method again"),
                    split_proposals_json(),
                    acceptance_continue_json("the answer can continue as a normal conversation"),
                ]
            )
            session = AiSandboxChatSession(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            )

            session.start()
            first = session.ask("first task")
            feedback_job_id = session.last_feedback_job_id
            self.assertIsNotNone(feedback_job_id)
            self.assertIsNotNone(session.service)
            assert feedback_job_id is not None
            assert session.service is not None
            assert session.last_job_id is not None
            first_job_events = session.service.list_events(session.last_job_id)
            self.assertIn(
                "method_law_bound",
                [event["event_type"] for event in first_job_events],
            )
            feedback_job = session.service.get_status(feedback_job_id)
            self.assertEqual(feedback_job["target"], "Clarify the next direction before continuing.")
            second = session.ask("second decision")
            self.assertIsNone(session.last_feedback_job_id)
            session.finish()

            self.assertEqual(first, "chat answer 1")
            self.assertEqual(second, "chat answer 2")
            self.assertFalse(sandbox.exists())
            log_files = sorted(log_dir.glob("ai-run-*.jsonl"))
            records = [
                json.loads(line)
                for line in log_files[0].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("user_input_recorded"), 2)
            self.assertEqual(event_types.count("input_provenance_recorded"), 2)
            self.assertEqual(event_types.count("method_context_loaded"), 2)
            self.assertEqual(event_types.count("method_context_injected"), 2)
            self.assertEqual(event_types.count("method_law_fragment_bound"), 2)
            self.assertEqual(event_types.count("method_self_review_requested"), 2)
            self.assertEqual(event_types.count("method_self_review_received"), 2)
            self.assertEqual(event_types.count("method_update_candidate_recorded"), 2)
            self.assertEqual(event_types.count("split_proposal_requested"), 2)
            self.assertEqual(event_types.count("split_proposal_received"), 2)
            self.assertEqual(event_types.count("split_proposal_skipped"), 2)
            self.assertEqual(event_types.count("result_output_recorded"), 2)
            self.assertEqual(event_types.count("candidate_submitted"), 2)
            self.assertEqual(event_types.count("evidence_submitted"), 3)
            self.assertEqual(event_types.count("verification_job_created"), 2)
            self.assertEqual(event_types.count("verification_tool_started"), 2)
            self.assertEqual(event_types.count("verification_result_recorded"), 2)
            self.assertEqual(event_types.count("verification_evidence_submitted"), 2)
            self.assertEqual(event_types.count("parent_verification_evidence_submitted"), 2)
            self.assertEqual(event_types.count("acceptance_routing_requested"), 2)
            self.assertEqual(event_types.count("acceptance_routing_received"), 2)
            self.assertEqual(event_types.count("acceptance_routing_evidence_submitted"), 2)
            self.assertEqual(event_types.count("feedback_job_created"), 1)
            self.assertEqual(event_types.count("acceptance_routing_skipped"), 1)
            self.assertEqual(event_types.count("provider_messages_recorded"), 8)
            self.assertGreaterEqual(event_types.count("process_step_recorded"), 20)
            self.assertGreaterEqual(event_types.count("job_tree_management_recorded"), 12)
            self.assertGreaterEqual(event_types.count("job_tree_snapshot_recorded"), 12)
            self.assertNotIn("human_verdict_requested", event_types)
            self.assertNotIn("human_verdict_recorded", event_types)
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)
            self.assertNotIn("feedback_judgment_requested", event_types)
            self.assertNotIn("feedback_judgment_received", event_types)
            self.assertIn("chat_session_finished", event_types)
            tree_actions = [
                record["data"]["job_tree_action"]
                for record in records
                if record["event_type"] == "job_tree_management_recorded"
            ]
            self.assertIn("feedback_child_created", tree_actions)
            self.assertIn("split_proposal_skipped", tree_actions)
            self.assertIn("acceptance_route_continued", tree_actions)
            self.assertIn("verification_child_created", tree_actions)
            self.assertIn("verification_candidate_attached", tree_actions)
            self.assertIn("verification_evidence_attached", tree_actions)
            self.assertIn("parent_verification_evidence_attached", tree_actions)
            tree_snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            verification_child_ids = [
                record["data"]["verification_job_id"]
                for record in records
                if record["event_type"] == "verification_job_created"
            ]
            self.assertTrue(verification_child_ids)
            self.assertTrue(
                any(
                    link["child_job_id"] == feedback_job_id
                    for snapshot in tree_snapshots
                    for link in snapshot["links"]
                )
            )
            self.assertTrue(
                any(
                    link["child_job_id"] in verification_child_ids
                    for snapshot in tree_snapshots
                    for link in snapshot["links"]
                )
            )

    def test_chat_acceptance_repair_updates_followup_history(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            client = FakeChatClient(
                responses=[
                    "draft chat candidate",
                    method_review_json(),
                    split_proposals_json(),
                    acceptance_repair_json("Return a repaired assistant answer."),
                    "repaired chat candidate",
                    "follow-up answer",
                    method_review_json("used method again"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )
            session = AiSandboxChatSession(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            )

            session.start()
            first = session.ask("first task")
            second = session.ask("second task")
            session.finish()

            self.assertEqual(first, "repaired chat candidate")
            self.assertEqual(second, "follow-up answer")
            candidate_batches = [
                batch
                for batch in client.message_batches
                if batch[-1].get("content") in {"first task", "second task"}
            ]
            self.assertEqual(len(candidate_batches), 2)
            second_generation_text = json.dumps(candidate_batches[1], ensure_ascii=False)
            self.assertIn("repaired chat candidate", second_generation_text)
            self.assertNotIn("draft chat candidate", second_generation_text)

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("repair_job_created"), 1)
            self.assertIn("acceptance_routing_received", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("acceptance_repair", serialized)

    def test_launcher_dry_run_prints_method_source(self) -> None:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts\\run_ai_sandbox.ps1",
                "-DryRun",
            ],
            check=True,
            text=True,
            capture_output=True,
        )

        self.assertIn("--method", completed.stdout)
        self.assertIn("Method:", completed.stdout)
        self.assertIn("Readable pointer:", completed.stdout)
        self.assertIn("InputEncoding", completed.stdout)
        self.assertIn("PYTHONIOENCODING", completed.stdout)

    def test_readable_event_format_blocks_long_fields(self) -> None:
        event = {
            "timestamp": "2026-05-17T10:00:00+00:00",
            "event_type": "method_context_loaded",
            "message": "method context loaded",
            "data": {
                "method_name": "test-method",
                "method_law_content": "line 1\nline 2",
                "result": "x" * 140,
            },
        }

        rendered = format_readable_event(event)

        self.assertIn("## 2026-05-17T10:00:00+00:00 | 方法上下文已加载（method_context_loaded）", rendered)
        self.assertIn("### 法片段内容（method_law_content）", rendered)
        self.assertIn("```text", rendered)
        self.assertIn("line 1", rendered)
        self.assertIn("- 方法名称（method_name）: test-method", rendered)

    def test_readable_event_translates_job_tree_action(self) -> None:
        rendered = format_readable_event(
            {
                "timestamp": "2026-05-17T10:00:00+00:00",
                "event_type": "job_tree_management_recorded",
                "message": "job tree management recorded",
                "data": {
                    "job_tree_action": "feedback_child_created",
                    "child_job_id": "job_child",
                },
            }
        )

        self.assertIn("业树管理已记录（job_tree_management_recorded）", rendered)
        self.assertIn("反馈子业已创建（feedback_child_created）", rendered)
        self.assertIn("子业编号（child_job_id）: job_child", rendered)

    def test_readable_event_warns_about_question_mark_encoding_damage(self) -> None:
        rendered = format_readable_event(
            {
                "timestamp": "2026-05-17T10:00:00+00:00",
                "event_type": "user_input_recorded",
                "message": "user input recorded",
                "data": {"input": "????????????"},
            }
        )

        self.assertIn("用户输入已记录（user_input_recorded）", rendered)
        self.assertIn("输入内容（input）", rendered)
        self.assertIn("编码警告", rendered)


if __name__ == "__main__":
    unittest.main()
