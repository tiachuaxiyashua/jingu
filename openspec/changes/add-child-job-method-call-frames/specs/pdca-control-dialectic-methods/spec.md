## ADDED Requirements

### Requirement: PDCA method is an independent method appearance source
The repository SHALL provide PDCA 法 as an independent skill method file that can be loaded by the existing method loader.

#### Scenario: Load PDCA method
- **WHEN** the method loader reads the PDCA method file
- **THEN** it returns a method context with a method name, checksum, and one or more method-law fragments

### Requirement: Control variable method is an independent method appearance source
The repository SHALL provide 控制变量法 as an independent skill method file that can be loaded by the existing method loader.

#### Scenario: Load control variable method
- **WHEN** the method loader reads the control variable method file
- **THEN** it returns a method context with a method name, checksum, and one or more method-law fragments

### Requirement: Dialectical method is an independent method appearance source
The repository SHALL provide 辩证法 as an independent skill method file that can be loaded by the existing method loader.

#### Scenario: Load dialectical method
- **WHEN** the method loader reads the dialectical method file
- **THEN** it returns a method context with a method name, checksum, and one or more method-law fragments

### Requirement: Method nesting is expressed through jobs and call frames
The repository SHALL describe PDCA 法, 控制变量法, and 辩证法 nesting as parent-child job relationships and call frames, not as static method file inclusion.

#### Scenario: PDCA delegates variable comparison
- **WHEN** PDCA 法 identifies that a variable comparison is required
- **THEN** it directs the caller to produce or delegate a control-variable child job whose result returns to PDCA Check

#### Scenario: PDCA delegates contradiction analysis
- **WHEN** PDCA 法 identifies a target tension or value conflict
- **THEN** it directs the caller to produce or delegate a dialectical child job whose result returns to PDCA Act
