# OpenClaw Integration Example

This document shows how to integrate **agent-constraint-gate** with an OpenClaw-style agent.

---

## 🧭 Goal

Insert a constraint check between reasoning and action:

```text
reason → verify (45° + policy) → act
```

---

## 🔧 Where to hook

In OpenClaw (or similar agents), tool execution typically looks like:

```python
result = tool.execute(action)
```

You insert the constraint gate **right before this line**.

---

## ✅ Minimal Integration

```python
from constraint import verify_action

def safe_execute(action, tool):
    decision = verify_action(action)

    if decision["allow"]:
        return tool.execute(action)

    # Block or revise
    print("Blocked by constraint gate:", decision["reason"])
    return {
        "error": "blocked",
        "reason": decision["reason"],
        "action": decision["action"]
    }
```

---

## 📐 Example Action (with 45° constraint)

```python
action = {
    "tool": "http_request",
    "url": "https://api.openai.com",
    "method": "POST",
    "alignment_score": 0.65
}
```

Result:

```text
Blocked: Alignment below 45° threshold
```

---

## 📊 Full Flow

```text
User input
    ↓
LLM reasoning
    ↓
Proposed action
    ↓
verify_action(action)   ← THIS REPO
    ↓
(allow) → execute tool
(block) → return error
(revise) → send back to model
```

---

## 🔁 Optional: Revision Loop (stronger pattern)

Instead of blocking completely, you can loop back:

```python
if decision["action"] == "revise":
    action["feedback"] = decision["reason"]
    return model.revise(action)
```

This enables:

```text
reason → verify → revise → verify → act
```

---

## 🧠 What this adds to OpenClaw

Without constraint gate:

```text
reason → act
```

With constraint gate:

```text
reason → verify (alignment + policy) → act
```

---

## 🔒 Safety Impact

This prevents:

- execution of unsafe file paths  
- requests to unapproved domains  
- low-alignment actions (below 45° threshold)  
- unrestricted shell commands  

---

## 🚀 Summary

> OpenClaw handles reasoning and action.  
> agent-constraint-gate ensures actions are **verified before execution**.

---

## 🔗 Repo

https://github.com/<your-username>/agent-constraint-gate
