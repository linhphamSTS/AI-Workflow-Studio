# Phase 2 — Analyze before you estimate

**No number is written in this phase.** Going straight to hours produces an estimate
nobody can defend, including you.

## Work out what this actually is

- **What kind of system.** One product or several? Consumer, business, internal? Does it
  aggregate other people's services, or own its own?
- **Front-end targets.** Count them: each web console, each mobile app. This drives the
  back-end-to-client ratio you will be judged against, and a native mobile app is 1.2-1.5×
  the equivalent web front-end.
- **What the client already has.** An existing system to integrate with, migrate from, or
  extend changes the shape completely. Look for "we already have" and "the current system".
- **Who the users are.** Every distinct role is screens, permissions and probably its own
  console.

## Find the money and the risk

Two things drive both cost and credibility:

- **Money paths.** Ledger, settlement, commission, payout, reconciliation, wallet, loyalty
  points. These are consistently under-estimated and a defect in them is a financial
  defect. Give them their own module.
- **External dependencies you do not control.** Authority gateways, banks, acquirers,
  national identity, partner systems, legacy interfaces. For each, ask: is there a
  sandbox? who obtains access, and on whose timeline? what happens if it never arrives?
  The answer to the last one belongs in the assumptions.

## Count the integrations

Go through the documents and write down, explicitly, **how many** of each external system
is in scope. Two banks. Three authorities. One aggregator per vertical. This count is the
single most common source of a badly wrong estimate: a row reading "authority integration"
priced once when the client meant five.

The count then goes into the assumption on that task, so anything beyond it is a change
request at the same unit effort.

## Design the breakdown (AUTHOR mode)

Aim for modules that map to how the work will actually be delivered and, where the
documents have a pricing schedule, to how it will be priced:

```
1  Infrastructure and cloud foundation
2  Shared platform services            <- everything more than one product uses
3  Product A
4  Product B
5  Product C
6  Non-functional requirements
```

**Put everything shared in one module rather than repeating it per product.** It is how
the work is really done, it stops the same service being counted three times, and where
the client asked for cost synergy it is the evidence.

Within a module: level-2 groups for capability areas, level-3 leaf tasks for the work.
Each leaf should be one feature across whichever disciplines it touches.

## Ask the structural questions

An RFP describes journeys. It rarely describes the structures the journeys attach to. For
every journey ask:

- Which entity, account or tenant owns this data?
- Who administers the users of that entity?
- What creates it in the first place?

A missing answer is usually a missing task. This exact gap has been found in a delivered
estimate.

## Present the analysis

Before the gate, write out:

1. What the system is, in a paragraph
2. The front-end targets, counted
3. The proposed module structure, or the client's structure in FILL mode
4. The heavy modules and why
5. The external dependencies, with the assumed count of each
6. Anything the documents leave unanswered
7. Anything explicitly out of scope
8. Technical recommendations that move the hours — cross-platform versus native mobile is
   usually the largest single one

Then Phase 3.
