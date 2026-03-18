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
reason → verify (45°) → act
```

The goal is simple:

> **Prevent unsafe tool execution before it happens**

---

## 📐 45° Constraint (Core Idea)

This repo enforces a geometric alignment threshold:

```text
cos(θ) ≥ 1 / √(1² + 1²) ≈ 0.707
```

Interpretation:
- Actions include an optional `alignment_score ∈ [0,1]`
- If `alignment_score < 0.707`, the action is **revised (blocked from execution)**

This adds a **continuous safety constraint** on top of rule-based checks.

---

## ⚠️ Problem

Agent frameworks (like OpenClaw) can:
- execute file operations  
- call APIs  
- send messages  

But they often lack a **pre-execution constraint check**, leading to:
- prompt injection exploits  
- data exfiltration  
- unintended autonomous actions  

---

## ✅ Solution

Add a **constraint gate** between reasoning and action.

The gate:
1. **Checks alignment (45° threshold)**  
2. **Verifies policy rules (YAML)**  
3. **Approves / blocks / revises before execution**

---

## 🔧 Minimal Example

```python
from constraint import verify_action

action = {
    "tool": "http_request",
    "url": "https://api.openai.com",
    "alignment_score": 0.65
}

decision = verify_action(action)

if decision["allow"]:
    execute(action)
else:
    print("Blocked:", decision["reason"])
```

---

## 📊 Behavior

| Alignment Score | Result |
|----------------|--------|
| ≥ 0.707        | Continue to policy checks |
| < 0.707        | Revise (blocked before execution) |

---

## 📐 Policy (example)

```yaml
rules:
  - tool: file_write
    allowed_paths:
      - "/workspace/output"
  - tool: http_request
    allowed_domains:
      - "api.openai.com"
```

---

## 🔗 OpenClaw Integration

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

- **Verify-before-act** (not react-after-harm)  
- **Geometric constraint (45°)** for alignment  
- **Policy-driven rules (YAML)**  
- **Framework-agnostic** (OpenClaw-compatible)  

---

## 🚀 Use Cases

- Autonomous agents (OpenClaw, AutoGPT-style systems)  
- Local agents with file/system access  
- API-calling assistants  
- Agent safety / alignment research  

---

## 📌 Status

Minimal prototype with:
- rule-based policy enforcement  
- 45° alignment constraint  

Contributions welcome.

---

## 📎 Reference

Antiviolent Intelligence framework:  
https://antiviolentintelligence.ai/9423-invariantV2.pdf

---

## 🧭 Summary

> Agents can act.  
> This ensures they **act within constraint**.
