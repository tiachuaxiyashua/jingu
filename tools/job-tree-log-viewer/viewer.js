"use strict";

const EVENT_LABELS = {
  sandbox_created: "沙盒已创建",
  runtime_initialized: "运行库已初始化",
  method_source_resolved: "方法来源已解析",
  method_context_loaded: "方法上下文已加载",
  method_law_fragment_loaded: "法片段已加载",
  method_law_fragment_bound: "法片段已绑定",
  method_context_injected: "方法上下文已注入",
  root_job_created: "根业已创建",
  job_ready: "业已就绪",
  job_running: "业运行中",
  job_tree_management_recorded: "业树管理已记录",
  job_tree_snapshot_recorded: "业树快照已记录",
  process_step_recorded: "运行步骤已记录",
  user_input_recorded: "用户输入已记录",
  input_provenance_recorded: "输入来源已记录",
  provider_messages_recorded: "Provider 请求消息已记录",
  provider_stream_delta_received: "Provider 流式增量已收到",
  provider_stream_finished: "Provider 流式输出已结束",
  ai_request_started: "AI 请求已开始",
  ai_response_received: "AI 响应已收到",
  candidate_submitted: "候选结果已提交",
  evidence_submitted: "证据已提交",
  verification_job_created: "候选校验业已创建",
  verification_tool_started: "候选校验工具已启动",
  verification_result_recorded: "候选校验结果已记录",
  verification_evidence_submitted: "候选校验证据已提交",
  parent_verification_evidence_submitted: "父业校验证据已回流",
  repair_job_created: "修复业已创建",
  repair_request_prepared: "修复请求已准备",
  repair_response_received: "修复响应已收到",
  repair_candidate_submitted: "修复候选已提交",
  repair_loop_finished: "修复循环已结束",
  verification_feedback_job_created: "校验反馈裁决业已创建",
  acceptance_routing_requested: "验收路由已请求",
  acceptance_routing_received: "验收路由已收到",
  acceptance_routing_evidence_submitted: "验收路由证据已提交",
  acceptance_routing_skipped: "验收路由已继续",
  feedback_judgment_requested: "反馈判断已请求",
  feedback_judgment_received: "反馈判断已收到",
  feedback_job_created: "反馈业已创建",
  feedback_job_skipped: "反馈业已跳过",
  method_self_review_requested: "方法自验已请求",
  method_self_review_received: "方法自验已收到",
  method_update_candidate_recorded: "方法更新候选已记录",
  split_proposal_requested: "分业申请已请求",
  split_proposal_received: "分业申请已收到",
  split_proposal_accepted: "分业申请已登记",
  split_proposal_rejected: "分业申请已拒绝",
  split_proposal_skipped: "分业登记已跳过",
  frontier_dispatch_started: "前沿子业调度已开始",
  frontier_dispatch_skipped: "前沿子业调度已跳过",
  frontier_dispatch_finished: "前沿子业调度已结束",
  child_job_dispatch_started: "子业调度已开始",
  child_job_response_received: "子业响应已收到",
  child_result_package_submitted: "子业果包已提交",
  child_result_package_rejected: "子业果包已拒绝",
  child_package_review_requested: "子业果包验收已请求",
  child_package_review_received: "子业果包验收已收到",
  child_package_review_accepted: "子业果包验收已接收",
  child_package_review_rejected: "子业果包验收已打回",
  child_package_repair_requested: "子业果包修复已请求",
  child_package_repair_response_received: "子业果包修复响应已收到",
  child_package_repair_package_submitted: "子业果包修复包已提交",
  child_package_repair_rejected: "子业果包修复已拒绝",
  child_package_repair_limit_reached: "子业果包修复上限已触达",
  accepted_parent_reevaluation_recorded: "已接收果包父业重评估已记录",
  parent_reevaluation_recorded: "父业重评估已记录",
  parent_integration_requested: "父业整合已请求",
  parent_integration_received: "父业整合响应已收到",
  parent_integration_candidate_submitted: "父业整合候选已提交",
  parent_integration_rejected: "父业整合已拒收",
  parent_integration_skipped: "父业整合已跳过",
  parent_integration_followup_registration_finished: "父业整合后续分业登记已结束",
  result_output_recorded: "结果输出已记录",
  chat_turn_finished: "对话轮次已完成",
  chat_session_finished: "对话会话已结束",
  run_failed: "运行失败",
  run_finished: "运行已完成",
  sandbox_destroyed: "沙盒已销毁",
};

const ACTION_LABELS = {
  root_created: "根业已创建",
  job_ready: "业已就绪",
  job_running: "业运行中",
  candidate_attached: "候选结果已挂载",
  evidence_attached: "证据已挂载",
  verification_child_created: "校验子业已创建",
  verification_child_ready: "校验子业已就绪",
  verification_child_running: "校验子业运行中",
  verification_candidate_attached: "校验报告候选已挂载",
  verification_evidence_attached: "校验证据已挂载",
  parent_verification_evidence_attached: "父业校验证据已回流",
  repair_verification_evidence_attached: "修复校验证据已挂载",
  repair_child_created: "修复子业已创建",
  repair_child_ready: "修复子业已就绪",
  repair_child_running: "修复子业运行中",
  repair_candidate_attached: "修复候选已挂载",
  verification_feedback_child_created: "校验反馈裁决子业已创建",
  feedback_child_created: "反馈子业已创建",
  feedback_child_skipped: "反馈子业已跳过",
  acceptance_route_continued: "验收路由继续",
  split_proposal_child_created: "分业申请子业已创建",
  split_proposal_rejected: "分业申请已拒绝",
  split_proposal_skipped: "分业登记已跳过",
  frontier_dispatch_started: "前沿子业调度已开始",
  frontier_dispatch_skipped: "前沿子业调度已跳过",
  frontier_dispatch_finished: "前沿子业调度已结束",
  child_dispatch_started: "子业调度已开始",
  child_package_submitted: "子业果包已提交",
  child_package_rejected: "子业果包已拒绝",
  child_package_review_requested: "子业果包验收已请求",
  child_package_review_rejected: "子业果包验收已打回",
  child_package_accepted: "子业果包已接收",
  child_package_repair_child_created: "子业果包修复业已创建",
  child_package_repair_child_running: "子业果包修复业运行中",
  child_package_repair_package_submitted: "子业果包修复包已提交",
  child_package_repair_rejected: "子业果包修复已拒绝",
  child_package_repair_limit_reached: "子业果包修复上限已触达",
  parent_reevaluation_recorded: "父业重评估已记录",
  accepted_parent_reevaluation_recorded: "已接收果包父业重评估已记录",
  parent_integration_requested: "父业整合已请求",
  parent_integration_candidate_submitted: "父业整合候选已提交",
  parent_integration_rejected: "父业整合已拒收",
  parent_integration_skipped: "父业整合已跳过",
  parent_integration_followup_registered: "父业整合后续分业登记已记录",
};

