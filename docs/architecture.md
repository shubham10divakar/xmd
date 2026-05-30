# XRuntime - The XMD Runtime

## The Most Important Component

The true innovation of XMD is not the file extensions.

The innovation is the runtime.

Without a runtime:

```text
AGENT.lmd
TASKS.tmd
WORKFLOW.wmd
```

are simply text files.

The runtime transforms:

```text
Document
    ↓
System
```

This is similar to how HTML became useful only after browsers existed.

```text
HTML
    ↓
Browser
    ↓
Application
```

Likewise:

```text
XMD
    ↓
XRuntime
    ↓
Agentic Application
```

---

# XRuntime Architecture

```text
             XMD File
                 │
                 ▼
            XMD Parser
                 │
                 ▼
      Intermediate Representation
                 │
                 ▼
         Execution Engine
                 │
      ┌──────────┼──────────┐
      ▼          ▼          ▼
   Plugins     Memory     Events
```

The runtime becomes the execution environment for all XMD documents.

---

# Layer 1 - Parser

The parser should be lightweight.

Its only responsibility is transforming XMD documents into a structured representation.

Example:

```wmd
@task train_model
dataset: plantdoc
epochs: 50
```

Parser output:

```json
{
  "type": "task",
  "name": "train_model",
  "params": {
    "dataset": "plantdoc",
    "epochs": 50
  }
}
```

The parser should never execute logic.

It only understands structure.

---

# Layer 2 - Intermediate Representation (IR)

The IR is the heart of the system.

Every document becomes a graph of nodes.

Example:

```python
Node(
    type="task",
    name="train_model",
    params={}
)
```

Memory node:

```python
Node(
    type="memory",
    source="last_tasks"
)
```

Plugin node:

```python
Node(
    type="github",
    action="open_issues"
)
```

Benefits:

* Language independent
* Runtime independent
* Easier optimization
* Easier validation
* Easier transpilation

The IR acts as the universal representation of XMD.

---

# Layer 3 - Execution Engine

The execution engine determines:

* What runs
* When it runs
* How it runs
* Dependency order

Example workflow:

```wmd
@workflow

task_a
task_b
task_c
```

Execution graph:

```text
task_a
   ↓
task_b
   ↓
task_c
```

The engine executes nodes in the correct order.

---

# Layer 4 - Plugin System

The runtime core should remain minimal.

Most functionality should be implemented through plugins.

Example structure:

```text
plugins/
├── python
├── java
├── node
├── shell
├── github
├── git
├── docker
├── database
├── http
├── filesystem
├── memory
└── llm
```

Example:

```emd
@github
repo: subham/xmd
action: open_issues
```

Execution:

```python
plugin.execute(node)
```

This architecture allows the runtime to grow without modifying the core.

---

# Layer 5 - Memory Engine

Memory is one of the most important capabilities.

Example:

```lmd
# Recent Tasks

{{ memory.last_10_tasks }}
```

The runtime resolves the values from memory.

Potential backends:

```text
SQLite
PostgreSQL
Vector Database
Redis
Filesystem
```

The memory layer allows documents to evolve over time.

---

# Layer 6 - Event Engine

Documents should react to events.

Examples:

```emd
@on_file_change
src/
run_tests()
```

```emd
@daily
update_metrics()
```

```emd
@on_commit
update_changelog()
```

The runtime continuously listens for events and executes matching workflows.

---

# Layer 7 - Agent Engine

This is where XMD becomes agentic.

Example:

```lmd
Goal:
Build a React Application
```

Agent Flow:

```text
Read Goal
    ↓
Generate Tasks
    ↓
Update TASKS.tmd
    ↓
Execute Tasks
    ↓
Update MEMORY.mmd
```

Documents begin managing other documents.

The system becomes self-organizing.

---

# Runtime Language Independence

One important design principle:

Avoid embedding implementation-specific languages.

Bad:

```emd
@python
print("hello")
```

This creates runtime dependency.

Preferred:

```emd
@task
name: train_model
```

The runtime determines whether:

```text
Python Plugin
Java Plugin
Node Plugin
Go Plugin
```

should execute the task.

This preserves portability.

---

# Development Roadmap

## Version 0.1

Core Foundation

Features:

```text
Parser
IR
CLI
Plugin System
```

Commands:

```bash
runxmd parse file.wmd
runxmd run file.wmd
runxmd validate file.wmd
```

---

## Version 0.2

Reactive Runtime

Features:

```text
Memory Engine
Event Engine
```

Commands:

```bash
runxmd watch .
```

Documents become reactive.

---

## Version 0.3

Agent Runtime

Features:

```text
Agent Engine
Task Planning
Memory Updates
Document Coordination
```

Commands:

```bash
runxmd agent AGENT.lmd
```

Documents become autonomous.

---

## Version 1.0

Distributed Runtime

Features:

```text
Multiple Agents
Shared Memory
Distributed Execution
Workflow Coordination
```

This transforms XMD into a complete document operating environment.

---

# XRuntime as a Document Operating System

Traditional Markdown:

```text
Markdown = Files
```

XMD Vision:

```text
XRuntime = Operating System for Documents
```

Where:

```text
Documents
    ↓
Processes

Memory Files
    ↓
State

Workflow Files
    ↓
Programs

Agent Files
    ↓
Autonomous Systems
```

The goal is not simply executable Markdown.

The goal is a runtime where documents become the primary unit of computation.

---

# Ultimate Runtime Vision

Today:

```text
Code
Configuration
Documentation
Memory
Automation
Workflows
```

are separate systems.

With XRuntime:

```text
Everything
    ↓
Documents
    ↓
Runtime
```

The document becomes:

* Documentation
* Configuration
* Workflow
* Memory
* Agent
* Application

This is the foundation of a document-centric operating environment where humans, agents, and software systems all interact through a unified XMD ecosystem.
