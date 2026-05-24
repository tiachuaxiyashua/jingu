"""JSONL flow event stream for sandbox runs."""

from __future__ import annotations

import json
import re
import hashlib
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from jingu.sandbox.paths import flow_events_path


FLOW_SANDBOX_CREATED = "sandbox_created"
FLOW_RUNTIME_INITIALIZED = "runtime_initialized"
FLOW_RUNTIME_OPTIONS_RECORDED = "runtime_options_recorded"
FLOW_CHAT_SESSION_STARTED = "chat_session_started"
FLOW_METHOD_SOURCE_RESOLVED = "method_source_resolved"
FLOW_METHOD_CONTEXT_LOADED = "method_context_loaded"
FLOW_METHOD_LAW_FRAGMENT_LOADED = "method_law_fragment_loaded"
FLOW_METHOD_LAW_FRAGMENT_BOUND = "method_law_fragment_bound"
FLOW_METHOD_CALL_FRAME_OPENED = "method_call_frame_opened"
FLOW_METHOD_CONTEXT_INJECTED = "method_context_injected"
FLOW_ROOT_JOB_CREATED = "root_job_created"
FLOW_JOB_READY = "job_ready"
FLOW_JOB_RUNNING = "job_running"
FLOW_JOB_TREE_MANAGEMENT_RECORDED = "job_tree_management_recorded"
FLOW_JOB_TREE_SNAPSHOT_RECORDED = "job_tree_snapshot_recorded"
FLOW_PROCESS_STEP_RECORDED = "process_step_recorded"
FLOW_USER_INPUT_RECORDED = "user_input_recorded"
FLOW_INPUT_PROVENANCE_RECORDED = "input_provenance_recorded"
FLOW_PROVIDER_MESSAGES_RECORDED = "provider_messages_recorded"
FLOW_PROVIDER_STREAM_DELTA_RECEIVED = "provider_stream_delta_received"
FLOW_PROVIDER_STREAM_FINISHED = "provider_stream_finished"
FLOW_AI_REQUEST_STARTED = "ai_request_started"
FLOW_AI_RESPONSE_RECEIVED = "ai_response_received"
FLOW_CANDIDATE_SUBMITTED = "candidate_submitted"
FLOW_EVIDENCE_SUBMITTED = "evidence_submitted"
FLOW_VERIFICATION_JOB_CREATED = "verification_job_created"
FLOW_VERIFICATION_TOOL_STARTED = "verification_tool_started"
FLOW_VERIFICATION_RESULT_RECORDED = "verification_result_recorded"
FLOW_VERIFICATION_EVIDENCE_SUBMITTED = "verification_evidence_submitted"
FLOW_PARENT_VERIFICATION_EVIDENCE_SUBMITTED = "parent_verification_evidence_submitted"
FLOW_REPAIR_JOB_CREATED = "repair_job_created"
FLOW_REPAIR_REQUEST_PREPARED = "repair_request_prepared"
FLOW_REPAIR_RESPONSE_RECEIVED = "repair_response_received"
FLOW_REPAIR_CANDIDATE_SUBMITTED = "repair_candidate_submitted"
FLOW_REPAIR_LOOP_FINISHED = "repair_loop_finished"
FLOW_VERIFICATION_FEEDBACK_JOB_CREATED = "verification_feedback_job_created"
FLOW_ACCEPTANCE_ROUTING_REQUESTED = "acceptance_routing_requested"
FLOW_ACCEPTANCE_ROUTING_RECEIVED = "acceptance_routing_received"
FLOW_ACCEPTANCE_ROUTING_EVIDENCE_SUBMITTED = "acceptance_routing_evidence_submitted"
FLOW_ACCEPTANCE_ROUTING_SKIPPED = "acceptance_routing_skipped"
FLOW_FEEDBACK_JUDGMENT_REQUESTED = "feedback_judgment_requested"
FLOW_FEEDBACK_JUDGMENT_RECEIVED = "feedback_judgment_received"
FLOW_FEEDBACK_JOB_CREATED = "feedback_job_created"
FLOW_FEEDBACK_JOB_SKIPPED = "feedback_job_skipped"
FLOW_METHOD_SELF_REVIEW_REQUESTED = "method_self_review_requested"
FLOW_METHOD_SELF_REVIEW_RECEIVED = "method_self_review_received"
FLOW_METHOD_UPDATE_CANDIDATE_RECORDED = "method_update_candidate_recorded"
FLOW_METHOD_LEARNING_CANDIDATE_RECORDED = "method_learning_candidate_recorded"
FLOW_METHOD_STEP_CANDIDATE_RECORDED = "method_step_candidate_recorded"
FLOW_METHOD_STEP_CANDIDATE_SKIPPED = "method_step_candidate_skipped"
FLOW_SPLIT_PROPOSAL_REQUESTED = "split_proposal_requested"
FLOW_SPLIT_PROPOSAL_RECEIVED = "split_proposal_received"
FLOW_SPLIT_PROPOSAL_ACCEPTED = "split_proposal_accepted"
FLOW_SPLIT_PROPOSAL_REJECTED = "split_proposal_rejected"
FLOW_SPLIT_PROPOSAL_SKIPPED = "split_proposal_skipped"
FLOW_FRONTIER_DISPATCH_STARTED = "frontier_dispatch_started"
FLOW_FRONTIER_DISPATCH_SKIPPED = "frontier_dispatch_skipped"
FLOW_FRONTIER_DISPATCH_FINISHED = "frontier_dispatch_finished"
FLOW_CHILD_JOB_DISPATCH_STARTED = "child_job_dispatch_started"
FLOW_CHILD_JOB_RESPONSE_RECEIVED = "child_job_response_received"
FLOW_CHILD_RESULT_PACKAGE_SUBMITTED = "child_result_package_submitted"
FLOW_CHILD_RESULT_PACKAGE_REJECTED = "child_result_package_rejected"
FLOW_CHILD_PACKAGE_REVIEW_REQUESTED = "child_package_review_requested"
FLOW_CHILD_PACKAGE_REVIEW_RECEIVED = "child_package_review_received"
FLOW_CHILD_PACKAGE_REVIEW_ACCEPTED = "child_package_review_accepted"
FLOW_CHILD_PACKAGE_REVIEW_REJECTED = "child_package_review_rejected"
FLOW_CHILD_PACKAGE_REPAIR_REQUESTED = "child_package_repair_requested"
FLOW_CHILD_PACKAGE_REPAIR_RESPONSE_RECEIVED = "child_package_repair_response_received"
FLOW_CHILD_PACKAGE_REPAIR_PACKAGE_SUBMITTED = "child_package_repair_package_submitted"
FLOW_CHILD_PACKAGE_REPAIR_REJECTED = "child_package_repair_rejected"
FLOW_CHILD_PACKAGE_REPAIR_LIMIT_REACHED = "child_package_repair_limit_reached"
FLOW_ACCEPTED_PARENT_REEVALUATION_RECORDED = "accepted_parent_reevaluation_recorded"
FLOW_PARENT_REEVALUATION_RECORDED = "parent_reevaluation_recorded"
FLOW_PARENT_INTEGRATION_REQUESTED = "parent_integration_requested"
FLOW_PARENT_INTEGRATION_JOB_CREATED = "parent_integration_job_created"
FLOW_PARENT_INTEGRATION_RECEIVED = "parent_integration_received"
FLOW_PARENT_INTEGRATION_CANDIDATE_SUBMITTED = "parent_integration_candidate_submitted"
FLOW_PARENT_INTEGRATION_REJECTED = "parent_integration_rejected"
FLOW_PARENT_INTEGRATION_SKIPPED = "parent_integration_skipped"
FLOW_PARENT_INTEGRATION_REPAIR_JOB_CREATED = "parent_integration_repair_job_created"
FLOW_PARENT_INTEGRATION_REPAIR_REQUESTED = "parent_integration_repair_requested"
FLOW_PARENT_INTEGRATION_REPAIR_RECEIVED = "parent_integration_repair_received"
FLOW_PARENT_INTEGRATION_REPAIR_REJECTED = "parent_integration_repair_rejected"
FLOW_PARENT_INTEGRATION_REPAIR_ACCEPTED = "parent_integration_repair_accepted"
FLOW_PARENT_INTEGRATION_FOLLOWUP_REGISTRATION_FINISHED = (
    "parent_integration_followup_registration_finished"
)
FLOW_ADVANCEMENT_WAVE_STARTED = "advancement_wave_started"
FLOW_ADVANCEMENT_WAVE_FINISHED = "advancement_wave_finished"
FLOW_ADVANCEMENT_LOOP_FINISHED = "advancement_loop_finished"
FLOW_HUMAN_DECISION_REQUESTED = "human_decision_requested"
FLOW_HUMAN_DECISION_RETURNED = "human_decision_returned"
FLOW_RESULT_OUTPUT_RECORDED = "result_output_recorded"
FLOW_CHAT_TURN_FINISHED = "chat_turn_finished"
FLOW_CHAT_SESSION_FINISHED = "chat_session_finished"
FLOW_RUN_FAILED = "run_failed"
FLOW_RUN_FINISHED = "run_finished"
FLOW_SANDBOX_DESTROYED = "sandbox_destroyed"

