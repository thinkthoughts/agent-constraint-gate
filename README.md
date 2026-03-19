# agent-constraint-gate

Constraint gate for autonomous AI agents  
Verify actions before execution using re-lift5 (constraint threshold + policy enforcement)

---

## 📐 Spec (core)

action → left5 → score → threshold (45°) → policy → decision  
constraint_score ∈ [0,1], threshold = 1/√(1²+1²) ≈ 0.707  
decision ∈ {allow, revise, block}

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

- Numeric measure of whether an action satisfies required constraints before execution  
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
