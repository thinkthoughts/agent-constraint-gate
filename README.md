# agent-constraint-gate

**Constraint gate for autonomous AI agents**  
Verify actions before execution to prevent unsafe behavior (OpenClaw-compatible)

---

## 🧭 Overview

Most agent systems follow:

```text
reason → act
```

This repo introduces a constraint layer:

```text
reason → verify → act
```

The goal is simple:

> **Prevent unsafe tool execution before it happens**

---

## ⚠️ Problem

Agent frameworks (like OpenClaw) can:
- execute file operations  
- call APIs  
- send messages  

But they often lack a **pre-execution constraint check**, which can lead to:
- prompt injection exploits  
- data exfiltration  
- unintended autonomous actions  

---

## ✅ Solution

Add a **constraint gate** between reasoning and action.

The gate:
1. **Observes** the proposed action  
2. **Verifies** it against a policy  
3. **Approves / blocks / revises** before execution  

---

## 🔧 Minimal Example

```python
from constraint import verify_action

action = {
    "tool": "file_write",
    "path": "/sensitive/data.txt",
    "content": "..."
}

decision = verify_action(action)

if decision["allow"]:
    execute(action)
else:
    print("Blocked:", decision["reason"])
```

---

## 📐 Policy (example)

```yaml
rules:
  - tool: file_write
    allow: false
    paths:
      - "/safe/"
  - tool: http_request
    allow_domains:
      - "api.openai.com"
      - "example.com"
```

---

## 🔗 OpenClaw Integration (example)

Insert constraint check before tool execution:

```text
OpenClaw reasoning
        ↓
constraint gate (this repo)
        ↓
tool execution
```

See: `examples/openclaw.md`

---

## 🧠 Design Principles

- **Verify-before-act** over react-after-harm  
- **Small, composable layer** (not a full agent framework)  
- **Policy-driven** (YAML or programmable)  
- **Framework-agnostic** (works with any agent system)  

---

## 🚀 Use Cases

- Autonomous agents (OpenClaw, AutoGPT-style systems)  
- Local agents with file/system access  
- API-calling assistants  
- Research on agent safety and alignment  

---

## 📌 Status

Minimal prototype — designed for clarity and integration.  
Contributions and feedback welcome.

---

## 📎 Reference

Antiviolent Intelligence framework:  
https://antiviolentintelligence.ai/9423-invariantV2.pdf

---

## 🧭 Summary

> Agents can act.  
> This ensures they **act safely**.
