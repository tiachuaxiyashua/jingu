## ADDED Requirements

### Requirement: Method source is decomposed into method-law fragments
The sandbox method loader SHALL parse a method source into reusable method-law fragments instead of treating the entire file as a single opaque method prompt.

#### Scenario: Method source has markdown headings
- **WHEN** a method file contains markdown heading sections
- **THEN** the loader MUST produce ordered fragments with id, title, heading level, checksum, and content.

#### Scenario: Method source has no headings
- **WHEN** a method file has content but no markdown heading sections
- **THEN** the loader MUST produce one fallback fragment for the full content.

### Requirement: Method-law fragments are bound to jobs
The sandbox SHALL bind method-law fragments to the current job as appearances and SHALL record the binding before calling the AI provider.

#### Scenario: A job uses a method source
- **WHEN** a sandbox run or chat turn creates a root job and loads a method source
- **THEN** the runtime MUST store method-law fragment appearances for that job and log a binding event with fragment references.

### Requirement: Method provider messages are fragment-driven
The sandbox SHALL inject method context as a manifest plus separate method-law fragment messages rather than one full method-file message.

#### Scenario: Provider messages are assembled
- **WHEN** the sandbox assembles provider messages for candidate generation
- **THEN** the messages MUST include the method manifest and each method-law fragment with its fragment id and checksum, and MUST NOT include a single full-file method content message.

### Requirement: Method trace evidence
The sandbox SHALL request method self-review that identifies method-law fragment usage, gaps, and update candidates.

#### Scenario: Candidate response is reviewed
- **WHEN** the AI returns a candidate result
- **THEN** the method self-review request MUST include the method-law manifest and ask for a fragment usage trace without accepting, rejecting, or mutating the method.

### Requirement: Method-law observability
The sandbox SHALL record method-law manifest loading, fragment loading, and fragment binding in both machine JSONL and readable Markdown logs.

#### Scenario: Method source is loaded
- **WHEN** the method loader resolves and parses a method source
- **THEN** the flow log MUST include method metadata, fragment count, fragment ids, and each fragment's content and checksum.
