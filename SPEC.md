# SPEC.md

## agent-constraint-gate Specification

This document defines the minimal, stable specification for the **re-lift5 constraint gate**.

---

## 🧭 Overview

The system enforces a verification step between reasoning and execution:

reason → verify (re-lift5: constraint threshold + policy) → act

---

## 📐 Core Concepts

### 1. action (external input)

An action is a dictionary proposed by an agent:

```json
{
  "tool": "http_request",
  "url": "https://api.openai.com",
  "constraint_score": 0.82
}
```

Required fields:
- tool

Optional fields:
- parameters (url, path, method, etc.)
- constraint_score (may be computed internally)

---

### 2. left5 (normalized structure)

Internal representation of action:

```json
{
  "tool": "...",
  "params": {...},
  "constraint_score": float,
  "metadata": {...}
}
```

Purpose:
- normalize inputs
- ensure consistent verification
- isolate external variability

---

### 3. constraint_score

constraint_score ∈ [0,1]

Definition:
- numeric measure of whether an action satisfies required constraints before execution

---

### Threshold (45° constraint)

constraint_score ≥ 1 / √(1² + 1²) ≈ 0.707

Meaning:
- ≥ threshold → eligible for policy evaluation
- < threshold → action must be revised or blocked

---

### 4. re-lift5

re-lift5 = verification layer

Components:
1. constraint threshold check
2. policy enforcement

An action must pass both.

---

### 5. policy

Defined in policy.yaml

Structure:
```yaml
rules:
  - tool: http_request
    allowed_domains:
      - "api.openai.com"
```

Purpose:
- define allowed actions
- restrict parameters (paths, domains, commands)

---

## 🔁 Verification Pipeline

```text
action → left5 → constraint_score → threshold check → policy check → decision
```

---

## ⚙️ Decision States

The system returns:

### allow
Action passes constraint threshold and policy

### revise
Action fails constraint threshold but may be corrected

### block
Action violates policy or is unsafe

---

## 📊 Decision Object

Example:

```json
{
  "allow": false,
  "action": "revise",
  "reason": "Constraint score below threshold",
  "details": {
    "constraint_score": 0.63,
    "threshold": 0.707
  }
}
```

---

## 🔧 constraint_score Computation (optional)

constraint_score may be:

### Provided externally
- passed by agent

### Computed internally
Example factors:
- tool safety
- parameter safety
- domain/path safety
- method safety
- risk penalties

---

## 🧠 Design Principles

- verify-before-act
- numeric constraint threshold (45°)
- policy-driven restrictions
- minimal, framework-agnostic interface

---

## 🚀 Summary

An action is allowed iff:

constraint_score ≥ threshold  
AND  
policy rules are satisfied

Otherwise:
→ revise OR block

---

## 📎 Reference

https://antiviolentintelligence.ai/9423-invariantV2.pdf