TERMINAL_EVENTS = {FLOW_RUN_FINISHED, FLOW_CHAT_SESSION_FINISHED, FLOW_SANDBOX_DESTROYED}
SUSPICIOUS_QUESTION_MARKS = re.compile(r"\?{4,}")
MARKDOWN_HEADING = re.compile(r"(?m)^#{1,6}\s+\S")
FENCED_BLOCK = re.compile(r"(?m)^```")

EVENT_LABELS = {
    FLOW_SANDBOX_CREATED: "沙盒已创建",
    FLOW_RUNTIME_INITIALIZED: "运行库已初始化",
    FLOW_RUNTIME_OPTIONS_RECORDED: "运行选项已记录",
    FLOW_CHAT_SESSION_STARTED: "对话会话已开始",
    FLOW_METHOD_SOURCE_RESOLVED: "方法来源已解析",
    FLOW_METHOD_CONTEXT_LOADED: "方法上下文已加载",
    FLOW_METHOD_LAW_FRAGMENT_LOADED: "法片段已加载",
    FLOW_METHOD_LAW_FRAGMENT_BOUND: "法片段已绑定",
    FLOW_METHOD_CALL_FRAME_OPENED: "法调用帧已打开",
    FLOW_METHOD_CONTEXT_INJECTED: "方法上下文已注入",
    FLOW_ROOT_JOB_CREATED: "根业已创建",
    FLOW_JOB_READY: "业已就绪",
    FLOW_JOB_RUNNING: "业运行中",
    FLOW_JOB_TREE_MANAGEMENT_RECORDED: "业树管理已记录",
    FLOW_JOB_TREE_SNAPSHOT_RECORDED: "业树快照已记录",
    FLOW_PROCESS_STEP_RECORDED: "运行步骤已记录",
    FLOW_USER_INPUT_RECORDED: "用户输入已记录",
    FLOW_INPUT_PROVENANCE_RECORDED: "输入来源已记录",
    FLOW_PROVIDER_MESSAGES_RECORDED: "Provider 请求消息已记录",
    FLOW_PROVIDER_STREAM_DELTA_RECEIVED: "Provider 流式增量已收到",
    FLOW_PROVIDER_STREAM_FINISHED: "Provider 流式输出已结束",
    FLOW_AI_REQUEST_STARTED: "AI 请求已开始",
    FLOW_AI_RESPONSE_RECEIVED: "AI 响应已收到",
    FLOW_CANDIDATE_SUBMITTED: "候选结果已提交",
    FLOW_EVIDENCE_SUBMITTED: "证据已提交",
    FLOW_VERIFICATION_JOB_CREATED: "候选校验业已创建",
    FLOW_VERIFICATION_TOOL_STARTED: "候选校验工具已启动",
    FLOW_VERIFICATION_RESULT_RECORDED: "候选校验结果已记录",
    FLOW_VERIFICATION_EVIDENCE_SUBMITTED: "候选校验证据已提交",
    FLOW_PARENT_VERIFICATION_EVIDENCE_SUBMITTED: "父业校验证据已回流",
    FLOW_REPAIR_JOB_CREATED: "修复业已创建",
    FLOW_REPAIR_REQUEST_PREPARED: "修复请求已准备",
    FLOW_REPAIR_RESPONSE_RECEIVED: "修复响应已收到",
    FLOW_REPAIR_CANDIDATE_SUBMITTED: "修复候选已提交",
    FLOW_REPAIR_LOOP_FINISHED: "修复循环已结束",
    FLOW_VERIFICATION_FEEDBACK_JOB_CREATED: "校验反馈裁决业已创建",
    FLOW_ACCEPTANCE_ROUTING_REQUESTED: "验收路由已请求",
    FLOW_ACCEPTANCE_ROUTING_RECEIVED: "验收路由已收到",
    FLOW_ACCEPTANCE_ROUTING_EVIDENCE_SUBMITTED: "验收路由证据已提交",
    FLOW_ACCEPTANCE_ROUTING_SKIPPED: "验收路由已继续",
    FLOW_FEEDBACK_JUDGMENT_REQUESTED: "反馈判断已请求",
    FLOW_FEEDBACK_JUDGMENT_RECEIVED: "反馈判断已收到",
    FLOW_FEEDBACK_JOB_CREATED: "反馈业已创建",
    FLOW_FEEDBACK_JOB_SKIPPED: "反馈业已跳过",
    FLOW_METHOD_SELF_REVIEW_REQUESTED: "方法自验已请求",
    FLOW_METHOD_SELF_REVIEW_RECEIVED: "方法自验已收到",
    FLOW_METHOD_UPDATE_CANDIDATE_RECORDED: "方法更新候选已记录",
    FLOW_METHOD_LEARNING_CANDIDATE_RECORDED: "方法学习候选已记录",
    FLOW_METHOD_STEP_CANDIDATE_RECORDED: "法步骤候选已记录",
    FLOW_METHOD_STEP_CANDIDATE_SKIPPED: "法步骤候选已跳过",
    FLOW_SPLIT_PROPOSAL_REQUESTED: "分业申请已请求",
    FLOW_SPLIT_PROPOSAL_RECEIVED: "分业申请已收到",
    FLOW_SPLIT_PROPOSAL_ACCEPTED: "分业申请已登记",
    FLOW_SPLIT_PROPOSAL_REJECTED: "分业申请已拒绝",
    FLOW_SPLIT_PROPOSAL_SKIPPED: "分业登记已跳过",
    FLOW_FRONTIER_DISPATCH_STARTED: "前沿子业调度已开始",
    FLOW_FRONTIER_DISPATCH_SKIPPED: "前沿子业调度已跳过",
    FLOW_FRONTIER_DISPATCH_FINISHED: "前沿子业调度已结束",
    FLOW_CHILD_JOB_DISPATCH_STARTED: "子业调度已开始",
    FLOW_CHILD_JOB_RESPONSE_RECEIVED: "子业响应已收到",
    FLOW_CHILD_RESULT_PACKAGE_SUBMITTED: "子业果包已提交",
    FLOW_CHILD_RESULT_PACKAGE_REJECTED: "子业果包已拒绝",
    FLOW_CHILD_PACKAGE_REVIEW_REQUESTED: "子业果包验收已请求",
    FLOW_CHILD_PACKAGE_REVIEW_RECEIVED: "子业果包验收已收到",
    FLOW_CHILD_PACKAGE_REVIEW_ACCEPTED: "子业果包验收已接收",
    FLOW_CHILD_PACKAGE_REVIEW_REJECTED: "子业果包验收已打回",
    FLOW_CHILD_PACKAGE_REPAIR_REQUESTED: "子业果包修复已请求",
    FLOW_CHILD_PACKAGE_REPAIR_RESPONSE_RECEIVED: "子业果包修复响应已收到",
    FLOW_CHILD_PACKAGE_REPAIR_PACKAGE_SUBMITTED: "子业果包修复包已提交",
    FLOW_CHILD_PACKAGE_REPAIR_REJECTED: "子业果包修复已拒绝",
    FLOW_CHILD_PACKAGE_REPAIR_LIMIT_REACHED: "子业果包修复上限已触达",
    FLOW_ACCEPTED_PARENT_REEVALUATION_RECORDED: "已接收果包父业重评估已记录",
    FLOW_PARENT_REEVALUATION_RECORDED: "父业重评估已记录",
    FLOW_PARENT_INTEGRATION_REQUESTED: "父业整合已请求",
    FLOW_PARENT_INTEGRATION_JOB_CREATED: "父业整合业已创建",
    FLOW_PARENT_INTEGRATION_RECEIVED: "父业整合响应已收到",
    FLOW_PARENT_INTEGRATION_CANDIDATE_SUBMITTED: "父业整合候选已提交",
    FLOW_PARENT_INTEGRATION_REJECTED: "父业整合已拒收",
    FLOW_PARENT_INTEGRATION_SKIPPED: "父业整合已跳过",
    FLOW_PARENT_INTEGRATION_REPAIR_JOB_CREATED: "父业整合修复业已创建",
    FLOW_PARENT_INTEGRATION_REPAIR_REQUESTED: "父业整合修复已请求",
    FLOW_PARENT_INTEGRATION_REPAIR_RECEIVED: "父业整合修复响应已收到",
    FLOW_PARENT_INTEGRATION_REPAIR_REJECTED: "父业整合修复已拒收",
    FLOW_PARENT_INTEGRATION_REPAIR_ACCEPTED: "父业整合修复已接收",
    FLOW_PARENT_INTEGRATION_FOLLOWUP_REGISTRATION_FINISHED: "父业整合后续分业登记已结束",
    FLOW_ADVANCEMENT_WAVE_STARTED: "推进波次已开始",
    FLOW_ADVANCEMENT_WAVE_FINISHED: "推进波次已结束",
    FLOW_ADVANCEMENT_LOOP_FINISHED: "推进循环已结束",
    FLOW_HUMAN_DECISION_REQUESTED: "人类裁决已请求",
    FLOW_HUMAN_DECISION_RETURNED: "人类裁决已回流",
    FLOW_RESULT_OUTPUT_RECORDED: "结果输出已记录",
    FLOW_CHAT_TURN_FINISHED: "对话轮次已完成",
    FLOW_CHAT_SESSION_FINISHED: "对话会话已结束",
    FLOW_RUN_FAILED: "运行失败",
    FLOW_RUN_FINISHED: "运行已完成",
    FLOW_SANDBOX_DESTROYED: "沙盒已销毁",
}

