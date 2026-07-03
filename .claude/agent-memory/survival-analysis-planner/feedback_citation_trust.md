---
name: feedback-citation-trust
description: When the requester supplies exact file:line citations already verified in their prompt, don't re-verify all of them before delivering — spot-check the load-bearing ones and move to the deliverable.
metadata:
  type: feedback
---

When a coordinator/user prompt already contains precise file:line citations (e.g. "line 646 in signature_service.py") and says they've confirmed the codebase, it's fine to do a first-pass verification of the most load-bearing claims (the ones the recommendation actually hinges on), but do not re-derive every single citation before producing the deliverable — the coordinator explicitly interrupted a session to say this slows things down.

**Why:** In [[project_therapy_km_curves]] the coordinator gave ~10 precise file:line references up front; I re-verified all of them via Read/Bash before writing the plan, which was correct the first time (it surfaced a real discrepancy — `TherapyEvidenceRecord` actually lives in `chat_routes.py`, not `signature_models.py` as the prompt guessed) but the coordinator then had to explicitly tell me to stop further exploration and ship the plan.

**How to apply:** Do one focused verification pass on claims that change the recommendation (e.g. "does this field have CI bounds", "is this function already gated by a sample-size floor") — these are worth catching because they change the plan's conclusion. Skip re-verifying claims that are just context/color and don't change what gets recommended. When in doubt about whether more exploration is welcome, produce a partial deliverable rather than open another round of tool calls.
