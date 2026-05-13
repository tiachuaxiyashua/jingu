# Context Engineering Review Checklist

## 1. Indexing and freshness

- Are indexed units explicit?
- Is stale detection explicit?
- Can incremental refresh update only dirty units?

## 2. Retrieval quality

- Are multiple retrieval paths combined intentionally?
- Is ranking or reranking explicit?
- Are reasons for each hit preserved?

## 3. Budget and packing

- Is there one token/budget owner?
- Does packing explain what was selected vs omitted?
- Are retrieval hits and recent changes balanced intentionally?

## 4. Provenance and evidence

- Is every retrieval hit traceable to a path and reason?
- Can a reviewer inspect the final context pack?
- Is context evidence persisted with the run?

## 5. Memory / compaction

- Is long-dialogue compression persisted?
- Are summaries versioned or attributable to a run?
- Can a resumed run rebuild context deterministically enough?

## 6. Review threshold

Mark `high` if any of these are true:
- retrieval exists without freshness or provenance
- compression exists without explicit omission evidence
- evidence cannot explain why context entered the prompt
- budget ownership is split across layers