FIELD_LABELS = {
    "acceptance_feedback_job_id": "验收路由反馈业编号",
    "acceptance_latest_candidate_appearance_id": "验收路由最新候选相编号",
    "acceptance_repair_instruction": "验收路由修复指令",
    "acceptance_route_action": "验收路由动作",
    "acceptance_route_kind": "验收路由类型",
    "acceptance_routing_evidence": "验收路由证据",
    "acceptance_routing_evidence_appearance_id": "验收路由证据相编号",
    "acceptance_routing_judgment": "验收路由判断",
    "acceptance_routing_prompt": "验收路由请求内容",
    "advancement_stop_reason": "推进停止原因",
    "advancement_wave": "推进波次",
    "advancement_wave_count": "推进波次数量",
    "advancement_wave_limit": "推进波次上限",
    "appearance_id": "相编号",
    "appearance_kind": "相用途类型",
    "candidate_lineage": "候选血缘",
    "candidate_only": "仅为候选",
    "error": "错误",
    "feedback_job_id": "反馈业编号",
    "feedback_job_kind": "反馈业类型",
    "feedback_job_summary": "反馈业摘要",
    "feedback_job_target": "反馈业目标",
    "child_job_id": "子业编号",
    "child_job_response": "子业响应",
    "child_method_path": "子业方法路径",
    "child_package_repair_attempt": "子业果包修复轮次",
    "child_package_repair_instruction": "子业果包修复指令",
    "child_package_repair_job_id": "子业果包修复业编号",
    "child_package_repair_limit": "子业果包修复上限",
    "child_package_repair_response": "子业果包修复响应",
    "child_package_review_action": "子业果包验收动作",
    "child_package_review_checks": "子业果包验收检查",
    "child_package_review_evidence": "子业果包验收证据",
    "child_package_review_evidence_id": "子业果包验收证据相编号",
    "child_package_review_judgment": "子业果包验收判断",
    "child_package_review_prompt": "子业果包验收请求内容",
    "child_result_package": "子业果包",
    "child_result_package_candidate_id": "子业果包候选相编号",
    "child_result_package_evidence_id": "子业果包证据相编号",
    "frontier_dispatch_limit": "前沿调度上限",
    "frontier_dispatch_summary": "前沿调度摘要",
    "frontier_job_count": "前沿业数量",
    "human_decision_request_kind": "人类裁决请求类型",
    "input": "输入内容",
    "input_character_count": "输入字符数",
    "input_has_fenced_block": "输入含代码块",
    "input_has_markdown_heading": "输入含 Markdown 标题",
    "input_line_count": "输入行数",
    "input_sha256": "输入 SHA-256",
    "input_source": "输入来源",
    "job_id": "业编号",
    "job_state": "业状态",
    "job_target": "业目标",
    "job_tree_action": "业树动作",
    "judgment": "判断结果",
    "log_path": "JSONL 日志路径",
    "message_count": "消息数量",
    "method_checksum": "方法校验码",
    "method_law_appearance_refs": "法片段相引用",
    "method_law_appearance_id": "法片段相编号",
    "method_law_checksum": "法片段校验码",
    "method_law_content": "法片段内容",
    "method_law_fragment_count": "法片段数量",
    "method_law_id": "法片段编号",
    "method_law_level": "法片段标题层级",
    "method_law_manifest": "法片段清单",
    "method_law_order": "法片段顺序",
    "method_law_title": "法片段标题",
    "method_call_frame": "法调用帧",
    "method_call_frame_depth": "法调用帧深度",
    "method_call_frame_repeat_key": "法调用帧重复检测键",
    "method_invocation_input": "法调用输入",
    "method_output_contract": "法调用输出契约",
    "method_return_point": "法调用回流点",
    "method_binding_reason": "法绑定原因",
    "method_budget": "法调用预算",
    "method_name": "方法名称",
    "method_path": "方法路径",
    "method_size": "方法大小",
    "method_catalog": "可用法目录",
    "method_learning_candidate": "方法学习候选",
    "method_learning_candidate_appearance_id": "方法学习候选相编号",
    "method_step_candidate_count": "法步骤候选数量",
    "method_step_candidate_summary": "法步骤候选摘要",
    "method_step_registration_enabled": "法步骤登记已启用",
    "parent_job_id": "父业编号",
    "parent_reevaluation": "父业重评估",
    "accepted_parent_reevaluation": "已接收果包父业重评估",
    "accepted_child_packages": "已接收子业果包",
    "consumed_child_jobs": "已消费子业编号",
    "integration_open_gaps": "整合开放缺口",
    "parent_integration_candidate": "父业整合候选",
    "parent_integration_candidate_appearance_id": "父业整合候选相编号",
    "parent_integration_evidence": "父业整合证据",
    "parent_integration_evidence_appearance_id": "父业整合证据相编号",
    "parent_integration_job_id": "父业整合业编号",
    "parent_integration_prompt": "父业整合请求内容",
    "parent_integration_repair_attempt": "父业整合修复轮次",
    "parent_integration_repair_job_id": "父业整合修复业编号",
    "parent_integration_repair_limit": "父业整合修复上限",
    "parent_integration_repair_prompt": "父业整合修复请求内容",
    "parent_integration_repair_response": "父业整合修复响应",
    "parent_integration_response": "父业整合响应",
    "parent_integration_status": "父业整合状态",
    "parent_integration_summary": "父业整合摘要",
    "parent_consumption_summary": "父业消费摘要",
    "process_action": "运行动作",
    "process_detail": "运行细节",
    "process_phase": "运行阶段",
    "process_status": "运行状态",
    "process_step": "运行步骤",
    "provider_call_kind": "Provider 调用类型",
    "provider_content_character_count": "Provider 正文字符数",
    "provider_delta_character_count": "Provider 增量字符数",
    "provider_delta_index": "Provider 增量序号",
    "provider_delta_kind": "Provider 增量类型",
    "provider_delta_text": "Provider 增量内容",
    "provider_finish_reason": "Provider 结束原因",
    "provider_messages": "Provider 请求消息",
    "provider_message_count": "Provider 消息数量",
    "provider_message_roles": "Provider 消息角色",
    "provider_reasoning_character_count": "Provider 思考字符数",
    "provider_stream_chunk_count": "Provider 流式块数量",
    "repair_attempt": "修复轮次",
    "repair_attempt_count": "修复轮次数量",
    "repair_candidate_appearance_id": "修复候选相编号",
    "repair_child_job_id": "修复子业编号",
    "repair_feedback_job_id": "修复反馈裁决业编号",
    "repair_latest_candidate_appearance_id": "最新候选相编号",
    "repair_latest_status": "最新校验状态",
    "repair_loop_outcome": "修复循环结果",
    "repair_loop_summary": "修复循环摘要证据",
    "repair_max_attempts": "最大修复轮次",
    "repair_prompt": "修复请求内容",
    "repair_reason": "修复原因",
    "repair_response": "修复响应",
    "repair_source": "修复来源",
    "repairable_check_count": "可修复校验项数量",
    "repairable_checks": "可修复校验项",
    "readable_log_path": "可读日志路径",
    "reason": "原因",
    "decision_evidence_appearance_id": "裁决证据相编号",
    "decision_text": "裁决内容",
    "evidence_hardness": "证据硬度",
    "evidence_id": "证据相编号",
    "evidence_kind": "证据类型",
    "required_context_gaps": "缺失上下文",
    "response": "AI 响应",
    "result": "结果输出",
    "runtime_options": "运行选项",
    "review": "方法自验",
    "root_job_id": "根业编号",
    "sandbox_path": "沙盒路径",
    "split_proposal": "分业申请",
    "split_proposal_count": "分业申请数量",
    "split_proposal_decision": "分业申请处理结果",
    "split_proposal_index": "分业申请序号",
    "split_proposal_prompt": "分业申请请求内容",
    "split_proposal_rejection_reason": "分业申请拒绝原因",
    "split_proposal_response": "分业申请响应",
    "split_law": "分业判定律",
    "split_registration_summary": "分业登记摘要",
    "tree_snapshot": "业树快照",
    "turn": "轮次",
    "verification_candidate_appearance_id": "校验候选相编号",
    "verification_check_count": "校验项数量",
    "verification_child_job_id": "校验子业编号",
    "verification_evidence_appearance_id": "校验证据相编号",
    "verification_gaps": "校验缺口",
    "verification_job_id": "校验业编号",
    "verification_parent_evidence": "父业校验证据",
    "verification_parent_evidence_appearance_id": "父业校验证据相编号",
    "verification_report": "校验报告",
    "verification_status": "校验状态",
    "verification_target": "校验目标",
    "verification_feedback_evidence": "校验反馈裁决证据",
}

