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
    normalize_split_proposal,
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


def default_split_law(**overrides: object) -> dict:
    law = {
        "blocks_parent_execution": True,
        "blocks_parent_acceptance": False,
        "needs_distinct_capability": False,
        "has_independent_result_package": True,
        "has_high_value_or_risk": False,
        "reason": "parent cannot continue without the child result package",
    }
    law.update(overrides)
    return law


def split_proposals_json(proposals: list[dict] | None = None) -> str:
    enriched = []
    for proposal in proposals or []:
        item = {**proposal}
        item.setdefault("delivery_relation", "does_not_advance_quantitative_delivery")
        item.setdefault("split_law", default_split_law())
        enriched.append(item)
    return json.dumps({"proposals": enriched}, ensure_ascii=False)


def child_result_package_json(
    *,
    conclusion: str = "child conclusion",
    artifacts: list[str] | None = None,
    delivery_contributions: list[dict] | None = None,
    evidence_summary: str = "child evidence summary",
    open_questions: list[str] | None = None,
    suggested_follow_up_jobs: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "conclusion": conclusion,
            "artifacts": artifacts or ["child artifact"],
            "delivery_contributions": delivery_contributions or [],
            "evidence_summary": evidence_summary,
            "open_questions": open_questions or [],
            "suggested_follow_up_jobs": suggested_follow_up_jobs or [],
        },
        ensure_ascii=False,
    )


def child_package_review_accept_json(
    *,
    reason: str = "package satisfies the child contract",
    parent_consumption_summary: str = "parent can consume the accepted child package",
) -> str:
    return json.dumps(
        {
            "review_action": "accept",
            "checks": [
                {
                    "check_id": "contract",
                    "criterion": "package satisfies child acceptance criteria",
                    "status": "passed",
                    "evidence": "package has conclusion, artifacts, and evidence summary",
                }
            ],
            "evidence": ["independent review found the package consumable"],
            "reason": reason,
            "repair_instruction": "",
            "parent_consumption_summary": parent_consumption_summary,
        },
        ensure_ascii=False,
    )


def child_package_review_repair_json(
    instruction: str = "Add measurable evidence before the parent consumes this package.",
) -> str:
    return json.dumps(
        {
            "review_action": "repair",
            "checks": [
                {
                    "check_id": "measurable_evidence",
                    "criterion": "package includes measurable evidence",
                    "status": "failed",
                    "evidence": "package evidence is not measurable enough",
                }
            ],
            "evidence": ["independent review found a repairable evidence gap"],
            "reason": "the child package is repairable but not yet consumable",
            "repair_instruction": instruction,
            "parent_consumption_summary": "parent cannot consume the package before repair",
        },
        ensure_ascii=False,
    )


def parent_integration_json(
    *,
    consumed_child_jobs: list[str],
    integrated_candidate_text: str = "integrated parent candidate",
    evidence: list[str] | None = None,
    open_gaps: list[str] | None = None,
    suggested_follow_up_jobs: list[str] | None = None,
    parent_consumption_summary: str = "parent consumed accepted child packages",
) -> str:
    return json.dumps(
        {
            "integrated_candidate_text": integrated_candidate_text,
            "consumed_child_jobs": consumed_child_jobs,
            "evidence": evidence or ["accepted child package was referenced by job id"],
            "open_gaps": open_gaps or [],
            "suggested_follow_up_jobs": suggested_follow_up_jobs or [],
            "parent_consumption_summary": parent_consumption_summary,
        },
        ensure_ascii=False,
    )


def accepted_child_ids_from_messages(messages: list[dict[str, str]]) -> list[str]:
    payload = json.loads(messages[-1]["content"])
    return [
        str(item["job_id"])
        for item in payload.get("accepted_child_packages", [])
        if item.get("job_id")
    ]