const STATE_LABELS = {
  draft: "草稿",
  ready: "就绪",
  running: "运行中",
  blocked: "阻塞中",
  reviewing: "评审中",
  accepted: "已接收",
  rejected: "已拒收",
  waiting_human: "等待人裁",
  abandoned: "废弃",
};

const FIELD_LABELS = {
  input: "用户输入",
  provider_messages: "Provider 请求消息",
  parent_integration_prompt: "父业整合请求",
  accepted_child_packages: "已接收子业果包",
  child_package_review_prompt: "子业果包验收请求",
  split_proposal_prompt: "分业申请请求",
  repair_prompt: "修复请求",
  acceptance_routing_prompt: "验收路由请求",
  method_law_content: "法片段内容",
  method_call_frame: "法调用帧",
  response: "AI 响应",
  child_job_response: "子业响应",
  child_result_package: "子业果包",
  child_package_review_judgment: "子业果包验收判断",
  child_package_repair_response: "子业果包修复响应",
  parent_integration_response: "父业整合响应",
  parent_integration_candidate: "父业整合候选",
  split_proposal_response: "分业申请响应",
  repair_response: "修复响应",
  verification_report: "校验报告",
  result: "结果输出",
  evidence: "证据",
  child_package_review_evidence: "子业果包验收证据",
  accepted_parent_reevaluation: "已接收果包父业重评估",
  parent_reevaluation: "父业重评估",
  parent_integration_evidence: "父业整合证据",
  acceptance_routing_evidence: "验收路由证据",
  verification_parent_evidence: "父业校验证据",
  verification_gaps: "校验缺口",
  job_tree_action: "业树动作",
  job_state: "业状态",
  process_step: "运行步骤",
  process_phase: "运行阶段",
  process_action: "运行动作",
  process_status: "运行状态",
  job_id: "业编号",
  parent_job_id: "父业编号",
  child_job_id: "子业编号",
  root_job_id: "根业编号",
  appearance_id: "相编号",
  reason: "原因",
  parent_integration_status: "父业整合状态",
  consumed_child_jobs: "已消费子业编号",
  integration_open_gaps: "整合开放缺口",
  parent_integration_summary: "父业整合摘要",
  acceptance_route_action: "验收路由动作",
  acceptance_route_kind: "验收路由类型",
  verification_status: "校验状态",
};

const STEP_FIELD_GROUPS = {
  inputs: [
    "input",
    "provider_messages",
    "parent_integration_prompt",
    "accepted_child_packages",
    "child_package_review_prompt",
    "split_proposal_prompt",
    "repair_prompt",
    "acceptance_routing_prompt",
    "method_law_content",
    "method_call_frame",
  ],
  outputs: [
    "response",
    "child_job_response",
    "child_result_package",
    "child_package_review_judgment",
    "child_package_repair_response",
    "parent_integration_response",
    "parent_integration_candidate",
    "split_proposal_response",
    "repair_response",
    "verification_report",
    "result",
  ],
  evidence: [
    "evidence",
    "child_package_review_evidence",
    "accepted_parent_reevaluation",
    "parent_reevaluation",
    "parent_integration_evidence",
    "acceptance_routing_evidence",
    "verification_parent_evidence",
    "verification_gaps",
  ],
  state: [
    "job_tree_action",
    "job_state",
    "process_step",
    "process_phase",
    "process_action",
    "process_status",
    "job_id",
    "parent_job_id",
    "child_job_id",
    "root_job_id",
    "appearance_id",
    "parent_integration_status",
    "consumed_child_jobs",
    "integration_open_gaps",
    "parent_integration_summary",
    "acceptance_route_action",
    "acceptance_route_kind",
    "verification_status",
    "reason",
  ],
};

const IMPORTANT_EVENTS = new Set([
  "root_job_created",
  "job_ready",
  "job_running",
  "job_tree_management_recorded",
  "job_tree_snapshot_recorded",
  "candidate_submitted",
  "evidence_submitted",
  "verification_job_created",
  "verification_result_recorded",
  "verification_evidence_submitted",
  "parent_verification_evidence_submitted",
  "repair_job_created",
  "repair_request_prepared",
  "repair_response_received",
  "repair_candidate_submitted",
  "repair_loop_finished",
  "verification_feedback_job_created",
  "acceptance_routing_requested",
  "acceptance_routing_received",
  "acceptance_routing_evidence_submitted",
  "acceptance_routing_skipped",
  "feedback_job_created",
  "split_proposal_requested",
  "split_proposal_accepted",
  "split_proposal_rejected",
  "split_proposal_skipped",
  "frontier_dispatch_started",
  "frontier_dispatch_finished",
  "child_job_dispatch_started",
  "child_result_package_submitted",
  "child_result_package_rejected",
  "child_package_review_requested",
  "child_package_review_accepted",
  "child_package_review_rejected",
  "accepted_parent_reevaluation_recorded",
  "parent_reevaluation_recorded",
  "parent_integration_requested",
  "parent_integration_candidate_submitted",
  "parent_integration_rejected",
  "parent_integration_skipped",
  "parent_integration_followup_registration_finished",
  "result_output_recorded",
  "chat_turn_finished",
  "chat_session_finished",
  "run_failed",
  "run_finished",
  "sandbox_destroyed",
]);

