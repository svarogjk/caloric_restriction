---
name: user-communication-style
description: How svarogjk prefers strategy/planning help delivered on this project
metadata:
  type: feedback
---

The user reads the code deeply themselves before asking for a strategy —
requests typically already cite exact file paths, function names, and even
approximate line numbers, and pre-empt the obvious objections (e.g. already
notes permission scope, already diagnosed a root cause and wants it
confirmed, not re-derived from scratch).

**How to apply**: verify their claims against current code rather than
re-explaining what they already showed they understand; skip broad surveys
of "how this could be done" and go straight to a concrete, numbered
recommendation tied to specific functions/fields/thresholds they can
implement directly. They explicitly ask for "focused, not exhaustive"
output — prefer 4-6 decisive recommendations with rationale over a long
options matrix. Grounding claims in things that don't yet exist in the code
(e.g. a threshold constant, a new response field) is fine as long as it's
flagged as a proposed addition, not presented as already-existing behavior.