JOB_TREE_ACTION_LABELS = {
    "candidate_attached": "候选结果已挂载",
    "child_dispatch_started": "子业调度已开始",
    "child_package_accepted": "子业果包已接收",
    "child_package_repair_child_created": "子业果包修复业已创建",
    "child_package_repair_child_running": "子业果包修复业运行中",
    "child_package_repair_package_submitted": "子业果包修复包已提交",
    "child_package_repair_rejected": "子业果包修复已拒绝",
    "child_package_repair_limit_reached": "子业果包修复上限已触达",
    "child_package_rejected": "子业果包已拒绝",
    "child_package_review_rejected": "子业果包验收已打回",
    "child_package_review_requested": "子业果包验收已请求",
    "child_package_submitted": "子业果包已提交",
    "evidence_attached": "证据已挂载",
    "feedback_child_created": "反馈子业已创建",
    "feedback_child_skipped": "反馈子业已跳过",
    "frontier_dispatch_finished": "前沿子业调度已结束",
    "frontier_dispatch_skipped": "前沿子业调度已跳过",
    "frontier_dispatch_started": "前沿子业调度已开始",
    "acceptance_route_continued": "验收路由继续运行",
    "job_ready": "业已就绪",
    "job_running": "业运行中",
    "method_call_frame_opened": "法调用帧已打开",
    "method_learning_candidate_recorded": "方法学习候选已记录",
    "method_step_child_created": "法步骤候选子业已创建",
    "parent_verification_evidence_attached": "父业校验证据已挂载",
    "parent_reevaluation_recorded": "父业重评估已记录",
    "accepted_parent_reevaluation_recorded": "已接收果包父业重评估已记录",
    "human_decision_child_created": "人类裁决子业已创建",
    "parent_integration_job_created": "父业整合业已创建",
    "parent_integration_candidate_submitted": "父业整合候选已提交",
    "parent_integration_rejected": "父业整合已拒收",
    "parent_integration_requested": "父业整合已请求",
    "parent_integration_repair_child_created": "父业整合修复业已创建",
    "parent_integration_repair_accepted": "父业整合修复已接收",
    "parent_integration_repair_rejected": "父业整合修复已拒收",
    "parent_integration_skipped": "父业整合已跳过",
    "parent_integration_followup_registered": "父业整合后续分业登记已记录",
    "root_created": "根业已创建",
    "repair_candidate_attached": "修复候选已挂载",
    "repair_child_created": "修复子业已创建",
    "repair_child_ready": "修复子业已就绪",
    "repair_child_running": "修复子业运行中",
    "repair_verification_evidence_attached": "修复校验证据已挂载",
    "split_proposal_child_created": "分业申请子业已创建",
    "split_proposal_rejected": "分业申请已拒绝",
    "split_proposal_skipped": "分业登记已跳过",
    "verification_candidate_attached": "校验报告候选已挂载",
    "verification_child_created": "校验子业已创建",
    "verification_child_ready": "校验子业已就绪",
    "verification_child_running": "校验子业运行中",
    "verification_evidence_attached": "校验证据已挂载",
    "verification_feedback_child_created": "校验反馈裁决子业已创建",
}