def parent_integration_response(
    integrated_candidate_text: str = "integrated parent candidate",
    *,
    open_gaps: list[str] | None = None,
    suggested_follow_up_jobs: list[str] | None = None,
):
    def _response(messages: list[dict[str, str]]) -> str:
        return parent_integration_json(
            consumed_child_jobs=accepted_child_ids_from_messages(messages),
            integrated_candidate_text=integrated_candidate_text,
            open_gaps=open_gaps,
            suggested_follow_up_jobs=suggested_follow_up_jobs,
        )

    return _response


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
    def __init__(self, content: str = "fake answer", responses: list | None = None) -> None:
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
            if isinstance(content, BaseException):
                raise content
            if callable(content):
                content = content(messages)
            return ChatResponse(content=content, raw={"ok": True})
        system_text = "\n".join(
            message.get("content", "")
            for message in messages
            if message.get("role") == "system"
        )
        latest_payload = messages[-1].get("content", "") if messages else ""
        if "分业申请提议位" in system_text or "available_method_catalog" in latest_payload:
            return ChatResponse(content=split_proposals_json(), raw={"ok": True})
        if "父业整合位" in system_text or "integration_contract" in latest_payload:
            return ChatResponse(content=parent_integration_response()(messages), raw={"ok": True})
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
    def test_ai_split_proposal_requires_split_law(self) -> None:
        with self.assertRaises(RuntimeError) as context:
            normalize_split_proposal(
                {
                    "target": "decorative concept list",
                    "blocking_reason": "parent may want a glossary",
                    "output_contract": "glossary",
                    "acceptance_criteria": "glossary exists",
                    "estimated_effort": 1,
                    "depth_limit": 2,
                    "required_context_gaps": [],
                    "method_path": "",
                    "method_binding_reason": "",
                    "method_return_point": "",
                },
                catalog_by_path={},
            )

        self.assertIn("split_law", str(context.exception))

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
                    {
                        "target": "qualitative effort child",
                        "blocking_reason": "parent cannot rely on qualitative effort values",
                        "output_contract": "should be rejected before registration",
                        "acceptance_criteria": "effort must be numeric",
                        "estimated_effort": "高",
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": "",
                        "method_binding_reason": "",
                        "method_return_point": "",
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

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("candidate that needs a protagonist child job", answer)
            self.assertIn("make protagonist vivid", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("split_proposal_accepted"), 1)
            self.assertEqual(event_types.count("split_proposal_rejected"), 2)
            self.assertEqual(event_types.count("child_result_package_rejected"), 1)
            self.assertEqual(event_types.count("frontier_job_blocked"), 1)
            loop_finished = [
                record for record in records if record["event_type"] == "advancement_loop_finished"
            ][-1]
            self.assertEqual(loop_finished["data"]["advancement_loop_outcome"], "blocked")
            self.assertIn("make protagonist vivid", loop_finished["data"]["remaining_frontier_jobs"])
            checkpoint = [
                record for record in records if record["event_type"] == "runtime_checkpoint_recorded"
            ][-1]
            self.assertTrue(Path(checkpoint["data"]["runtime_checkpoint_path"]).exists())
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("child-method", serialized)
            self.assertIn("make protagonist vivid", serialized)
            self.assertIn("split proposal method is not in catalog", serialized)
            self.assertIn("split proposal field must be a positive integer: estimated_effort", serialized)
            self.assertIn("result package is missing fields", serialized)
            self.assertIn("split_proposal_child_created", serialized)
            self.assertIn("method_call_frames", serialized)
            self.assertIn("parent_integration_skipped", serialized)
            readable_text = next(log_dir.glob("ai-run-*.md")).read_text(encoding="utf-8-sig")
            self.assertIn("分业申请已登记（split_proposal_accepted）", readable_text)
            self.assertIn("分业申请已拒绝（split_proposal_rejected）", readable_text)
            self.assertIn("子业果包已拒绝（child_result_package_rejected）", readable_text)
            self.assertIn("前沿业已阻塞（frontier_job_blocked）", readable_text)
            self.assertIn("父业整合已跳过（parent_integration_skipped）", readable_text)

    def test_runner_returns_accepted_child_package_before_registering_followup(self) -> None:
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
                        "description: Child method for frontier dispatch tests.",
                        "---",
                        "# Child Method",
                        "Return a structured result package and surface next blocking work.",
                    ]
                ),
                encoding="utf-8",
            )
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "build protagonist card",
                        "blocking_reason": "parent needs a usable protagonist card before drafting",
                        "output_contract": "structured protagonist card",
                        "acceptance_criteria": "card includes desire, wound, contradiction, and scene evidence",
                        "estimated_effort": 1,
                        "depth_limit": 4,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "the child job needs a focused character method",
                        "method_return_point": "return character evidence to the parent story job",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate that needs character work",
                    method_review_json("checked root method use"),
                    root_split_payload,
                    child_result_package_json(
                        conclusion="protagonist card candidate",
                        artifacts=["desire: leave the egg-city", "contradiction: fears open sky"],
                        evidence_summary="the card maps directly to the requested story conflict",
                        open_questions=["vividness checklist is not yet quantified"],
                        suggested_follow_up_jobs=["turn vividness into measurable checks"],
                    ),
                    child_package_review_accept_json(
                        parent_consumption_summary="parent can consume the protagonist card"
                    ),
                    parent_integration_response(
                        "integrated root candidate with protagonist card",
                        suggested_follow_up_jobs=["quantify protagonist vividness checks"],
                    ),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create a story candidate and split blocking character work.")

            self.assertIn("# 金箍运行已暂停", answer)
            self.assertIn("integrated root candidate with protagonist card", answer)
            self.assertIn("quantify protagonist vividness checks", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("frontier_dispatch_started"), 1)
            self.assertEqual(event_types.count("child_job_dispatch_started"), 1)
            self.assertEqual(event_types.count("child_job_response_received"), 1)
            self.assertEqual(event_types.count("child_result_package_submitted"), 1)
            self.assertEqual(event_types.count("child_package_review_requested"), 1)
            self.assertEqual(event_types.count("child_package_review_received"), 1)
            self.assertEqual(event_types.count("child_package_review_accepted"), 1)
            self.assertEqual(event_types.count("accepted_parent_reevaluation_recorded"), 1)
            self.assertEqual(event_types.count("parent_integration_requested"), 1)
            self.assertEqual(event_types.count("parent_integration_candidate_submitted"), 1)
            self.assertEqual(event_types.count("frontier_dispatch_finished"), 1)
            self.assertEqual(event_types.count("split_proposal_accepted"), 2)
            self.assertNotIn("child_result_package_rejected", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            loop_finished = [
                record for record in records if record["event_type"] == "advancement_loop_finished"
            ][-1]
            self.assertEqual(loop_finished["data"]["advancement_loop_outcome"], "paused")
            self.assertIn("quantify protagonist vividness checks", loop_finished["data"]["remaining_frontier_jobs"])
            checkpoint = [
                record for record in records if record["event_type"] == "runtime_checkpoint_recorded"
            ][-1]
            self.assertTrue(Path(checkpoint["data"]["runtime_checkpoint_path"]).exists())
            self.assertIn("protagonist card candidate", serialized)
            self.assertIn("vividness checklist is not yet quantified", serialized)
            self.assertIn("quantify protagonist vividness checks", serialized)
            self.assertIn("accepted_parent_reevaluation", serialized)
            self.assertIn("parent can consume the protagonist card", serialized)
            self.assertIn("integrated root candidate with protagonist card", serialized)
            tree_actions = [
                record["data"]["job_tree_action"]
                for record in records
                if record["event_type"] == "job_tree_management_recorded"
            ]
            self.assertIn("child_dispatch_started", tree_actions)
            self.assertIn("child_package_submitted", tree_actions)
            self.assertIn("child_package_accepted", tree_actions)
            self.assertIn("accepted_parent_reevaluation_recorded", tree_actions)
            self.assertIn("parent_integration_candidate_submitted", tree_actions)
            tree_snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            final_root_nodes = [
                node
                for node in tree_snapshots[-1]["nodes"]
                if node["job_id"] == tree_snapshots[-1]["root_job_id"]
            ]
            self.assertEqual(final_root_nodes[0]["state"], "reviewing")
            self.assertTrue(
                any(
                    node["target"] == "quantify protagonist vividness checks"
                    for snapshot in tree_snapshots
                    for node in snapshot["nodes"]
                )
            )
            final_snapshot = tree_snapshots[-1]
            followup_nodes = [
                node
                for node in final_snapshot["nodes"]
                if node["target"] == "quantify protagonist vividness checks"
            ]
            self.assertEqual(followup_nodes[0]["parent_job_id"], final_snapshot["root_job_id"])
            readable_text = next(log_dir.glob("ai-run-*.md")).read_text(encoding="utf-8-sig")
            self.assertIn("子业果包已提交（child_result_package_submitted）", readable_text)
            self.assertIn("子业果包验收已接收（child_package_review_accepted）", readable_text)
            self.assertIn("已接收果包父业重评估已记录（accepted_parent_reevaluation_recorded）", readable_text)
            self.assertIn("父业整合候选已提交（parent_integration_candidate_submitted）", readable_text)
            self.assertIn("推进循环结果（advancement_loop_outcome）: paused", readable_text)
            self.assertNotIn("????", readable_text)

    def test_context_gap_frontier_blocks_without_package_rejection(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "collect missing source material",
                        "blocking_reason": "parent cannot proceed without source material",
                        "output_contract": "source material evidence package",
                        "acceptance_criteria": "source material is available and cited",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": ["missing source material"],
                        "method_path": "",
                        "method_binding_reason": "",
                        "method_return_point": "",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate",
                    method_review_json("checked root method use"),
                    root_split_payload,
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create a candidate but require source material first.")

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("missing source material", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("frontier_job_blocked", event_types)
            self.assertNotIn("child_result_package_rejected", event_types)
            loop_finished = [
                record for record in records if record["event_type"] == "advancement_loop_finished"
            ][-1]
            self.assertEqual(loop_finished["data"]["advancement_loop_outcome"], "blocked")
            self.assertIn("missing source material", loop_finished["data"]["blocked_frontier_jobs"])
            checkpoint = [
                record for record in records if record["event_type"] == "runtime_checkpoint_recorded"
            ][-1]
            self.assertTrue(Path(checkpoint["data"]["runtime_checkpoint_path"]).exists())

    def test_child_provider_failure_blocks_child_and_records_checkpoint(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "generate first chapter sample",
                        "blocking_reason": "parent needs a concrete chapter sample",
                        "output_contract": "chapter package",
                        "acceptance_criteria": "package includes chapter text and evidence",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": "",
                        "method_binding_reason": "",
                        "method_return_point": "",
                    }
                ]
            )
            provider_error = JinguRuntimeError(
                "AI provider stream idle timeout after 1 seconds without content"
            )
            client = FakeChatClient(
                responses=[
                    "root candidate",
                    method_review_json("checked root method use"),
                    root_split_payload,
                    provider_error,
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create a story and dispatch a child chapter job.")

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("generate first chapter sample", answer)
            self.assertIn("Provider 调用在子业产生果包前失败", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("provider_call_started", event_types)
            self.assertIn("provider_call_failed", event_types)
            self.assertIn("frontier_job_blocked", event_types)
            self.assertIn("advancement_loop_finished", event_types)
            self.assertIn("runtime_checkpoint_recorded", event_types)
            self.assertIn("run_finished", event_types)
            self.assertNotIn("run_failed", event_types)
            loop_finished = [
                record for record in records if record["event_type"] == "advancement_loop_finished"
            ][-1]
            self.assertEqual(loop_finished["data"]["advancement_loop_outcome"], "blocked")
            self.assertIn("AI provider stream idle timeout", loop_finished["data"]["blocked_frontier_jobs"])
            checkpoint = [
                record for record in records if record["event_type"] == "runtime_checkpoint_recorded"
            ][-1]
            self.assertTrue(Path(checkpoint["data"]["runtime_checkpoint_path"]).exists())
            readable_text = next(log_dir.glob("ai-run-*.md")).read_text(encoding="utf-8-sig")
            self.assertIn("Provider 调用已失败（provider_call_failed）", readable_text)
            self.assertIn("Provider 调用在子业产生果包前失败", readable_text)

    def test_runner_repairs_child_package_before_acceptance(self) -> None:
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
                        "---",
                        "# Child Method",
                        "Repair child packages when review sends them back.",
                    ]
                ),
                encoding="utf-8",
            )
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "make evidence measurable",
                        "blocking_reason": "parent needs measurable child evidence",
                        "output_contract": "result package with measurable evidence",
                        "acceptance_criteria": "evidence includes observable checks",
                        "estimated_effort": 1,
                        "depth_limit": 4,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "child method repairs evidence gaps",
                        "method_return_point": "return measurable evidence to parent",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate",
                    method_review_json("checked root method use"),
                    root_split_payload,
                    child_result_package_json(
                        conclusion="weak package",
                        artifacts=["artifact without metric"],
                        evidence_summary="evidence is vague",
                    ),
                    child_package_review_repair_json("Add one measurable check and threshold."),
                    child_result_package_json(
                        conclusion="repaired package",
                        artifacts=["check: at least three observable details"],
                        evidence_summary="threshold is explicit and parent-consumable",
                    ),
                    child_package_review_accept_json(
                        parent_consumption_summary="parent can consume the repaired package"
                    ),
                    parent_integration_response("integrated root candidate after repaired package"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create a child package and repair it if review finds evidence gaps.")

            self.assertEqual(answer, "integrated root candidate after repaired package")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_package_review_rejected"), 1)
            self.assertEqual(event_types.count("child_package_repair_requested"), 1)
            self.assertEqual(event_types.count("child_package_repair_response_received"), 1)
            self.assertEqual(event_types.count("child_package_repair_package_submitted"), 1)
            self.assertEqual(event_types.count("child_package_review_accepted"), 1)
            self.assertEqual(event_types.count("accepted_parent_reevaluation_recorded"), 1)
            self.assertEqual(event_types.count("parent_integration_candidate_submitted"), 1)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("Add one measurable check and threshold.", serialized)
            self.assertIn("repaired package", serialized)
            self.assertIn("parent can consume the repaired package", serialized)
            tree_actions = [
                record["data"]["job_tree_action"]
                for record in records
                if record["event_type"] == "job_tree_management_recorded"
            ]
            self.assertIn("child_package_repair_child_created", tree_actions)
            self.assertIn("child_package_repair_package_submitted", tree_actions)
            self.assertIn("child_package_accepted", tree_actions)

    def test_runner_rejects_invalid_parent_integration_without_mutating_parent_candidate(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            child_method = workspace / ".agents" / "skills" / "child-method" / "SKILL.md"
            child_method.parent.mkdir(parents=True)
            child_method.write_text("# Child Method\nReturn packages.", encoding="utf-8")
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "accepted child with invalid parent integration",
                        "blocking_reason": "parent needs child material",
                        "output_contract": "valid package",
                        "acceptance_criteria": "package is accepted before parent integration",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "local child method",
                        "method_return_point": "return package to parent",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate before integration",
                    method_review_json(),
                    root_split_payload,
                    child_result_package_json(conclusion="accepted child package"),
                    child_package_review_accept_json(),
                    "not json",
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create child material but make parent integration invalid.")

            self.assertEqual(answer, "root candidate before integration")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("parent_integration_requested"), 1)
            self.assertEqual(event_types.count("parent_integration_rejected"), 1)
            self.assertNotIn("parent_integration_candidate_submitted", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("parent integration response must be valid JSON", serialized)
            self.assertIn("root candidate before integration", serialized)

    def test_runner_records_invalid_child_package_review_without_accepting(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            child_method = workspace / ".agents" / "skills" / "child-method" / "SKILL.md"
            child_method.parent.mkdir(parents=True)
            child_method.write_text("# Child Method\nReturn packages.", encoding="utf-8")
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "review invalid response child",
                        "blocking_reason": "parent needs to see invalid review handling",
                        "output_contract": "valid package",
                        "acceptance_criteria": "review must be valid before acceptance",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "local child method",
                        "method_return_point": "return package to parent",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate",
                    method_review_json(),
                    root_split_payload,
                    child_result_package_json(),
                    "not json",
                    acceptance_continue_json(),
                ]
            )

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("Create a child package but make review invalid.")

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_package_review_rejected"), 1)
            self.assertEqual(event_types.count("parent_reevaluation_recorded"), 1)
            self.assertNotIn("child_package_review_accepted", event_types)
            self.assertNotIn("accepted_parent_reevaluation_recorded", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("child package review response must be valid JSON", serialized)

    def test_runner_stops_child_package_repair_at_limit(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sandbox = workspace / "sandbox"
            log_dir = workspace / "logs"
            method_path = write_method_file(workspace)
            child_method = workspace / ".agents" / "skills" / "child-method" / "SKILL.md"
            child_method.parent.mkdir(parents=True)
            child_method.write_text("# Child Method\nReturn packages.", encoding="utf-8")
            root_split_payload = split_proposals_json(
                [
                    {
                        "target": "repair limit child",
                        "blocking_reason": "parent needs repair limit visibility",
                        "output_contract": "valid package",
                        "acceptance_criteria": "repair is limited",
                        "estimated_effort": 1,
                        "depth_limit": 3,
                        "required_context_gaps": [],
                        "method_path": str(child_method),
                        "method_binding_reason": "local child method",
                        "method_return_point": "return package to parent",
                    }
                ]
            )
            client = FakeChatClient(
                responses=[
                    "root candidate",
                    method_review_json(),
                    root_split_payload,
                    child_result_package_json(),
                    child_package_review_repair_json("Repair would exceed configured budget."),
                    acceptance_continue_json(),
                ]
            )

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_child_package_repair_attempts=0,
            ).run("Create a child package but stop repair at the configured limit.")

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_package_repair_limit_reached"), 1)
            self.assertNotIn("child_package_repair_requested", event_types)
            self.assertNotIn("child_package_review_accepted", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("Repair would exceed configured budget.", serialized)

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

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("校验", answer)
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

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("direction choice", answer)
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
            checkpoint = [
                record for record in records if record["event_type"] == "runtime_checkpoint_recorded"
            ][-1]
            self.assertTrue(Path(checkpoint["data"]["runtime_checkpoint_path"]).exists())
            self.assertNotIn("job_accepted", event_types)
            self.assertNotIn("job_rejected", event_types)

    def test_runner_resume_restores_checkpoint_and_reenters_feedback_job(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            resume_sandbox = Path(tmp) / "resume-sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            initial_client = FakeChatClient(
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

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=initial_client,
            ).run("Produce a candidate and surface important unresolved direction choices.")
            first_records = [
                json.loads(line)
                for line in sorted(log_dir.glob("ai-run-*.jsonl"))[0].read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            checkpoint_path = Path(
                [
                    record
                    for record in first_records
                    if record["event_type"] == "runtime_checkpoint_recorded"
                ][-1]["data"]["runtime_checkpoint_path"]
            )
            feedback_job_id = [
                record
                for record in first_records
                if record["event_type"] == "feedback_job_created"
            ][-1]["data"]["feedback_job_id"]
            resume_client = FakeChatClient(
                responses=[
                    child_result_package_json(
                        conclusion="direction decision applied",
                        artifacts=["human chose the concrete direction"],
                        evidence_summary="human decision evidence is attached to the feedback job",
                    ),
                    child_package_review_accept_json(
                        parent_consumption_summary="parent can consume the returned direction decision"
                    ),
                    parent_integration_response("integrated answer after human decision"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=resume_sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=resume_client,
            ).resume(
                checkpoint_path=checkpoint_path,
                human_response="Use the concrete direction and continue.",
                feedback_job_id=feedback_job_id,
            )

            self.assertEqual(answer, "integrated answer after human decision")
            resume_log = max(log_dir.glob("ai-run-*.jsonl"), key=lambda path: path.stat().st_mtime)
            resume_records = [
                json.loads(line)
                for line in resume_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            resume_event_types = [record["event_type"] for record in resume_records]
            self.assertIn("runtime_checkpoint_restored", resume_event_types)
            self.assertIn("human_decision_returned", resume_event_types)
            self.assertIn("context_gaps_resolved", resume_event_types)
            self.assertIn("child_job_dispatch_started", resume_event_types)
            self.assertIn("parent_integration_candidate_submitted", resume_event_types)
            self.assertFalse(resume_sandbox.exists())

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

    def test_acceptance_routing_requires_reason_and_evidence(self) -> None:
        with self.assertRaises(RuntimeError) as context:
            parse_acceptance_routing_judgment(
                json.dumps(
                    {
                        "route_action": "continue",
                        "feedback_job_kind": "none",
                        "feedback_job_summary": "",
                        "required_context_gaps": [],
                        "repair_instruction": "",
                        "reason": "",
                        "evidence": [],
                    },
                    ensure_ascii=False,
                )
            )

        self.assertIn("reason is required", str(context.exception))

    def test_parent_integration_repair_creates_repair_job_and_lineage(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "Produce parent support material",
                "blocking_reason": "parent needs a consumable child package",
                "output_contract": "structured child result package",
                "acceptance_criteria": "package has conclusion, artifacts, evidence, gaps, and follow-up jobs",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
            }
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(),
                    child_package_review_accept_json(),
                    "{not valid integration json",
                    parent_integration_response("repaired integrated parent candidate"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("integrate child material")

            self.assertEqual(answer, "repaired integrated parent candidate")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("parent_integration_job_created", event_types)
            self.assertIn("parent_integration_repair_job_created", event_types)
            self.assertIn("parent_integration_repair_accepted", event_types)
            self.assertIn("parent_integration_candidate_submitted", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("candidate_lineage", serialized)
            self.assertIn("parent_integration_job_id", serialized)
            self.assertIn("evidence_hardness", serialized)

    def test_parent_integration_open_gaps_register_real_blocked_child_jobs(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "Produce parent support material",
                "blocking_reason": "parent needs a consumable child package",
                "output_contract": "structured child result package",
                "acceptance_criteria": "package has conclusion, artifacts, evidence, gaps, and follow-up jobs",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
            }
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(),
                    child_package_review_accept_json(),
                    parent_integration_response(
                        "integrated parent candidate with gap",
                        open_gaps=["missing external source"],
                        suggested_follow_up_jobs=["separate consistency review"],
                    ),
                    split_proposals_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("integrate child material and surface gaps")

            self.assertIn("missing external source", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("parent_integration_followup_registration_finished", event_types)
            self.assertIn("frontier_job_blocked", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("补齐父业整合开放缺口", serialized)
            self.assertIn("separate consistency review", serialized)
            snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            self.assertTrue(
                any(
                    node["state"] == "blocked" and "missing external source" in json.dumps(node, ensure_ascii=False)
                    for snapshot in snapshots
                    for node in snapshot["nodes"]
                )
            )

    def test_parent_integration_parks_followups_when_delivery_ledger_is_incomplete(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "Produce the first measurable batch",
                "blocking_reason": "parent needs initial content before acceptance work",
                "output_contract": "structured child result package",
                "acceptance_criteria": "package advances the parent candidate",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
            }
            client = FakeChatClient(
                responses=[
                    "字" * 1000,
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(
                        delivery_contributions=[
                            {
                                "contribution_id": "batch_1",
                                "content": "字" * 3000,
                                "counts_toward_parent_delivery": True,
                                "evidence": "first batch content belongs to the requested body text",
                            }
                        ]
                    ),
                    child_package_review_accept_json(),
                    parent_integration_response(
                        "字" * 2000,
                        open_gaps=["missing external source"],
                        suggested_follow_up_jobs=["separate consistency review"],
                    ),
                    split_proposals_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("请输出1万字到2万字的完整正文。")

            self.assertIn("# 金箍运行已暂停", answer)
            self.assertIn("继续补齐根业量化交付目标", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("delivery_ledger_recorded", event_types)
            self.assertIn("parent_integration_followup_parked", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("below_minimum", serialized)
            self.assertIn("当前 3000 / 最低 10000", serialized)
            self.assertIn("accepted_delivery_contributions", serialized)
            self.assertIn("missing external source", serialized)
            self.assertIn("separate consistency review", serialized)
            self.assertIn("delivery_ledger", serialized)
            ledgers = [
                json.loads(record["data"]["delivery_ledger"])
                for record in records
                if record["event_type"] == "delivery_ledger_recorded"
            ]
            self.assertTrue(
                any(
                    ledger["accounting_basis"] == "accepted_delivery_contributions"
                    and ledger["actual_cjk_characters"] == 3000
                    for ledger in ledgers
                )
            )
            snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            self.assertFalse(
                any(
                    node["state"] == "blocked" and "missing external source" in json.dumps(node, ensure_ascii=False)
                    for snapshot in snapshots
                    for node in snapshot["nodes"]
                )
            )

    def test_split_proposal_rejects_completion_dependent_child_before_delivery_minimum(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            final_proposal = {
                "target": "最终交付完整正文",
                "blocking_reason": "parent acceptance depends on the final manuscript",
                "output_contract": "complete manuscript package",
                "acceptance_criteria": "总字数1万字到2万字之间，并附带完整证据",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "split_law": default_split_law(
                    blocks_parent_execution=False,
                    blocks_parent_acceptance=True,
                    needs_distinct_capability=True,
                ),
            }
            batch_proposal = {
                "target": "继续生成下一批正文",
                "blocking_reason": "parent needs more body content before final acceptance work",
                "output_contract": "incremental body package",
                "acceptance_criteria": "package advances the parent candidate",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
                "split_law": default_split_law(blocks_parent_execution=True),
            }
            feedback_proposal = {
                "target": "收集读者反馈",
                "blocking_reason": "feedback may improve later writing",
                "output_contract": "feedback report",
                "acceptance_criteria": "report has observations",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "does_not_advance_quantitative_delivery",
                "split_law": default_split_law(blocks_parent_acceptance=True),
            }
            client = FakeChatClient(
                responses=[
                    "字" * 1000,
                    method_review_json(),
                    split_proposals_json([final_proposal, batch_proposal, feedback_proposal]),
                    child_result_package_json(
                        delivery_contributions=[
                            {
                                "contribution_id": "batch_1",
                                "content": "字" * 2000,
                                "counts_toward_parent_delivery": True,
                                "evidence": "incremental body text",
                            }
                        ]
                    ),
                    child_package_review_accept_json(),
                    parent_integration_response("字" * 2000),
                    split_proposals_json(),
                ]
            )

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("请输出1万字到2万字的完整正文。")

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("split_proposal_rejected", event_types)
            self.assertIn("split_proposal_parked", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("root quantitative delivery is still below the minimum", serialized)
            self.assertIn("non-critical split is parked", serialized)
            snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            self.assertFalse(
                any(
                    "最终交付完整正文" in json.dumps(node, ensure_ascii=False)
                    for snapshot in snapshots
                    for node in snapshot["nodes"]
                )
            )

    def test_completion_only_split_falls_back_to_delivery_continuation(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            final_proposal = {
                "target": "最终交付完整正文",
                "blocking_reason": "parent acceptance depends on the final manuscript",
                "output_contract": "complete manuscript package",
                "acceptance_criteria": "总字数1万字到2万字之间，并附带完整证据",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "split_law": default_split_law(
                    blocks_parent_execution=False,
                    blocks_parent_acceptance=True,
                    needs_distinct_capability=True,
                ),
            }
            client = FakeChatClient(
                responses=[
                    "字" * 1000,
                    method_review_json(),
                    split_proposals_json([final_proposal]),
                    child_result_package_json(
                        delivery_contributions=[
                            {
                                "contribution_id": "fallback_batch",
                                "content": "字" * 1500,
                                "counts_toward_parent_delivery": True,
                                "evidence": "runtime fallback asked for direct delivery continuation",
                            }
                        ]
                    ),
                    child_package_review_accept_json(),
                    parent_integration_response("阶段整合说明"),
                ]
            )

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("请输出1万字到2万字的完整正文。")

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("root quantitative delivery is still below the minimum", serialized)
            self.assertIn("继续补齐根业量化交付目标", serialized)
            self.assertIn("fallback_batch", serialized)
            snapshots = [
                json.loads(record["data"]["tree_snapshot"])
                for record in records
                if record["event_type"] == "job_tree_snapshot_recorded"
            ]
            self.assertFalse(
                any(
                    "最终交付完整正文" in json.dumps(node, ensure_ascii=False)
                    for snapshot in snapshots
                    for node in snapshot["nodes"]
                )
            )

    def test_invalid_parent_integration_repair_does_not_mutate_parent_candidate(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "Produce parent support material",
                "blocking_reason": "parent needs a consumable child package",
                "output_contract": "structured child result package",
                "acceptance_criteria": "package has conclusion, artifacts, evidence, gaps, and follow-up jobs",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
            }
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(),
                    child_package_review_accept_json(),
                    "{not valid integration json",
                    "{still invalid",
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
            ).run("do not mutate parent on invalid repair")

            self.assertEqual(answer, "root draft")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("parent_integration_repair_rejected", event_types)
            self.assertNotIn("parent_integration_candidate_submitted", event_types)

    def test_advancement_loop_processes_followup_child_in_second_wave(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))

            def proposal(target: str) -> dict:
                return {
                    "target": target,
                    "blocking_reason": "needed by parent",
                    "output_contract": "structured child result package",
                    "acceptance_criteria": "package is consumable by parent",
                    "estimated_effort": 1,
                    "depth_limit": 3,
                    "required_context_gaps": [],
                    "method_path": "",
                    "method_binding_reason": "",
                    "method_return_point": "",
                }

            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([proposal("first child")]),
                    child_result_package_json(conclusion="first"),
                    child_package_review_accept_json(),
                    parent_integration_response("first integration"),
                    split_proposals_json([proposal("second child")]),
                    child_result_package_json(conclusion="second"),
                    child_package_review_accept_json(),
                    parent_integration_response("second integration"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=2,
            ).run("advance multiple child waves")

            self.assertEqual(answer, "second integration")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("advancement_wave_started"), 2)
            self.assertGreaterEqual(event_types.count("child_job_dispatch_started"), 2)
            self.assertIn("advancement_loop_finished", event_types)

    def test_runner_auto_continues_when_wave_budget_leaves_runnable_frontier(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))

            def proposal(target: str) -> dict:
                return {
                    "target": target,
                    "blocking_reason": "needed by parent",
                    "output_contract": "structured child result package",
                    "acceptance_criteria": "package is consumable by parent",
                    "estimated_effort": 1,
                    "depth_limit": 3,
                    "required_context_gaps": [],
                    "method_path": "",
                    "method_binding_reason": "",
                    "method_return_point": "",
                }

            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([proposal("first child")]),
                    child_result_package_json(conclusion="first"),
                    child_package_review_accept_json(),
                    parent_integration_response("first integration"),
                    split_proposals_json([proposal("second child")]),
                    child_result_package_json(conclusion="second"),
                    child_package_review_accept_json(),
                    parent_integration_response("second integration"),
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=1,
                auto_continue_to_blocker=True,
            ).run("continue runnable frontier in one command")

            self.assertEqual(answer, "second integration")
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("advancement_loop_finished"), 2)
            self.assertEqual(event_types.count("runtime_checkpoint_recorded"), 0)
            self.assertGreaterEqual(event_types.count("child_job_dispatch_started"), 2)
            self.assertTrue(
                any(
                    record["event_type"] == "process_step_recorded"
                    and record["data"].get("process_status") == "continued"
                    for record in records
                )
            )

    def test_auto_continue_pauses_after_quantitative_delivery_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "produce first text batch",
                "blocking_reason": "parent needs measurable body text",
                "output_contract": "structured batch package",
                "acceptance_criteria": "package includes counted delivery text",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
            }
            client = FakeChatClient(
                responses=[
                    "字" * 1000,
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(
                        delivery_contributions=[
                            {
                                "contribution_id": "batch_1",
                                "content": "字" * 3000,
                                "counts_toward_parent_delivery": True,
                                "evidence": "first measurable body text batch",
                            }
                        ]
                    ),
                    child_package_review_accept_json(),
                    parent_integration_response("阶段交付清单"),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=1,
                auto_continue_to_blocker=True,
            ).run("请输出1万字到2万字的完整正文。")

            self.assertIn("# 金箍运行已暂停", answer)
            self.assertIn("measurable delivery batch accepted", answer)
            self.assertIn("确定性交付账本", answer)
            self.assertIn("actual_cjk_characters", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_job_dispatch_started"), 1)
            self.assertEqual(event_types.count("runtime_checkpoint_recorded"), 1)
            self.assertIn("batch_boundary", "\n".join(json.dumps(record) for record in records))

    def test_child_package_guardrail_failure_creates_repair_job_and_accepts_repaired_package(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "produce counted text batch",
                "blocking_reason": "parent needs measurable body text",
                "output_contract": "structured batch package",
                "acceptance_criteria": "package includes counted delivery text",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
            }
            invalid_package = json.dumps(
                {
                    "conclusion": "invalid counted package",
                    "artifacts": [],
                    "delivery_contributions": [
                        {
                            "contribution_id": "bad_count",
                            "content": "正文",
                            "counts_toward_parent_delivery": "true",
                            "evidence": "正文可计入父业。",
                        }
                    ],
                    "evidence_summary": "invalid boolean should be blocked",
                    "open_questions": [],
                    "suggested_follow_up_jobs": [],
                },
                ensure_ascii=False,
            )
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    invalid_package,
                    child_result_package_json(
                        conclusion="repaired counted package",
                        delivery_contributions=[
                            {
                                "contribution_id": "batch_1",
                                "content": "字" * 3000,
                                "counts_toward_parent_delivery": True,
                                "evidence": "repaired package contains measurable parent-delivery text",
                            }
                        ],
                        evidence_summary="deterministic repair produced a valid package",
                    ),
                    child_package_review_accept_json(
                        parent_consumption_summary="parent can consume the repaired package"
                    ),
                    parent_integration_response("阶段交付清单"),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=1,
                auto_continue_to_blocker=True,
            ).run("请输出1万字到2万字的完整正文。")

            self.assertIn("# 金箍运行已暂停", answer)
            self.assertIn("measurable delivery batch accepted", answer)
            self.assertIn("确定性交付账本", answer)
            self.assertIn("actual_cjk_characters", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_job_dispatch_started"), 1)
            self.assertEqual(event_types.count("child_result_package_rejected"), 1)
            self.assertEqual(event_types.count("child_package_repair_requested"), 1)
            self.assertEqual(event_types.count("child_package_repair_response_received"), 1)
            self.assertEqual(event_types.count("child_package_repair_package_submitted"), 1)
            self.assertEqual(event_types.count("child_package_review_accepted"), 1)
            self.assertEqual(event_types.count("frontier_job_blocked"), 0)
            self.assertEqual(event_types.count("runtime_checkpoint_recorded"), 1)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("deterministic_guardrail", serialized)
            self.assertIn("counts_toward_parent_delivery must be boolean", serialized)
            self.assertIn("repaired counted package", serialized)
            tree_actions = [
                record["data"]["job_tree_action"]
                for record in records
                if record["event_type"] == "job_tree_management_recorded"
            ]
            self.assertIn("child_package_repair_child_created", tree_actions)
            self.assertIn("child_package_repair_package_submitted", tree_actions)

    def test_child_package_guardrail_repair_limit_blocks_original_child_once(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "produce counted text batch",
                "blocking_reason": "parent needs measurable body text",
                "output_contract": "structured batch package",
                "acceptance_criteria": "package includes counted delivery text",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
            }
            invalid_package = json.dumps(
                {
                    "conclusion": "invalid counted package",
                    "artifacts": [],
                    "delivery_contributions": [
                        {
                            "contribution_id": "bad_count",
                            "content": "正文",
                            "counts_toward_parent_delivery": "true",
                            "evidence": "正文可计入父业。",
                        }
                    ],
                    "evidence_summary": "invalid boolean should be blocked",
                    "open_questions": [],
                    "suggested_follow_up_jobs": [],
                },
                ensure_ascii=False,
            )
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    invalid_package,
                    invalid_package,
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=1,
                max_child_package_repair_attempts=1,
                auto_continue_to_blocker=True,
            ).run("请输出1万字到2万字的完整正文。")

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("counts_toward_parent_delivery must be boolean", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_result_package_rejected"), 1)
            self.assertEqual(event_types.count("child_package_repair_requested"), 1)
            self.assertEqual(event_types.count("child_package_repair_response_received"), 1)
            self.assertEqual(event_types.count("child_package_repair_rejected"), 1)
            self.assertEqual(event_types.count("child_package_repair_limit_reached"), 1)
            self.assertEqual(event_types.count("child_package_repair_package_submitted"), 0)
            self.assertEqual(event_types.count("child_package_review_requested"), 0)
            self.assertEqual(event_types.count("frontier_job_blocked"), 1)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("deterministic_guardrail", serialized)
            self.assertIn("确定性果包修复次数已达上限", serialized)

    def test_critical_delivery_child_without_counted_contribution_is_blocked(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(Path(tmp))
            child_proposal = {
                "target": "produce measurable text batch",
                "blocking_reason": "parent needs measurable body text",
                "output_contract": "structured batch package",
                "acceptance_criteria": "package includes counted delivery text",
                "estimated_effort": 1,
                "depth_limit": 3,
                "required_context_gaps": [],
                "method_path": "",
                "method_binding_reason": "",
                "method_return_point": "",
                "delivery_relation": "advances_quantitative_delivery",
            }
            client = FakeChatClient(
                responses=[
                    "root draft",
                    method_review_json(),
                    split_proposals_json([child_proposal]),
                    child_result_package_json(
                        conclusion="review report only",
                        artifacts=["claims 3000 words but no counted delivery contribution"],
                        evidence_summary="support-only package",
                        delivery_contributions=[],
                    ),
                    child_package_review_accept_json(),
                ]
            )

            answer = AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_advancement_waves=1,
                auto_continue_to_blocker=True,
            ).run("请输出1万字到2万字的完整正文。")

            self.assertIn("# 金箍运行已阻塞", answer)
            self.assertIn("no counted delivery_contributions", answer)
            self.assertIn("确定性交付账本", answer)
            self.assertIn("actual_cjk_characters", answer)
            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertEqual(event_types.count("child_package_review_accepted"), 0)
            self.assertEqual(event_types.count("accepted_parent_reevaluation_recorded"), 0)
            self.assertEqual(event_types.count("parent_integration_candidate_submitted"), 0)
            self.assertEqual(event_types.count("frontier_job_blocked"), 1)

    def test_method_learning_candidate_and_method_step_candidate_are_visible(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = Path(tmp) / "logs"
            method_path = write_method_file(
                Path(tmp),
                "\n".join(
                    [
                        "---",
                        "name: step-method",
                        "---",
                        "# Step One",
                        "Do the first step.",
                        "# Step Two",
                        "Do the second step.",
                    ]
                ),
            )
            review_with_update = json.dumps(
                {
                    "method_use_summary": "used visible steps",
                    "evidence": ["method law ids referenced"],
                    "gaps": [],
                    "observed_failure_modes": [],
                    "method_update_candidates": ["Add a measurable acceptance checklist."],
                },
                ensure_ascii=False,
            )
            client = FakeChatClient(
                responses=[
                    "candidate",
                    review_with_update,
                    split_proposals_json(),
                    acceptance_continue_json(),
                ]
            )

            AiSandboxRunner(
                sandbox_path=sandbox,
                log_dir=log_dir,
                method_path=method_path,
                client=client,
                max_frontier_dispatches=0,
                register_method_step_candidates=True,
            ).run("show method learning and steps")

            records = [
                json.loads(line)
                for line in next(log_dir.glob("ai-run-*.jsonl")).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [record["event_type"] for record in records]
            self.assertIn("method_learning_candidate_recorded", event_types)
            self.assertIn("method_step_candidate_recorded", event_types)
            serialized = "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
            self.assertIn("candidate_only", serialized)
            self.assertIn("method_step_candidate_summary", serialized)

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
            kwargs: dict[str, object] = {}

            def __init__(self, **kwargs):
                FakeRunner.kwargs = kwargs

            def run(self, message: str) -> str:
                self.message = message
                return "answer only"

        output = StringIO()
        with patch("jingu.cli.AiSandboxRunner", FakeRunner), redirect_stdout(output):
            code = main(["ai", "run", "--message", "hello"])

        self.assertEqual(code, 0)
        self.assertEqual(output.getvalue(), "answer only\n")
        self.assertTrue(FakeRunner.kwargs["auto_continue_to_blocker"])

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
                    child_result_package_json(
                        conclusion="direction decision applied",
                        artifacts=["human returned the next direction"],
                        evidence_summary="human decision evidence is attached",
                    ),
                    child_package_review_accept_json(
                        parent_consumption_summary="parent can consume the returned direction decision"
                    ),
                    parent_integration_response("chat answer 2 after decision"),
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

            self.assertIn("# 金箍运行已阻塞", first)
            self.assertIn("next direction", first)
            self.assertEqual(second, "chat answer 2 after decision")
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
            self.assertEqual(event_types.count("method_context_injected"), 1)
            self.assertEqual(event_types.count("method_law_fragment_bound"), 1)
            self.assertEqual(event_types.count("method_self_review_requested"), 1)
            self.assertEqual(event_types.count("method_self_review_received"), 1)
            self.assertEqual(event_types.count("method_update_candidate_recorded"), 1)
            self.assertGreaterEqual(event_types.count("split_proposal_requested"), 2)
            self.assertGreaterEqual(event_types.count("split_proposal_received"), 2)
            self.assertGreaterEqual(event_types.count("split_proposal_skipped"), 3)
            self.assertEqual(event_types.count("result_output_recorded"), 2)
            self.assertGreaterEqual(event_types.count("candidate_submitted"), 1)
            self.assertGreaterEqual(event_types.count("evidence_submitted"), 2)
            self.assertEqual(event_types.count("verification_job_created"), 2)
            self.assertEqual(event_types.count("verification_tool_started"), 2)
            self.assertEqual(event_types.count("verification_result_recorded"), 2)
            self.assertEqual(event_types.count("verification_evidence_submitted"), 2)
            self.assertEqual(event_types.count("parent_verification_evidence_submitted"), 2)
            self.assertEqual(event_types.count("acceptance_routing_requested"), 2)
            self.assertEqual(event_types.count("acceptance_routing_received"), 2)
            self.assertEqual(event_types.count("acceptance_routing_evidence_submitted"), 2)
            self.assertEqual(event_types.count("feedback_job_created"), 1)
            self.assertEqual(event_types.count("human_decision_returned"), 1)
            self.assertEqual(event_types.count("context_gaps_resolved"), 1)
            self.assertEqual(event_types.count("child_job_dispatch_started"), 1)
            self.assertEqual(event_types.count("parent_integration_candidate_submitted"), 1)
            self.assertEqual(event_types.count("acceptance_routing_skipped"), 1)
            self.assertGreaterEqual(event_types.count("provider_messages_recorded"), 9)
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

    def test_readable_event_skips_provider_stream_deltas(self) -> None:
        rendered = format_readable_event(
            {
                "timestamp": "2026-05-17T10:00:00+00:00",
                "event_type": "provider_stream_delta_received",
                "message": "provider stream delta received",
                "data": {
                    "provider_call_kind": "candidate_generation",
                    "provider_delta_text": "逐字流",
                },
            }
        )

        self.assertEqual(rendered, "")


if __name__ == "__main__":
    unittest.main()
