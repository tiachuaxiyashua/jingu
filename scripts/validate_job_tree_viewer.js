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
      arg === "--expect-parent-integration"
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

  console.log(
    [
      `ok ${scenario.expectation}`,
      `file=${absolutePath}`,
      `events=${events.length}`,
      `jobs=${projection.stats.jobs}`,
      `routes=${routeActions.join(",") || "none"}`,
      `childReviews=${projection.stats.childReviews}`,
      `parentIntegrations=${projection.stats.parentIntegrations}`,
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
      "--expect-closure <log.jsonl>",
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