@dataclass(frozen=True)
class FlowEvent:
    event_type: str
    message: str
    timestamp: str
    data: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_type": self.event_type,
                "message": self.message,
                "timestamp": self.timestamp,
                "data": self.data,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class FlowWriter:
    def __init__(
        self,
        sandbox_path: Path,
        diagnostic_log_path: Path | None = None,
        readable_log_path: Path | None = None,
    ) -> None:
        self.path = flow_events_path(sandbox_path)
        self.diagnostic_log_path = diagnostic_log_path
        self.readable_log_path = readable_log_path
        self._readable_header_written = False

    def write(self, event_type: str, message: str, **data: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = FlowEvent(
            event_type=event_type,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(event.to_json())
            stream.write("\n")
        if self.diagnostic_log_path is not None:
            self.diagnostic_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.diagnostic_log_path.open("a", encoding="utf-8") as stream:
                stream.write(event.to_json())
                stream.write("\n")
        if self.readable_log_path is not None:
            self._write_readable_event(event)

    def _write_readable_event(self, event: FlowEvent) -> None:
        self.readable_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._readable_header_written:
            fresh = not self.readable_log_path.exists()
            with self.readable_log_path.open(
                "a", encoding="utf-8-sig" if fresh else "utf-8"
            ) as stream:
                if fresh:
                    jsonl_path = self.diagnostic_log_path or self.path
                    stream.write(
                        "# 金箍 AI 沙盒可读日志\n\n"
                        f"- JSONL 机器日志：`{jsonl_path}`\n"
                        f"- 沙盒实时事件流：`{self.path}`\n"
                        f"- 人类可读日志：`{self.readable_log_path}`\n"
                        "- 文件编码：UTF-8 with BOM\n\n"
                    )
            self._readable_header_written = True

        with self.readable_log_path.open("a", encoding="utf-8") as stream:
            stream.write(format_readable_event(event.to_dict()))
            stream.write("\n")


def new_diagnostic_log_path(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return log_dir / f"ai-run-{timestamp}-{uuid.uuid4().hex}.jsonl"


def readable_log_path_for(diagnostic_log_path: Path) -> Path:
    return diagnostic_log_path.with_suffix(".md")


def format_readable_event(event: dict[str, object]) -> str:
    timestamp = str(event.get("timestamp", ""))
    event_type = str(event.get("event_type", ""))
    event_label = EVENT_LABELS.get(event_type, event_type)
    message = readable_message(event_type, str(event.get("message", "")))
    data = event.get("data") or {}
    if not isinstance(data, dict):
        data = {"data": data}

    lines = [f"## {timestamp} | {event_label}（{event_type}）", "", f"说明：{message}"]
    if data:
        lines.append("")
        for key in sorted(data):
            value = "" if data[key] is None else str(data[key])
            value = readable_field_value(str(key), value)
            label = readable_field_label(str(key))
            if _should_render_as_block(key, value):
                lines.append(f"### {label}")
                lines.append("")
                lines.extend(_encoding_warning_lines(value))
                fence = _dynamic_fence(value)
                lines.append(f"{fence}text")
                lines.append(value)
                lines.append(f"{fence}")
                lines.append("")
            else:
                warning = " 编码警告：该字段包含连续问号，原始中文可能在进入系统前已经损坏。" if has_suspicious_question_marks(value) else ""
                lines.append(f"- {label}: {value}{warning}")
    else:
        lines.append("")
        lines.append("- 数据：无")
    return "\n".join(lines).rstrip() + "\n"


def readable_message(event_type: str, fallback: str) -> str:
    return EVENT_LABELS.get(event_type, fallback)


def readable_field_label(key: str) -> str:
    label = FIELD_LABELS.get(key, key)
    return f"{label}（{key}）"


def readable_field_value(key: str, value: str) -> str:
    if key == "job_tree_action":
        label = JOB_TREE_ACTION_LABELS.get(value)
        if label:
            return f"{label}（{value}）"
    return value


def input_provenance_fields(input_text: str, *, input_source: str) -> dict[str, str]:
    return {
        "input_source": input_source,
        "input_character_count": str(len(input_text)),
        "input_line_count": str(len(input_text.splitlines()) or (1 if input_text else 0)),
        "input_sha256": hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        "input_has_markdown_heading": str(bool(MARKDOWN_HEADING.search(input_text))).lower(),
        "input_has_fenced_block": str(bool(FENCED_BLOCK.search(input_text))).lower(),
    }


def has_suspicious_question_marks(value: str) -> bool:
    return bool(SUSPICIOUS_QUESTION_MARKS.search(value))


def _encoding_warning_lines(value: str) -> list[str]:
    if not has_suspicious_question_marks(value):
        return []
    return [
        "编码警告：该字段包含连续问号，原始中文可能在进入系统前已经损坏。",
        "",
    ]


def _should_render_as_block(key: str, value: str) -> bool:
    if "\n" in value:
        return True
    if len(value) > 120:
        return True
    return key in {
        "input",
        "response",
        "result",
        "review",
        "method_law_content",
        "method_law_manifest",
        "method_law_appearance_refs",
        "method_call_frame",
        "method_invocation_input",
        "method_output_contract",
        "method_binding_reason",
        "method_budget",
        "method_catalog",
        "method_learning_candidate",
        "method_step_candidate_summary",
        "runtime_options",
        "candidate_lineage",
        "child_job_response",
        "child_package_repair_instruction",
        "child_package_repair_response",
        "child_package_review_checks",
        "child_package_review_evidence",
        "child_package_review_judgment",
        "child_package_review_prompt",
        "child_result_package",
        "accepted_parent_reevaluation",
        "accepted_child_packages",
        "frontier_dispatch_summary",
        "integration_open_gaps",
        "parent_reevaluation",
        "parent_integration_candidate",
        "parent_integration_evidence",
        "parent_integration_prompt",
        "parent_integration_repair_prompt",
        "parent_integration_repair_response",
        "parent_integration_response",
        "parent_integration_summary",
        "parent_consumption_summary",
        "provider_delta_text",
        "repair_prompt",
        "repair_response",
        "repair_loop_summary",
        "repairable_checks",
        "judgment",
        "required_context_gaps",
        "split_law",
        "split_proposal",
        "split_proposal_prompt",
        "split_proposal_response",
        "split_registration_summary",
        "feedback_job_target",
        "feedback_job_summary",
        "job_target",
        "tree_snapshot",
        "provider_messages",
        "acceptance_routing_prompt",
        "acceptance_routing_judgment",
        "acceptance_routing_evidence",
        "acceptance_repair_instruction",
        "verification_gaps",
        "verification_parent_evidence",
        "verification_report",
        "verification_feedback_evidence",
    }


def _dynamic_fence(value: str) -> str:
    longest_run = 0
    current = 0
    for char in value:
        if char == "`":
            current += 1
            longest_run = max(longest_run, current)
        else:
            current = 0
    return "`" * max(3, longest_run + 1)


def tail_flow_events(
    sandbox_path: Path,
    *,
    poll_seconds: float = 0.2,
    wait_seconds: float = 30.0,
) -> Iterator[dict]:
    path = flow_events_path(sandbox_path)
    deadline = time.monotonic() + wait_seconds
    position = 0
    seen_terminal = False

    while True:
        if path.exists():
            deadline = time.monotonic() + wait_seconds
            with path.open("r", encoding="utf-8") as stream:
                stream.seek(position)
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    position = stream.tell()
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    yield event
                    if event.get("event_type") in TERMINAL_EVENTS:
                        seen_terminal = True
                if seen_terminal:
                    return
        elif seen_terminal or (not sandbox_path.exists() and time.monotonic() > deadline):
            return

        if time.monotonic() > deadline and not sandbox_path.exists():
            return
        time.sleep(poll_seconds)
