# OpenClaw Integration Example

This document shows how to integrate **agent-constraint-gate** with an OpenClaw-style agent using the updated spec:

- re-lift5 (verification layer)
- constraint_score (numeric threshold)
- left5 (normalized internal structure)

---

## 🧭 Goal

Insert a constraint check between reasoning and action:

reason → verify (re-lift5: constraint threshold + policy) → act

---

## 🔧 Where to hook

In OpenClaw (or similar agents), tool execution typically looks like:

```python
result = tool.execute(action)
```

You insert the constraint gate **right before execution**.

---

## ✅ Minimal Integration

```python
from constraint import verify_action

def safe_execute(action, tool):
    decision = verify_action(action)  # re-lift5 enforcement

    if decision["allow"]:
        return tool.execute(action)

    # Block or revise
    print("Blocked by re-lift5:", decision["reason"])
    return {
        "error": "blocked",
        "reason": decision["reason"],
        "action": decision["action"]
    }
```

---

## 📐 Example Action

```python
action = {
    "tool": "http_request",
    "url": "https://api.openai.com",
    "method": "POST",
    "constraint_score": 0.65
}
```

Result:

Blocked before execution due to constraint threshold (< 0.707)

---

## 📊 Full Flow

User input  
↓  
LLM reasoning  
↓  
Proposed action (external)  
↓  
re-lift5 verification (this repo)  
↓  
(allow) → execute tool  
(revise/block) → return decision  

---

## 🧠 Internal Structure (left5)

Inside the constraint layer, actions are normalized:

action → left5

left5 includes:

- tool  
- params (path, url, method, etc.)  
- constraint_score  
- metadata  

This ensures consistent verification before policy checks.

---

## 🔁 Optional: Revision Loop

Instead of blocking completely, loop back:

```python
if decision["action"] == "revise":
    action["feedback"] = decision["reason"]
    return model.revise(action)
```

Flow becomes:

reason → verify → revise → verify → act

---

## 🔒 Safety Impact

This prevents:

- execution of unsafe file paths  
- requests to unapproved domains  
- actions below constraint threshold  
- unrestricted system commands  

---

## 🚀 Summary

OpenClaw handles reasoning and action.  
re-lift5 ensures actions meet constraint + policy before execution.

---

## 🔗 Repo

https://github.com/<your-username>/agent-constraint-gate
