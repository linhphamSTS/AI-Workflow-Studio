# Phase 3 — Confirmation gate (human-in-the-loop)

The Phase 2 brief is a **draft proposal for review**, not a final answer.
Present it to the user and wait for an explicit decision. Anything in the
brief can change — tech stack (swap .NET → Node, Postgres → DynamoDB,
EKS → Lambda, etc.), diagram inventory (add / drop / reorder), section
outline, problem framing, scope inclusions. Do not start Phase 4 without
confirmation.

## How to present

Output the full `proposal_brief.md` content, then use AskUserQuestion with
these four options:

1. **OK, proceed to generation** — Phase 4 starts.
2. **Adjust tech stack** — ask follow-up: which layer, what to change. Examples: "swap backend to Java / Spring Boot", "drop Aurora, use DynamoDB", "replace EKS with Lambda", "use Azure instead of AWS". Loop back to Phase 2 with the adjustment noted in `requirements.json.constraints.tech_stack_forced` — Phase 2 must re-derive the architecture around the user's choice, not just slot in the new name.
3. **Adjust diagram list** — ask follow-up: add / remove / replace which diagrams. Loop back to Phase 2 step 4. Diagram count is whatever the user wants; honour their judgment.
4. **Adjust section outline** — ask follow-up: which sections to add / remove. Loop back to Phase 2 step 5.

## Loop budget

If the user adjusts 3 times without converging, ask them directly to write
the final ask in their own words rather than picking option buttons. This
avoids infinite ping-pong.

## Do NOT

- Re-run Phase 1 (re-reading the same RFP) on a Phase 3 adjustment. Phase 1
  output is stable; only Phase 2 re-runs.
- Proceed without an explicit OK. Silence is not consent.
- Hide concerns. If the user requests something the senior architect view
  flags as risky (e.g. "use Mongo for transactional data"), surface the
  concern before proceeding — but ultimately defer to the user's call.