const VIEWER_STATE = {
  fileName: "",
  events: [],
  cursor: 0,
  selectedJobId: "",
  playTimer: null,
};

function parseJsonl(text) {
  const normalized = String(text || "").replace(/^\uFEFF/, "");
  const events = [];
  const lines = normalized.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) {
      continue;
    }
    let parsed;
    try {
      parsed = JSON.parse(line);
    } catch (error) {
      const reason = error && error.message ? error.message : String(error);
      throw new Error(`第 ${index + 1} 行不是合法 JSON：${reason}`);
    }
    events.push(normalizeEvent(parsed, events.length));
  }
  if (!events.length) {
    throw new Error("文件中没有可解析的 JSONL 事件。");
  }
  return events;
}

function normalizeEvent(event, index) {
  const data = event && typeof event.data === "object" && event.data !== null ? event.data : {};
  return {
    index,
    event_type: stringValue(event && event.event_type),
    message: stringValue(event && event.message),
    timestamp: stringValue(event && event.timestamp),
    data,
    raw: event,
  };
}

function projectEvents(events, cursor) {
  const projection = emptyProjection();
  const end = Math.max(0, Math.min(cursor, events.length));
  for (let index = 0; index < end; index += 1) {
    applyEvent(projection, events[index]);
  }
  projection.nodes = Array.from(projection.nodeMap.values());
  projection.links = Array.from(projection.linkMap.values());
  assignDepths(projection);
  projection.currentEvent = end > 0 ? events[end - 1] : null;
  projection.cursor = end;
  projection.totalEvents = events.length;
  return projection;
}

function emptyProjection() {
  return {
    nodeMap: new Map(),
    linkMap: new Map(),
    nodes: [],
    links: [],
    roots: new Set(),
    stats: {
      events: 0,
      jobs: 0,
      candidates: 0,
      evidence: 0,
      verification: 0,
      repairs: 0,
      feedback: 0,
      routes: 0,
      childReviews: 0,
      parentIntegrations: 0,
      snapshots: 0,
    },
    milestones: {
      routeActions: [],
      repairCreated: 0,
      feedbackCreated: 0,
      childPackageReviews: [],
      parentIntegrations: [],
      verificationResults: [],
      resultOutput: false,
      runFinished: false,
      chatFinished: false,
      runFailed: false,
      sandboxDestroyed: false,
    },
    warnings: [],
  };
}

