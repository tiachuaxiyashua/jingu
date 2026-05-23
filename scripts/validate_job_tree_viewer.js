"use strict";

const fs = require("fs");
const path = require("path");
const viewer = require("../tools/job-tree-log-viewer/viewer.js");

function main(argv) {
  const scenarios = parseArgs(argv);
  if (!scenarios.length) {
    printUsage();
    return 2;
  }

  for (const scenario of scenarios) {
    validateScenario(scenario);
  }
  return 0;
}

function parseArgs(argv) {
  const scenarios = [];
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (
      arg === "--expect-repair" ||
      arg === "--expect-feedback" ||
      arg === "--expect-closure" ||
      arg === "--expect-child-review" ||
      arg === "--expect-parent-integration" ||
      arg === "--expect-integration-repair" ||
      arg === "--expect-human-decision" ||
      arg === "--expect-evidence-hardness" ||
      arg === "--expect-method-learning" ||
      arg === "--expect-filter"
    ) {
      const filePath = argv[index + 1];
      if (!filePath || filePath.startsWith("--")) {
        throw new Error(`${arg} requires a log path`);
      }
      scenarios.push({
        expectation: arg.replace("--expect-", ""),
        filePath,
      });
      index += 1;
      continue;
    }
    throw new Error(`unknown argument: ${arg}`);
  }
  return scenarios;
}

function validateScenario(scenario) {
  const absolutePath = path.resolve(scenario.filePath);
  const text = fs.readFileSync(absolutePath, "utf8");
  const events = viewer.parseJsonl(text);
  const projection = viewer.projectEvents(events, events.length);
  const routeActions = projection.milestones.routeActions.map((route) => route.action);
  const nodeKinds = projection.nodes.map((node) => node.kind);
  const closure = viewer.closureText(projection);
  const traces = events.map((event) => viewer.stepTraceFromEvent(event));

  if (scenario.expectation === "repair") {
    assert(routeActions.includes("repair"), "expected acceptance route action repair");
    assert(projection.milestones.repairCreated > 0, "expected repair job creation milestone");
    assert(nodeKinds.includes("repair"), "expected repair node in job tree projection");
    assert(projection.milestones.verificationResults.length >= 2, "expected initial and repaired verification results");
  }

  if (scenario.expectation === "feedback") {
    assert(routeActions.includes("feedback"), "expected acceptance route action feedback");
    assert(projection.milestones.feedbackCreated > 0, "expected feedback job creation milestone");
    assert(nodeKinds.includes("feedback"), "expected feedback node in job tree projection");
  }

  if (scenario.expectation === "closure") {
    assert(
      projection.milestones.runFinished || projection.milestones.chatFinished,
      "expected run or chat session finished milestone",
    );
    assert(projection.milestones.sandboxDestroyed, "expected sandbox destroyed milestone");
  }

  if (scenario.expectation === "child-review") {
    assert(
      projection.milestones.childPackageReviews.length > 0,
      "expected child package review milestones",
    );
    assert(
      traces.some((trace) => trace && trace.inputs.some((item) => item.key === "child_package_review_prompt")),
      "expected child package review input trace",
    );
    assert(
      traces.some((trace) => trace && trace.outputs.some((item) => item.key === "child_package_review_judgment")),
      "expected child package review output trace",
    );
  }

  if (scenario.expectation === "parent-integration") {
    assert(
      projection.milestones.parentIntegrations.length > 0,
      "expected parent integration milestones",
    );
    assert(
      traces.some((trace) => trace && trace.inputs.some((item) => item.key === "parent_integration_prompt")),
      "expected parent integration input trace",
    );
    assert(
      traces.some((trace) => trace && trace.outputs.some((item) => item.key === "parent_integration_candidate")),
      "expected parent integration candidate output trace",
    );
  }

  if (scenario.expectation === "integration-repair") {
    assert(
      projection.milestones.integrationRepairCreated > 0,
      "expected parent integration repair milestone",
    );
    assert(nodeKinds.includes("integration-repair"), "expected integration repair node");
  }

  if (scenario.expectation === "human-decision") {
    assert(
      projection.milestones.humanDecisionRequests + projection.milestones.humanDecisionReturns > 0,
      "expected human decision request or return milestone",
    );
  }

  if (scenario.expectation === "evidence-hardness") {
    assert(projection.milestones.weakEvidenceEvents > 0, "expected weak evidence hardness milestone");
    assert(
      traces.some((trace) => trace && trace.evidence.some((item) => item.key === "evidence_hardness")),
      "expected evidence hardness trace item",
    );
  }

  if (scenario.expectation === "method-learning") {
    assert(projection.milestones.methodLearningCandidates > 0, "expected method learning candidate milestone");
    assert(
      traces.some((trace) => trace && trace.outputs.some((item) => item.key === "method_learning_candidate")),
      "expected method learning candidate output trace",
    );
  }

  if (scenario.expectation === "filter") {
    const filtered = viewer.filterEventsForTimeline(events, { phase: "parent_integration" });
    assert(filtered.length > 0, "expected phase filter to return events");
    assert(
      filtered.every((event) => viewer.stepTraceFromEvent(event).phase === "parent_integration"),
      "expected phase filter to keep only parent integration events",
    );
  }

  console.log(
    [
      `ok ${scenario.expectation}`,
      `file=${absolutePath}`,
      `events=${events.length}`,
      `jobs=${projection.stats.jobs}`,
      `routes=${routeActions.join(",") || "none"}`,
      `childReviews=${projection.stats.childReviews}`,
      `parentIntegrations=${projection.stats.parentIntegrations}`,
      `integrationRepairs=${projection.stats.integrationRepairs}`,
      `humanDecisions=${projection.stats.humanDecisions}`,
      `closure=${closure}`,
    ].join(" | "),
  );
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function printUsage() {
  console.error(
    "Usage: node scripts/validate_job_tree_viewer.js " +
      "--expect-repair <log.jsonl> --expect-feedback <log.jsonl> " +
      "--expect-child-review <log.jsonl> --expect-parent-integration <log.jsonl> " +
      "--expect-integration-repair <log.jsonl> --expect-human-decision <log.jsonl> " +
      "--expect-evidence-hardness <log.jsonl> --expect-method-learning <log.jsonl> " +
      "--expect-filter <log.jsonl> --expect-closure <log.jsonl>",
  );
}

if (require.main === module) {
  try {
    process.exitCode = main(process.argv.slice(2));
  } catch (error) {
    console.error(error && error.message ? error.message : String(error));
    process.exitCode = 1;
  }
}
