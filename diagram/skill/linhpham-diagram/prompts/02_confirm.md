# Phase 2 — Confirm gate (human-in-the-loop)

Never render before the user confirms the normalized spec. This is mandatory.

Show the user the **diagram brief** from Phase 1 in a compact form:

- **Type & renderer** (e.g. "Sequence diagram — PIL renderer").
- **Purpose** — one line.
- **Elements** — the node/actor/boundary list and the key edges, so the user can see the content
  before it is drawn. For a flow/sequence, list the steps in order.
- **Orientation / cloud / level** — the decisions taken.
- **Assumptions** — anything you filled that the user did not state.
- **Caption**: the planned `<Type>: <Scope>` (a colon, never a dash).

Then ask the user to **confirm or adjust**. Offer easy edits: add/remove/rename an element, change an
edge, switch orientation, change the type. Loop on the brief (cheap) until the user says go — do not
render on the first pass unless the user explicitly says "just draw it".

Only after an explicit OK, proceed to Phase 3 (Generate).