function applyEvent(projection, event) {
  projection.stats.events += 1;
  const data = event.data || {};

  if (event.event_type === "root_job_created") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.kind = "root";
      node.state = node.state || "draft";
      node.rootJobId = node.rootJobId || data.job_id;
      node.events.push(event.index);
      addNodeAction(node, event, "根业已创建");
      projection.roots.add(node.id);
    }
  }

  if (event.event_type === "job_ready" || event.event_type === "job_running") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.state = event.event_type === "job_ready" ? "ready" : "running";
      mergeNodeFields(node, data);
      addNodeAction(node, event, eventLabel(event));
    }
  }

  if (event.event_type === "candidate_submitted") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.candidates.add(stringValue(data.appearance_id));
      node.state = node.state || "reviewing";
      addNodeAction(node, event, "候选结果已提交");
    }
  }

  if (event.event_type === "evidence_submitted") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.evidence.add(stringValue(data.appearance_id));
      addNodeAction(node, event, "证据已提交");
    }
  }

  if (event.event_type === "verification_job_created") {
    const parentId = stringValue(data.parent_job_id || data.job_id);
    const childId = stringValue(data.verification_job_id || data.verification_child_job_id);
    const child = ensureNode(projection, childId);
    if (child) {
      child.kind = "verification";
      child.parentJobId = child.parentJobId || parentId;
      child.rootJobId = child.rootJobId || rootFrom(data, parentId);
      child.target = stringValue(data.verification_target || child.target || "校验候选结果");
      child.state = child.state || "draft";
      child.candidates.add(stringValue(data.appearance_id));
      addLink(projection, parentId, child.id);
      addNodeAction(child, event, "候选校验业已创建");
    }
  }

  if (event.event_type === "repair_job_created") {
    const node = ensureNode(projection, data.job_id || data.repair_job_id || data.repair_child_job_id);
    if (node) {
      node.kind = "repair";
      node.parentJobId = node.parentJobId || stringValue(data.parent_job_id);
      node.rootJobId = node.rootJobId || rootFrom(data, node.parentJobId);
      node.target = node.target || "修复候选问题";
      node.state = node.state || "draft";
      addLink(projection, node.parentJobId, node.id);
      addNodeAction(node, event, "修复业已创建");
      projection.milestones.repairCreated += 1;
    }
  }

  if (event.event_type === "feedback_job_created" || event.event_type === "verification_feedback_job_created") {
    const childId = stringValue(data.feedback_job_id || data.acceptance_feedback_job_id || data.repair_feedback_job_id);
    const node = ensureNode(projection, childId);
    if (node) {
      node.kind = "feedback";
      node.parentJobId = node.parentJobId || stringValue(data.job_id || data.parent_job_id);
      node.rootJobId = node.rootJobId || rootFrom(data, node.parentJobId);
      node.target = stringValue(data.feedback_job_target || data.feedback_job_summary || node.target || "反馈业");
      node.state = node.state || "draft";
      node.feedbackKind = stringValue(data.feedback_job_kind || data.acceptance_route_kind);
      addLink(projection, node.parentJobId, node.id);
      addNodeAction(node, event, "反馈业已创建");
      projection.milestones.feedbackCreated += 1;
    }
  }

  if (event.event_type === "job_tree_management_recorded") {
    applyJobTreeManagement(projection, event);
  }

  if (event.event_type === "job_tree_snapshot_recorded") {
    projection.stats.snapshots += 1;
    applySnapshotFallback(projection, event);
  }

  if (event.event_type === "verification_result_recorded") {
    const node = ensureNode(projection, data.job_id);
    const status = stringValue(data.verification_status || statusFromReport(data.verification_report));
    if (node) {
      node.verificationStatus = status || node.verificationStatus;
      node.kind = node.kind === "unknown" ? "verification" : node.kind;
      addNodeAction(node, event, status ? `校验结果：${status}` : "校验结果已记录");
    }
    projection.milestones.verificationResults.push({ index: event.index, status });
  }

  if (event.event_type === "repair_candidate_submitted" || event.event_type === "repair_response_received") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.kind = "repair";
      if (data.repair_candidate_appearance_id || data.appearance_id) {
        node.candidates.add(stringValue(data.repair_candidate_appearance_id || data.appearance_id));
      }
      addNodeAction(node, event, eventLabel(event));
    }
  }

  if (event.event_type === "acceptance_routing_received") {
    const route = acceptanceRouteFrom(data);
    projection.milestones.routeActions.push({
      index: event.index,
      action: route.action,
      kind: route.kind,
      reason: stringValue(data.reason || route.reason),
    });
    const node = ensureNode(projection, data.job_id);
    if (node) {
      node.lastRouteAction = route.action;
      node.lastRouteKind = route.kind;
      node.lastRouteReason = stringValue(data.reason || route.reason);
      addNodeAction(node, event, `验收路由：${route.action || "未知"}`);
    }
  }

  if (event.event_type === "acceptance_routing_requested" || event.event_type === "acceptance_routing_evidence_submitted" || event.event_type === "acceptance_routing_skipped") {
    const node = ensureNode(projection, data.job_id);
    if (node) {
      addNodeAction(node, event, eventLabel(event));
      if (data.appearance_id) {
        node.evidence.add(stringValue(data.appearance_id));
      }
    }
  }

  if (event.event_type.startsWith("child_package_review_")) {
    projection.milestones.childPackageReviews.push({
      index: event.index,
      action: stringValue(data.child_package_review_action || data.parent_integration_status || event.event_type),
      childJobId: stringValue(data.child_job_id || data.job_id),
    });
    const node = ensureNode(projection, data.child_job_id || data.job_id);
    if (node) {
      node.kind = node.kind === "unknown" ? "child" : node.kind;
      addNodeAction(node, event, eventLabel(event));
      if (event.event_type === "child_package_review_accepted") {
        node.state = "accepted";
      }
    }
  }

  if (event.event_type.startsWith("parent_integration_")) {
    projection.milestones.parentIntegrations.push({
      index: event.index,
      status: stringValue(data.parent_integration_status || event.event_type),
      parentJobId: stringValue(data.parent_job_id || data.job_id),
    });
    const node = ensureNode(projection, data.parent_job_id || data.job_id);
    if (node) {
      addNodeAction(node, event, eventLabel(event));
      if (data.parent_integration_candidate_appearance_id) {
        node.candidates.add(stringValue(data.parent_integration_candidate_appearance_id));
        node.state = "reviewing";
      }
      if (data.parent_integration_evidence_appearance_id) {
        node.evidence.add(stringValue(data.parent_integration_evidence_appearance_id));
      }
    }
  }

  if (event.event_type === "result_output_recorded") {
    projection.milestones.resultOutput = true;
    const node = ensureNode(projection, data.job_id);
    if (node) {
      addNodeAction(node, event, "结果输出已记录");
    }
  }

  if (event.event_type === "run_finished") {
    projection.milestones.runFinished = true;
    const node = ensureNode(projection, data.job_id);
    if (node) {
      addNodeAction(node, event, "运行已完成");
    }
  }

  if (event.event_type === "chat_session_finished") {
    projection.milestones.chatFinished = true;
  }

  if (event.event_type === "run_failed") {
    projection.milestones.runFailed = true;
  }

  if (event.event_type === "sandbox_destroyed") {
    projection.milestones.sandboxDestroyed = true;
  }
}

function applyJobTreeManagement(projection, event) {
  const data = event.data || {};
  const action = stringValue(data.job_tree_action);
  const nodeId = stringValue(data.job_id);
  const childId = stringValue(data.child_job_id);
  const parentId = stringValue(data.parent_job_id);
  const targetId = nodeId || childId;
  const node = ensureNode(projection, targetId);
  if (!node) {
    projection.warnings.push(`第 ${event.index + 1} 条业树事件缺少业编号。`);
    return;
  }

  mergeNodeFields(node, data);
  node.kind = classifyKind(node, action, data);
  addNodeAction(node, event, ACTION_LABELS[action] || action || "业树动作");

  if (parentId && childId) {
    addLink(projection, parentId, childId);
    const child = ensureNode(projection, childId);
    if (child) {
      child.parentJobId = child.parentJobId || parentId;
      child.rootJobId = child.rootJobId || rootFrom(data, parentId);
      if (data.job_target && child.id === nodeId) {
        child.target = stringValue(data.job_target);
      }
    }
  } else if (parentId && node.id !== parentId) {
    addLink(projection, parentId, node.id);
  }

  if (action === "root_created") {
    projection.roots.add(node.id);
    node.kind = "root";
  }

  if (data.appearance_id) {
    attachAppearance(node, action, stringValue(data.appearance_id));
  }
}

