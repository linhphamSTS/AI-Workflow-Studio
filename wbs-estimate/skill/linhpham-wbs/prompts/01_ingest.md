# Phase 1 — Ingest and detect the mode

## Read everything

Read **every file in the project folder**, including the ones in subfolders and the ones
that look like leftovers. `.pdf`, `.docx`, `.xlsx`, `.md`, `.txt`, `.csv`. A requirement
hiding in a "questions and answers" file or a sample data sheet is still a requirement, and
sample data is often the only place the real field-level complexity shows up.

If the folder is large, use `scripts/ingest.py` to build a digest first, but **do not stop
at the digest**. Open any spreadsheet directly: a WBS or a data model loses its structure
when flattened to text.

**Watch the per-file truncation limit.** A digest tool that caps each file will silently
drop the tail of a long RFP, which is where the appendices and the required-contents list
usually live. Raise the cap or read the original.

## Detect the mode

| Signal | Mode |
|---|---|
| A spreadsheet with a task-ID column (`1`, `1.1`, `1.1.1`) and empty effort columns | **FILL** |
| Only an RFP, brief, or requirements document | **AUTHOR** |
| A spreadsheet that is a feature list, not a numbered breakdown | **AUTHOR**, but reuse their grouping |

State the mode and the evidence. The user can override at the gate.

### If FILL

Record, exactly:

- the sheet name, the header row, and which column holds the ID
- which columns are effort columns, and their labels in the client's own words
- how many task rows there are, and which are section rows
- any total row and the formula in it

**Never add, remove, renumber or reword a row.** A client who sends a WBS is comparing
bids line by line. A changed structure makes that comparison impossible and reads as
carelessness, whatever the hours say.

If their structure has a genuine problem — a row bundling five integrations, a missing
module — raise it in the analysis as a note. Do not fix it in their file.

### If AUTHOR

You will design the breakdown in Phase 2.

## Build the requirement list

Extract **every requirement identifier** in the documents: `CC-01`, `FR-3.2`, `A1-05`,
whatever the scheme is. Capture the id, the verbatim text, and the priority if one is
given. This becomes `requirements` in the spec and it is what Phase 6 proves coverage
against.

If the documents have no identifier scheme, create one from the section numbering and say
that you did. Coverage cannot be proven against requirements that were never enumerated,
and on an authored WBS that is the only thing standing between the estimate and a silently
missing feature.

## Output

A short written summary: what was read, the mode and why, how many requirements were
found, and anything in the documents that looks contradictory or missing. Then Phase 2.
