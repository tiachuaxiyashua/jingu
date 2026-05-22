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
    if (arg === "--expect-repair" || arg === "--expect-feedback" || arg === "--expect-closure") {
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

  console.log(
    [
      `ok ${scenario.expectation}`,
      `file=${absolutePath}`,
      `events=${events.length}`,
      `jobs=${projection.stats.jobs}`,
      `routes=${routeActions.join(",") || "none"}`,
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
      "--expect-repair <log.jsonl> --expect-feedback <log.jsonl> --expect-closure <log.jsonl>",
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