function applySnapshotFallback(projection, event) {
  const snapshotText = event.data && event.data.tree_snapshot;
  if (!snapshotText) {
    return;
  }
  const snapshot = tryParseJson(snapshotText);
  if (!snapshot || typeof snapshot !== "object") {
    projection.warnings.push(`第 ${event.index + 1} 条业树快照无法解析。`);
    return;
  }
  const nodes = Array.isArray(snapshot.nodes) ? snapshot.nodes : [];
  for (const item of nodes) {
    const node = ensureNode(projection, item.job_id);
    if (!node) {
      continue;
    }
    node.parentJobId = node.parentJobId || stringValue(item.parent_job_id);
    node.rootJobId = node.rootJobId || stringValue(item.root_job_id);
    node.state = node.state || stringValue(item.state);
    node.target = node.target || stringValue(item.target);
    node.kind = classifyKind(node, "", { job_target: node.target });
    if (item.candidate_appearance_id) {
      node.candidates.add(stringValue(item.candidate_appearance_id));
    }
    if (item.evidence_appearance_id) {
      node.evidence.add(stringValue(item.evidence_appearance_id));
    }
  }
  const links = Array.isArray(snapshot.links) ? snapshot.links : [];
  for (const link of links) {
    addLink(projection, link.parent_job_id, link.child_job_id);
  }
}

function ensureNode(projection, id) {
  const nodeId = stringValue(id);
  if (!nodeId) {
    return null;
  }
  if (!projection.nodeMap.has(nodeId)) {
    projection.nodeMap.set(nodeId, {
      id: nodeId,
      parentJobId: "",
      rootJobId: "",
      state: "",
      target: "",
      kind: "unknown",
      candidates: new Set(),
      evidence: new Set(),
      appearances: new Set(),
      actions: [],
      events: [],
      depth: 0,
      order: projection.nodeMap.size,
      verificationStatus: "",
      feedbackKind: "",
      lastRouteAction: "",
      lastRouteKind: "",
      lastRouteReason: "",
    });
  }
  return projection.nodeMap.get(nodeId);
}

function mergeNodeFields(node, data) {
  if (!node || !data) {
    return;
  }
  node.parentJobId = node.parentJobId || stringValue(data.parent_job_id);
  node.rootJobId = node.rootJobId || stringValue(data.root_job_id);
  node.state = stringValue(data.job_state || node.state);
  node.target = stringValue(data.job_target || data.verification_target || data.feedback_job_target || node.target);
}

function addLink(projection, parentId, childId) {
  const parent = stringValue(parentId);
  const child = stringValue(childId);
  if (!parent || !child || parent === child) {
    return;
  }
  ensureNode(projection, parent);
  ensureNode(projection, child);
  projection.linkMap.set(`${parent}>${child}`, { parent, child });
}

function addNodeAction(node, event, label) {
  if (!node) {
    return;
  }
  node.events.push(event.index);
  node.actions.push({
    index: event.index,
    label: stringValue(label || eventLabel(event)),
    event_type: event.event_type,
    timestamp: event.timestamp,
  });
}

function attachAppearance(node, action, appearanceId) {
  if (!appearanceId) {
    return;
  }
  if (String(action).includes("candidate")) {
    node.candidates.add(appearanceId);
  } else if (String(action).includes("evidence")) {
    node.evidence.add(appearanceId);
  } else {
    node.appearances.add(appearanceId);
  }
}

function classifyKind(node, action, data) {
  if (node.kind && node.kind !== "unknown") {
    if (action === "root_created") {
      return "root";
    }
    return node.kind;
  }
  const target = stringValue(data && (data.job_target || data.verification_target || data.feedback_job_target));
  if (action === "root_created") {
    return "root";
  }
  if (action.startsWith("verification_child") || target.includes("校验")) {
    return "verification";
  }
  if (action.startsWith("repair_child") || target.includes("修复")) {
    return "repair";
  }
  if (action.startsWith("feedback_child") || target.includes("反馈") || target.includes("裁决")) {
    return "feedback";
  }
  return "unknown";
}

function assignDepths(projection) {
  const parentByChild = new Map();
  for (const link of projection.links) {
    parentByChild.set(link.child, link.parent);
  }
  for (const node of projection.nodeMap.values()) {
    if (!parentByChild.has(node.id)) {
      projection.roots.add(node.id);
    }
  }
  for (const node of projection.nodeMap.values()) {
    node.depth = computeDepth(node.id, parentByChild);
  }
  projection.stats.jobs = projection.nodeMap.size;
  projection.stats.candidates = sumNodeSet(projection.nodeMap, "candidates");
  projection.stats.evidence = sumNodeSet(projection.nodeMap, "evidence");
  projection.stats.verification = projection.milestones.verificationResults.length;
  projection.stats.repairs = projection.milestones.repairCreated;
  projection.stats.feedback = projection.milestones.feedbackCreated;
  projection.stats.routes = projection.milestones.routeActions.length;
  projection.stats.childReviews = projection.milestones.childPackageReviews.length;
  projection.stats.parentIntegrations = projection.milestones.parentIntegrations.length;
}

function computeDepth(nodeId, parentByChild) {
  let depth = 0;
  let current = nodeId;
  const seen = new Set([current]);
  while (parentByChild.has(current)) {
    current = parentByChild.get(current);
    if (seen.has(current)) {
      return depth;
    }
    seen.add(current);
    depth += 1;
  }
  return depth;
}

function sumNodeSet(nodeMap, field) {
  let total = 0;
  for (const node of nodeMap.values()) {
    total += node[field].size;
  }
  return total;
}

function rootFrom(data, fallback) {
  return stringValue((data && data.root_job_id) || fallback || "");
}

function statusFromReport(reportText) {
  const report = tryParseJson(reportText);
  return report && report.overall_status ? report.overall_status : "";
}

function acceptanceRouteFrom(data) {
  const judgment = tryParseJson(data.acceptance_routing_judgment);
  return {
    action: stringValue(data.acceptance_route_action || (judgment && judgment.route_action)),
    kind: stringValue(data.acceptance_route_kind || (judgment && judgment.feedback_job_kind)),
    reason: stringValue(data.reason || (judgment && judgment.reason)),
  };
}

function tryParseJson(value) {
  if (!value || typeof value !== "string") {
    return null;
  }
  try {
    return JSON.parse(value);
  } catch (_error) {
    return null;
  }
}

function isImportantEvent(event) {
  return IMPORTANT_EVENTS.has(event.event_type);
}

function eventLabel(event) {
  return EVENT_LABELS[event.event_type] || event.event_type || "未知事件";
}

