# agent-constraint-gate

**Constraint gate for autonomous AI agents**  
Verify actions before execution using **re-lift5 (constraint threshold + policy enforcement)**  
(OpenClaw-compatible)

---

## 🧭 Overview

Most agent systems follow:

reason → act

This repo introduces a constraint layer:

reason → verify (re-lift5: constraint threshold + policy) → act

---

## 📐 re-lift5 (Core Specification)

**re-lift5** is the verification layer combining:

- **constraint_score (numeric constraint check)**
- **policy enforcement (YAML rules)**

An action must satisfy both before execution.

---

## 📊 constraint_score

constraint_score ∈ [0,1]

- Represents how well an action satisfies required constraints before execution  
- Acts as a **pre-execution filter**

### Threshold

constraint_score ≥ 1 / √(1² + 1²) ≈ 0.707

Interpretation:

- ≥ 0.707 → eligible for policy check  
- < 0.707 → revise (blocked before execution)

---

## ⚠️ Problem

Agent frameworks (e.g., OpenClaw) can:

- execute file operations  
- call APIs  
- run system commands  

But typically lack:

**a pre-execution constraint layer**

This leads to:

- prompt injection exploits  
- unsafe tool execution  
- data exfiltration  
- unintended autonomous actions  

---

## ✅ Solution

Insert a **re-lift5 constraint gate** between reasoning and action.

Pipeline:

1. constraint_score check (threshold)
2. policy check (YAML rules)
3. allow / revise / block

---

## 🔧 Minimal Example

```python
from constraint import verify_action

action = {
    "tool": "http_request",
    "url": "https://api.openai.com",
    "constraint_score": 0.82
}

decision = verify_action(action)

if decision["allow"]:
    execute(action)
else:
    print("Blocked:", decision["reason"])
```

---

## 📐 Policy Layer (YAML)

```yaml
rules:
  - tool: file_write
    allowed_paths:
      - "/workspace/output"

  - tool: http_request
    allowed_domains:
      - "api.openai.com"
```

Policy defines:
what is allowed

re-lift5 ensures:
whether the action qualifies before execution

---

## 🔗 OpenClaw Integration

OpenClaw reasoning  
↓  
re-lift5 constraint gate (this repo)  
↓  
tool execution  

Hook point:

```python
decision = verify_action(action)
```

---

## 🧠 Design Principles

- Verify-before-act  
- Numeric constraint threshold (45°)  
- Policy-driven rules  
- Framework-agnostic  

---

## 📐 Formal Specification

An action is allowed iff:

constraint_score ≥ 1 / √(1² + 1²)  
AND  
action satisfies policy.yaml  

Otherwise:

→ action = revise OR block

---

## 🚀 Use Cases

- Autonomous agents (OpenClaw, AutoGPT-style systems)  
- Local agents with system access  
- API-executing assistants  
- Agent safety / alignment research  

---

## 📌 Status

Minimal working prototype with:

- numeric constraint enforcement  
- policy validation  
- modular integration  

---

## 📎 Reference

https://antiviolentintelligence.ai/9423-invariantV2.pdf

---

## 🧭 Summary

Agents can act.  
re-lift5 ensures they act within constraint + policy.
