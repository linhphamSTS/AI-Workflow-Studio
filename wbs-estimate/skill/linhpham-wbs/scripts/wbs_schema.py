# -*- coding: utf-8 -*-
"""The contract between the estimating phase and the building phase.

Phase 4 writes `wbs.json`; `build_wbs.py` renders it and `verify_wbs.py` checks it.
Keeping the judgement in JSON and the rendering in Python means the numbers can be
reviewed, diffed and re-run without touching any code, and a re-run produces the same
workbook rather than a differently-worded one.

    {
      "project":       "Acme Platform",          // used in the filename and the cover
      "currency_note": "man-hours",
      "mode":          "author" | "fill",
      "columns":       ["ui", "be", "fe", "mob", "ai"],   // in sheet order, F onward
      "column_labels": ["UI/UX Design", "Back-end Development",
                        "Front-end Development", "Mobile", "AI"],

      "zero_columns":  ["ui"],        // priced at zero on purpose, rows kept
      "zero_modules":  ["6"],         // same, by leading module number
      "zero_note":     "why they are zero, shown on the cover",
      "competitive":   1.0,           // 1.0 = no discount taken in the hours

      "sheets": [                     // one per commercial line item
        {"name": "Shared Platform", "modules": [1, 2]},
        {"name": "App 1",           "modules": [3]}
      ],

      "rows": [
        {"kind": "L1", "id": 1,       "title": "INFRASTRUCTURE"},
        {"kind": "L2", "id": "1.1",   "title": "Cloud foundation"},
        {"kind": "T",  "id": "1.1.1",
         "group":   "Landing zone",        // column B; null continues the merge above
         "feature": "Cloud landing zone",
         "desc":    "- bullet\n- bullet",
         "assum":   "Assumption:\n- ...",
         "ui": 0, "be": 8, "fe": 0, "mob": 0, "ai": 0,
         "refs":    ["CC-01", "SEC-03"],   // requirement ids this task satisfies
         "risk":    {"level": "High",      // optional
                     "risk": "what can go wrong",
                     "mitigation": "what is done about it"}}
      ],

      "factors": [                    // the explicit uplift table, printed on build
        {"id": "2.1.2", "col": "be", "base": 18, "final": 23,
         "rule": "M-NS", "note": "no public sandbox"}
      ],
      "uncertainty": {                // selective, never blanket
        "factor": 1.15,
        "scopes": [{"prefix": "3.6", "reason": "one RFP line hides a whole ATS"}]
      },

      "requirements": [               // every id in the source documents
        {"id": "CC-01", "text": "...", "priority": "M"}
      ],
      "out_of_scope": [{"item": "...", "reason": "..."}]
    }

Anything optional may be omitted. Anything present is validated, because a spec that is
silently wrong produces a workbook that is confidently wrong.
"""

KINDS = ('L1', 'L2', 'T')
RISK_LEVELS = ('High', 'Medium')


class SpecError(Exception):
    """Raised with every problem found, so one run fixes them all."""


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(spec):
    """Return the spec, or raise SpecError listing everything wrong with it."""
    e = []

    for key in ('project', 'columns', 'rows', 'sheets'):
        if not spec.get(key):
            e.append(f'missing required key: {key}')
    if e:
        raise SpecError('\n'.join(' ! ' + x for x in e))

    cols = spec['columns']
    labels = spec.get('column_labels') or []
    if labels and len(labels) != len(cols):
        e.append(f'column_labels has {len(labels)} entries for {len(cols)} columns')

    rows = spec['rows']
    leaves = [r for r in rows if r.get('kind') == 'T']
    if not leaves:
        e.append('no leaf tasks: a WBS with only section rows estimates nothing')

    seen_ids, order = set(), []
    for i, r in enumerate(rows):
        kind = r.get('kind')
        where = f'rows[{i}] id={r.get("id")!r}'
        if kind not in KINDS:
            e.append(f'{where}: kind must be one of {KINDS}')
            continue
        rid = str(r.get('id', '')).strip()
        if not rid:
            e.append(f'{where}: missing id')
            continue
        if rid in seen_ids:
            e.append(f'{where}: duplicate id')
        seen_ids.add(rid)
        try:
            order.append([int(p) for p in rid.split('.')])
        except ValueError:
            e.append(f'{where}: id must be dotted integers')

        if kind in ('L1', 'L2'):
            if not r.get('title'):
                e.append(f'{where}: section row needs a title')
            if any(_num(r.get(c)) and r.get(c) for c in cols):
                e.append(f'{where}: a section row must carry no hours; '
                         'the total is a formula over its children')
            continue

        # leaf
        if not r.get('feature'):
            e.append(f'{where}: leaf needs a feature')
        if not (r.get('assum') or '').strip():
            e.append(f'{where}: leaf needs an assumption; an unstated assumption is '
                     'an unpriced risk')
        vals = []
        for c in cols:
            v = r.get(c, 0) or 0
            if not _num(v):
                e.append(f'{where}: {c}={v!r} is not a number')
                continue
            if v < 0:
                e.append(f'{where}: {c} is negative')
            if float(v) != int(v):
                e.append(f'{where}: {c}={v} is not a whole hour')
            vals.append(v)
        if vals and not any(vals):
            e.append(f'{where}: every column is zero. Either estimate it, or list it in '
                     'out_of_scope, or zero it deliberately via zero_columns/zero_modules')
        risk = r.get('risk')
        if risk is not None:
            if risk.get('level') not in RISK_LEVELS:
                e.append(f'{where}: risk.level must be one of {RISK_LEVELS}')
            for k in ('risk', 'mitigation'):
                if not (risk.get(k) or '').strip():
                    e.append(f'{where}: risk.{k} is empty. A risk without a mitigation '
                             'is a worry, not a plan')

    for i in range(1, len(order)):
        if order[i] <= order[i - 1]:
            e.append(f'ids out of ascending order at {rows[i].get("id")!r} '
                     f'(after {rows[i - 1].get("id")!r})')

    modules = {int(str(r['id']).split('.')[0]) for r in rows if str(r.get('id', ''))[:1].isdigit()}
    covered = set()
    for s in spec['sheets']:
        if not s.get('name'):
            e.append('a sheet has no name')
        for m in s.get('modules', []):
            if m in covered:
                e.append(f'module {m} appears on more than one sheet, so it would be '
                         'counted twice')
            covered.add(m)
    missing = modules - covered
    if missing:
        e.append(f'modules not assigned to any sheet, so they would be dropped: '
                 f'{sorted(missing)}')

    by_id = {str(r.get('id')): r for r in rows}
    for f in spec.get('factors', []):
        rid = str(f.get('id'))
        if rid not in by_id:
            e.append(f'factors: unknown task id {rid!r}')
            continue
        if f.get('col') not in cols:
            e.append(f'factors[{rid}]: unknown column {f.get("col")!r}')
            continue
        if by_id[rid].get(f['col']) != f.get('base'):
            e.append(f'factors[{rid}].{f["col"]}: base {f.get("base")} does not match the '
                     f'row value {by_id[rid].get(f["col"])}. Update the factor when the '
                     'base estimate changes, or the audit trail is fiction')

    for c in spec.get('zero_columns', []):
        if c not in cols:
            e.append(f'zero_columns: unknown column {c!r}')

    if e:
        raise SpecError('\n'.join(' ! ' + x for x in e))
    return spec


def leaf_rows(spec):
    return [r for r in spec['rows'] if r.get('kind') == 'T']


def module_of(row):
    return str(row.get('id', '')).split('.')[0]