function stateLabel(state) {
  return STATE_LABELS[state] || state || "未知";
}

function stringValue(value) {
  if (value === undefined || value === null) {
    return "";
  }
  return String(value);
}

function shortId(id) {
  const text = stringValue(id);
  if (text.length <= 14) {
    return text || "无编号";
  }
  return `${text.slice(0, 8)}...${text.slice(-4)}`;
}

function escapeHtml(value) {
  return stringValue(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function stepTraceFromEvent(event) {
  if (!event) {
    return null;
  }
  const data = event.data || {};
  return {
    index: event.index,
    eventType: event.event_type,
    label: eventLabel(event),
    timestamp: event.timestamp,
    message: event.message,
    jobId: stringValue(data.job_id),
    parentJobId: stringValue(data.parent_job_id),
    childJobId: stringValue(data.child_job_id || data.verification_job_id || data.feedback_job_id),
    action: stringValue(data.process_action || data.job_tree_action || data.acceptance_route_action || ""),
    phase: stringValue(data.process_phase || phaseFromEvent(event)),
    status: stringValue(data.process_status || data.parent_integration_status || data.verification_status || ""),
    inputs: fieldsToTraceItems(data, STEP_FIELD_GROUPS.inputs),
    outputs: fieldsToTraceItems(data, STEP_FIELD_GROUPS.outputs),
    evidence: fieldsToTraceItems(data, STEP_FIELD_GROUPS.evidence),
    state: fieldsToTraceItems(data, STEP_FIELD_GROUPS.state),
    raw: event.raw,
  };
}

function fieldsToTraceItems(data, keys) {
  const items = [];
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(data, key)) {
      continue;
    }
    const value = data[key];
    if (value === undefined || value === null || String(value) === "") {
      continue;
    }
    items.push({
      key,
      label: FIELD_LABELS[key] || key,
      value: prettyValue(value),
    });
  }
  return items;
}

function prettyValue(value) {
  if (typeof value !== "string") {
    return JSON.stringify(value, null, 2);
  }
  const parsed = tryParseJson(value);
  if (parsed !== null) {
    return JSON.stringify(parsed, null, 2);
  }
  return value;
}

function phaseFromEvent(event) {
  const type = stringValue(event && event.event_type);
  if (type.includes("integration")) {
    return "parent_integration";
  }
  if (type.includes("child_package")) {
    return "child_package_review";
  }
  if (type.includes("split_proposal")) {
    return "split_proposal";
  }
  if (type.includes("verification")) {
    return "verification";
  }
  if (type.includes("repair")) {
    return "repair";
  }
  if (type.includes("acceptance")) {
    return "acceptance";
  }
  if (type.includes("provider")) {
    return "provider";
  }
  return "";
}

function setupViewer() {
  const input = document.getElementById("logFileInput");
  input.addEventListener("change", handleFileSelected);
  document.getElementById("toStartButton").addEventListener("click", () => setCursor(0));
  document.getElementById("prevButton").addEventListener("click", () => setCursor(VIEWER_STATE.cursor - 1));
  document.getElementById("nextButton").addEventListener("click", () => setCursor(VIEWER_STATE.cursor + 1));
  document.getElementById("toEndButton").addEventListener("click", () => setCursor(VIEWER_STATE.events.length));
  document.getElementById("nextImportantButton").addEventListener("click", nextImportant);
  document.getElementById("playButton").addEventListener("click", togglePlay);
}

function handleFileSelected(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) {
    return;
  }
  stopPlay();
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const events = parseJsonl(reader.result);
      VIEWER_STATE.fileName = file.name;
      VIEWER_STATE.events = events;
      VIEWER_STATE.cursor = 0;
      VIEWER_STATE.selectedJobId = "";
      showViewer();
      render();
    } catch (error) {
      showError(error && error.message ? error.message : String(error));
    }
  };
  reader.onerror = () => showError("浏览器读取文件失败，请重新选择日志文件。");
  reader.readAsText(file, "utf-8");
}

function showViewer() {
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("errorState").classList.add("hidden");
  document.getElementById("viewer").classList.remove("hidden");
}

function showError(message) {
  document.getElementById("viewer").classList.add("hidden");
  document.getElementById("emptyState").classList.add("hidden");
  const errorState = document.getElementById("errorState");
  errorState.textContent = message;
  errorState.classList.remove("hidden");
}

function setCursor(nextCursor) {
  const bounded = Math.max(0, Math.min(nextCursor, VIEWER_STATE.events.length));
  VIEWER_STATE.cursor = bounded;
  render();
}

function nextImportant() {
  for (let index = VIEWER_STATE.cursor; index < VIEWER_STATE.events.length; index += 1) {
    if (isImportantEvent(VIEWER_STATE.events[index])) {
      setCursor(index + 1);
      return;
    }
  }
  setCursor(VIEWER_STATE.events.length);
}

function togglePlay() {
  if (VIEWER_STATE.playTimer) {
    stopPlay();
    return;
  }
  document.getElementById("playButton").textContent = "暂停";
  VIEWER_STATE.playTimer = window.setInterval(() => {
    const before = VIEWER_STATE.cursor;
    nextImportant();
    if (VIEWER_STATE.cursor === before || VIEWER_STATE.cursor >= VIEWER_STATE.events.length) {
      stopPlay();
    }
  }, 550);
}

function stopPlay() {
  if (VIEWER_STATE.playTimer) {
    window.clearInterval(VIEWER_STATE.playTimer);
    VIEWER_STATE.playTimer = null;
  }
  const playButton = typeof document !== "undefined" ? document.getElementById("playButton") : null;
  if (playButton) {
    playButton.textContent = "播放";
  }
}

function render() {
  const projection = projectEvents(VIEWER_STATE.events, VIEWER_STATE.cursor);
  ensureSelectedJob(projection);
  renderHeader(projection);
  renderSummary(projection);
  renderGraph(projection);
  renderDetails(projection);
  renderTimeline(projection);
  renderControls();
}

function ensureSelectedJob(projection) {
  if (VIEWER_STATE.selectedJobId && projection.nodeMap.has(VIEWER_STATE.selectedJobId)) {
    return;
  }
  const currentJobId = projection.currentEvent && projection.currentEvent.data && projection.currentEvent.data.job_id;
  if (currentJobId && projection.nodeMap.has(currentJobId)) {
    VIEWER_STATE.selectedJobId = currentJobId;
    return;
  }
  const firstNode = projection.nodes.slice().sort((a, b) => a.order - b.order)[0];
  VIEWER_STATE.selectedJobId = firstNode ? firstNode.id : "";
}

function renderHeader(projection) {
  document.getElementById("fileName").textContent = VIEWER_STATE.fileName || "未加载";
  document.getElementById("cursorInfo").textContent = `${projection.cursor} / ${projection.totalEvents}`;
  document.getElementById("closureStatus").textContent = `闭环状态：${closureText(projection)}`;
}

function closureText(projection) {
  if (projection.milestones.runFailed) {
    return "运行失败";
  }
  const runClosed = projection.milestones.runFinished || projection.milestones.chatFinished;
  if (runClosed && projection.milestones.sandboxDestroyed) {
    return "运行完成，沙盒已销毁";
  }
  if (runClosed) {
    return "运行完成，等待沙盒销毁事件";
  }
  return "未完成";
}

function renderSummary(projection) {
  const route = projection.milestones.routeActions[projection.milestones.routeActions.length - 1];
  const items = [
    ["事件", projection.stats.events],
    ["业节点", projection.stats.jobs],
    ["候选", projection.stats.candidates],
    ["证据", projection.stats.evidence],
    ["校验", projection.stats.verification],
    ["修复业", projection.stats.repairs],
    ["反馈业", projection.stats.feedback],
    ["果包验收", projection.stats.childReviews],
    ["父业整合", projection.stats.parentIntegrations],
    ["路由", route ? `${route.action || "未知"}` : "无"],
  ];
  document.getElementById("summaryGrid").innerHTML = items
    .map(([label, value]) => `<div class="summary-item"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`)
    .join("");
}

function renderGraph(projection) {
  const canvas = document.getElementById("graphCanvas");
  if (!projection.nodes.length) {
    canvas.innerHTML = '<div class="empty-graph">尚未重放到业树事件。点击“下一步”或“下一关键”。</div>';
    return;
  }
  const layout = layoutNodes(projection.nodes, projection.links);
  const width = Math.max(760, layout.width);
  const height = Math.max(430, layout.height);
  const paths = projection.links
    .map((link) => edgePath(layout.positions.get(link.parent), layout.positions.get(link.child)))
    .filter(Boolean)
    .map((path) => `<path d="${path}"></path>`)
    .join("");
  const nodes = projection.nodes
    .slice()
    .sort((a, b) => a.depth - b.depth || a.order - b.order)
    .map((node) => renderNode(node, layout.positions.get(node.id)))
    .join("");
  canvas.innerHTML = `
    <div class="graph-inner" style="width:${width}px;height:${height}px">
      <svg class="edge-layer" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">${paths}</svg>
      ${nodes}
    </div>
  `;
  canvas.querySelectorAll(".job-node").forEach((nodeElement) => {
    nodeElement.addEventListener("click", () => {
      VIEWER_STATE.selectedJobId = nodeElement.dataset.jobId;
      render();
    });
  });
}

function layoutNodes(nodes, links) {
  const childrenByParent = new Map();
  for (const link of links) {
    if (!childrenByParent.has(link.parent)) {
      childrenByParent.set(link.parent, []);
    }
    childrenByParent.get(link.parent).push(link.child);
  }
  const sorted = nodes.slice().sort((a, b) => a.depth - b.depth || a.order - b.order);
  const byDepth = new Map();
  for (const node of sorted) {
    if (!byDepth.has(node.depth)) {
      byDepth.set(node.depth, []);
    }
    byDepth.get(node.depth).push(node);
  }
  const positions = new Map();
  const nodeWidth = 248;
  const nodeHeight = 108;
  const xGap = 92;
  const yGap = 34;
  let maxX = 0;
  let maxY = 0;
  for (const [depth, depthNodes] of byDepth.entries()) {
    depthNodes.sort((a, b) => a.order - b.order);
    depthNodes.forEach((node, index) => {
      const x = 24 + depth * (nodeWidth + xGap);
      const y = 24 + index * (nodeHeight + yGap);
      positions.set(node.id, { x, y, width: nodeWidth, height: nodeHeight });
      maxX = Math.max(maxX, x + nodeWidth + 24);
      maxY = Math.max(maxY, y + nodeHeight + 24);
    });
  }
  return { positions, width: maxX, height: maxY };
}

function edgePath(parent, child) {
  if (!parent || !child) {
    return "";
  }
  const startX = parent.x + parent.width;
  const startY = parent.y + parent.height / 2;
  const endX = child.x;
  const endY = child.y + child.height / 2;
  const midX = startX + Math.max(32, (endX - startX) / 2);
  return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
}

function renderNode(node, position) {
  const pos = position || { x: 0, y: 0 };
  const stateClass = `state-${node.state || "draft"}`;
  const selected = node.id === VIEWER_STATE.selectedJobId ? " selected" : "";
  const title = `${kindLabel(node.kind)} ${shortId(node.id)}`;
  const target = node.target || "未记录目标";
  return `
    <article class="job-node kind-${escapeHtml(node.kind)}${selected}" data-job-id="${escapeHtml(node.id)}" style="left:${pos.x}px;top:${pos.y}px">
      <div class="node-title" title="${escapeHtml(node.id)}">${escapeHtml(title)}</div>
      <div class="node-target" title="${escapeHtml(target)}">${escapeHtml(target)}</div>
      <div class="node-meta">
        <span class="pill ${stateClass}">${escapeHtml(stateLabel(node.state))}</span>
        <span class="pill">候选 ${node.candidates.size}</span>
        <span class="pill">证据 ${node.evidence.size}</span>
      </div>
    </article>
  `;
}

function kindLabel(kind) {
  return {
    root: "根业",
    verification: "校验业",
    repair: "修复业",
    feedback: "反馈业",
    child: "子业",
    terminal: "终止",
    unknown: "业",
  }[kind] || "业";
}

function renderDetails(projection) {
  const currentEvent = projection.currentEvent;
  const selectedNode = VIEWER_STATE.selectedJobId ? projection.nodeMap.get(VIEWER_STATE.selectedJobId) : null;
  const trace = stepTraceFromEvent(currentEvent);
  document.getElementById("currentStepTitle").textContent = trace
    ? `${trace.index + 1}. ${trace.label}（${trace.eventType}）`
    : "尚未重放事件。";
  document.getElementById("stepActionDetail").innerHTML = trace
    ? stepActionHtml(trace)
    : '<p class="muted">尚未重放事件。</p>';
  document.getElementById("stepInput").innerHTML = traceItemsHtml(trace ? trace.inputs : []);
  document.getElementById("stepOutput").innerHTML = traceItemsHtml(trace ? trace.outputs : []);
  document.getElementById("stepEvidence").innerHTML = traceItemsHtml(trace ? trace.evidence : []);
  document.getElementById("stepState").innerHTML = traceItemsHtml(trace ? trace.state : []);
  document.getElementById("selectedJobDetail").innerHTML = selectedNode
    ? nodeDetailHtml(selectedNode)
    : '<p class="muted">尚未出现业节点。</p>';
  document.getElementById("rawEvent").textContent = currentEvent
    ? JSON.stringify(currentEvent.raw, null, 2)
    : "";
}

function stepActionHtml(trace) {
  const rows = [
    ["序号", trace.index + 1],
    ["阶段", trace.phase],
    ["动作", ACTION_LABELS[trace.action] || trace.action],
    ["状态", trace.status],
    ["时间", trace.timestamp || "未记录"],
    ["业编号", trace.jobId],
    ["父业", trace.parentJobId],
    ["子业", trace.childJobId],
    ["说明", trace.message],
  ];
  return rows
    .filter((row) => stringValue(row[1]))
    .map(([label, value]) => detailRow(label, value))
    .join("");
}

function traceItemsHtml(items) {
  if (!items || !items.length) {
    return '<p class="trace-empty">当前步骤未记录该类信息。</p>';
  }
  return items
    .map((item) => {
      return `
        <article class="trace-item">
          <div class="trace-item-title">${escapeHtml(item.label)}（${escapeHtml(item.key)}）</div>
          <pre class="trace-item-body">${escapeHtml(item.value)}</pre>
        </article>
      `;
    })
    .join("");
}

function nodeDetailHtml(node) {
  const latestActions = node.actions.slice(-8).reverse().map((action) => `${action.index + 1}. ${action.label}`).join("\n");
  const rows = [
    ["业编号", node.id],
    ["类型", kindLabel(node.kind)],
    ["状态", stateLabel(node.state)],
    ["父业", node.parentJobId],
    ["根业", node.rootJobId],
    ["目标", node.target],
    ["候选数", node.candidates.size],
    ["证据数", node.evidence.size],
    ["校验状态", node.verificationStatus],
    ["路由动作", node.lastRouteAction],
    ["路由原因", node.lastRouteReason],
    ["最近动作", latestActions],
  ];
  return rows
    .filter((row) => row[1] !== "" && row[1] !== undefined && row[1] !== null)
    .map(([label, value]) => detailRow(label, value))
    .join("");
}

function detailRow(label, value) {
  return `<div class="detail-row"><span>${escapeHtml(label)}</span><span>${escapeHtml(value)}</span></div>`;
}

function renderTimeline(projection) {
  const timeline = document.getElementById("timeline");
  const events = VIEWER_STATE.events;
  const center = Math.max(0, projection.cursor - 1);
  const start = Math.max(0, center - 70);
  const end = Math.min(events.length, Math.max(center + 50, 120));
  timeline.innerHTML = events.slice(start, end).map((event) => {
    const trace = stepTraceFromEvent(event);
    const current = event.index === center && projection.cursor > 0 ? " current" : "";
    const important = isImportantEvent(event) ? " important" : "";
    const ioRich = trace && (trace.inputs.length || trace.outputs.length || trace.evidence.length) ? " io-rich" : "";
    const actionText = trace && trace.action ? ` | ${ACTION_LABELS[trace.action] || trace.action}` : "";
    return `
      <li class="${current}${important}${ioRich}">
        <span class="timeline-label">${event.index + 1}. ${escapeHtml(eventLabel(event))}${escapeHtml(actionText)}</span>
        <span class="timeline-time">${escapeHtml(event.timestamp || event.event_type)}</span>
      </li>
    `;
  }).join("");
}

function renderControls() {
  const hasEvents = VIEWER_STATE.events.length > 0;
  document.getElementById("toStartButton").disabled = !hasEvents || VIEWER_STATE.cursor <= 0;
  document.getElementById("prevButton").disabled = !hasEvents || VIEWER_STATE.cursor <= 0;
  document.getElementById("nextButton").disabled = !hasEvents || VIEWER_STATE.cursor >= VIEWER_STATE.events.length;
  document.getElementById("toEndButton").disabled = !hasEvents || VIEWER_STATE.cursor >= VIEWER_STATE.events.length;
  document.getElementById("nextImportantButton").disabled = !hasEvents || VIEWER_STATE.cursor >= VIEWER_STATE.events.length;
  document.getElementById("playButton").disabled = !hasEvents || VIEWER_STATE.cursor >= VIEWER_STATE.events.length;
}

if (typeof document !== "undefined") {
  setupViewer();
}

if (typeof module !== "undefined") {
  module.exports = {
    parseJsonl,
    projectEvents,
    stepTraceFromEvent,
    isImportantEvent,
    eventLabel,
    closureText,
  };
}
