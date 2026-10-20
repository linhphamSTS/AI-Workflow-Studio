#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a WBS workbook from `wbs.json`.

    python build_wbs.py --spec wbs.json --out "WBS_Acme.xlsx"

The estimate lives in the spec; this file only draws it. Two consequences worth
knowing: a re-run of the same spec produces the same workbook, and changing a number
never means editing code.

The factor layer is applied here rather than baked into the spec's numbers, so the
build prints a base -> final -> rule table. An estimate whose reasoning is invisible
cannot be reviewed, and the most expensive mistake in the reference log was an estimate
that applied only the downward factor because nothing showed the upward ones missing.

Sheet layout follows the reference workbooks: one sheet per commercial line item, plus
a Cover that rolls up and an Out of Scope sheet that draws the boundary.
"""
import argparse
import json
import os
import re
import sys

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xlsx_style import (  # noqa: E402
    A_CENTER, A_LEFT_CENTER, A_LEFT_TOP, B_LTB, B_NONE, B_RTB, B_TB, C_EFFORT, C_HEADER,
    C_HEADER_TOT, C_L1, C_L2, C_LEAF, C_OOS_HDR, C_TOTAL, FONT, autofit_row_heights,
    banner, bold_labels, notes, style,
)
from openpyxl.styles import Font  # noqa: E402
import wbs_schema  # noqa: E402

WIDTHS = {'A': 10.43, 'B': 33.29, 'C': 63.0, 'D': 87.0, 'E': 60.14,
          'F': 12.57, 'G': 15.71, 'H': 15.71, 'I': 10.5, 'J': 9.0, 'K': 12.14}
COVER_WIDTHS = {'A': 48, 'B': 13, 'C': 15, 'D': 15, 'E': 11, 'F': 9, 'G': 13}
OOS_WIDTHS = {'A': 6.57, 'B': 60.0, 'C': 70.0}
DEFAULT_LABELS = {'ui': 'UI/UX Design', 'devops': 'Devops', 'be': 'Back-end Development',
                  'fe': 'Front-end Development', 'mob': 'Mobile', 'ai': 'AI'}


SITUATION_FACTOR = {
    'existing client': (0.90, 0.90),
    'follow-on': (0.90, 0.90),
    'new client': (0.85, 0.90),
    'many vendors bidding': (0.85, 0.90),
    'sole bidder': (0.95, 1.00),
    'referral': (0.95, 1.00),
    'exclusive': (0.95, 1.00),
    'complex, few vendors capable': (0.95, 1.00),
}


# ------------------------------------------------------------------ factor layer
def apply_factors(spec):
    """Explicit uplifts, then the selective uncertainty factor, then deliberate zeros."""
    cols = spec['columns']
    by_id = {str(r['id']): r for r in spec['rows']}
    log = []

    for f in spec.get('factors', []):
        row = by_id[str(f['id'])]
        row[f['col']] = f['final']
        log.append(('adjust', f['id'], f['col'], f['base'], f['final'], f.get('rule', ''),
                    f.get('note', '')))

    unc = spec.get('uncertainty') or {}
    factor = unc.get('factor')
    if factor:
        adjusted = {(str(f['id']), f['col']) for f in spec.get('factors', [])}
        for scope in unc.get('scopes', []):
            prefix = scope['prefix'] + '.'
            before = after = 0
            for row in wbs_schema.leaf_rows(spec):
                if not str(row['id']).startswith(prefix):
                    continue
                for c in cols:
                    v = row.get(c) or 0
                    if not v:
                        continue
                    before += v
                    if (str(row['id']), c) in adjusted:
                        after += v          # a stronger rule already moved it
                        continue
                    row[c] = max(1, int(v * factor + 0.5))
                    after += row[c]
            if before:
                log.append(('uncertainty', scope['prefix'], '', before, after,
                            'x%.2f' % factor, scope.get('reason', '')))

    for c in spec.get('zero_columns', []):
        out = sum(r.get(c) or 0 for r in wbs_schema.leaf_rows(spec))
        n = sum(1 for r in wbs_schema.leaf_rows(spec) if r.get(c))
        for r in wbs_schema.leaf_rows(spec):
            r[c] = 0
        log.append(('zero', 'column ' + c, '', out, 0, 'absorbed', '%d row(s)' % n))
    for m in spec.get('zero_modules', []):
        rows_ = [r for r in wbs_schema.leaf_rows(spec)
                 if str(r['id']) == str(m) or str(r['id']).startswith(str(m) + '.')]
        out = sum(r.get(c) or 0 for r in rows_ for c in cols)
        for r in rows_:
            for c in cols:
                r[c] = 0
        log.append(('zero', 'module ' + str(m), '', out, 0, 'absorbed',
                    '%d row(s), kept so the scope stays visible' % len(rows_)))

    # Section 1 of the rules puts the competitive factor INSIDE the standard formula:
    # base x AI x competitive is the number the client is given. Leaving it at 1.0 by
    # default is how a bid is lost to a cheaper vendor, so when the spec does not set it
    # the situation table decides, and the floors below stop it going too far.
    comp = spec.get('competitive')
    if comp is None:
        sit = str(spec.get('bid_situation') or '').lower()
        for key, (lo, hi) in SITUATION_FACTOR.items():
            if key in sit:
                comp = hi          # the cautious end of the range the table gives
                break
        comp = comp or 1.0
    # Write it back, or the factor log and the competitive position report different
    # numbers in the same run and neither is obviously the wrong one.
    spec['competitive'] = comp
    pre_comp = {str(r['id']): sum(r.get(c) or 0 for c in cols if c not in
                                  (spec.get('zero_columns') or []))
                for r in wbs_schema.leaf_rows(spec)}
    if comp and comp != 1.0:
        before = sum(r.get(c) or 0 for r in wbs_schema.leaf_rows(spec) for c in cols)
        for r in wbs_schema.leaf_rows(spec):
            for c in cols:
                if r.get(c):
                    r[c] = max(1, int(r[c] * comp + 0.5))
        after = sum(r.get(c) or 0 for r in wbs_schema.leaf_rows(spec) for c in cols)
        # A percentage applied per task, to whole hours, mostly does not survive the
        # rounding. Half-up rounding leaves 1 to 5 hours untouched at x0.90, and a
        # well-formed WBS has most tasks in exactly that band, so the intended discount
        # can arrive as almost nothing. Recording what was actually realised is the
        # difference between giving a discount and believing you gave one.
        realised = (1 - after / before) if before else 0.0
        spec['_competitive_realised'] = realised
        spec['_competitive_before'] = before
        log.append(('competitive', 'all', '', before, after, 'x%.2f' % comp,
                    'intended -%.0f%%, realised -%.1f%%  (%s)'
                    % ((1 - comp) * 100, realised * 100,
                       spec.get('bid_situation') or 'situation not stated')))
    apply_floors(spec, log, pre_comp)
    return log


def print_factor_log(log, comp):
    if not log:
        print('Factor layer: nothing applied.')
        return
    print('=' * 96)
    print('FACTOR LAYER  (base -> final, and the rule that moved it)')
    print('=' * 96)
    print('%-12s %-16s %-5s %8s %8s  %-12s %s'
          % ('kind', 'what', 'col', 'base', 'final', 'rule', 'note'))
    for kind, what, col, base, final, rule, note in log:
        print('%-12s %-16s %-5s %8s %8s  %-12s %s'
              % (kind, str(what)[:16], col, base, final, rule, str(note)[:44]))
    print()
    print('Competitive factor: x%.2f%s'
          % (comp, '' if comp != 1.0 else '  (hours not discounted)'))
    print()



# Section 1 of the rules: the floors are what protect the margin, not refusing the discount.
# Below these a task has no room for its own testing, so the saving is borrowed from quality.
FLOOR_RULES = (
    (('auth', 'login', 'sign-in', 'sso', 'oauth', 'mfa', 'otp', 'password'), 6,
     'security work is not cut'),
    (('integrat', 'gateway', 'webhook', 'connector', 'api of', 'third-part', 'soap',
      'sftp', 'erp', 'hrms'), 6, 'retry, error handling and rate limits'),
    (('infrastructur', 'landing zone', 'pipeline', 'cluster', 'network', 'terraform',
      'iac', 'environment'), 4, 'wrong infrastructure takes the project down'),
    ((), 3, 'under three hours leaves no room to test'),
)


def floor_for(row):
    # Feature name only, whole words from the start: a description reworded, or a group
    # called "Onboarding & Authentication", must not move the hours of the task.
    text = str(row.get('feature') or '').lower()
    for words, floor, why in FLOOR_RULES:
        if not words:
            return floor, why
        if any(re.search(r'\b' + re.escape(w), text) for w in words):
            return floor, why
    return 3, 'under three hours leaves no room to test'


def apply_floors(spec, log, before):
    """Raise any leaf the competitive factor pushed under its floor.

    The competitive factor is applied to win the work; the floors are applied so winning it
    is still worth having. They are not in tension: one moves the price, the other refuses to
    move the part of the estimate that pays for testing the work.

    Only a task the factor actually reduced is raised, and never above what it was before
    the factor. A small task the estimator wrote as small stays as written: the floor is a
    guard on the discount, not a second estimate.
    """
    cols = spec['columns']
    zero = set(spec.get('zero_columns') or [])
    for row in wbs_schema.leaf_rows(spec):
        if wbs_schema.is_zeroed(row, spec):
            continue
        live = [c for c in cols if c not in zero and (row.get(c) or 0)]
        total = sum(row.get(c) or 0 for c in live)
        pre = before.get(str(row['id']), total)
        if not total or total >= pre:
            continue
        floor, why = floor_for(row)
        floor = min(floor, pre)
        if total >= floor:
            continue
        biggest = max(live, key=lambda c: row.get(c) or 0)
        row[biggest] += floor - total
        log.append(('floor', row['id'], biggest, total, floor, '>=%dh' % floor, why))


# ------------------------------------------------------- competitive position


def competitive_position(spec, total):
    """What makes this number competitive, in figures rather than adjectives.

    A percentage taken off the hours is the weakest lever available and the only one that
    cannot be undone later. The strong levers are already in the estimate and normally go
    unstated: the discount the delivery model has already granted, and the work quoted once
    instead of once per product. Both are computed here so they can be quoted in the bid
    instead of reconstructed by hand afterwards.

    Returns (client_facing_lines, internal_lines).
    """
    client, internal = [], []
    cols = spec['columns']

    ai = spec.get('ai_factor') or {}
    blended = ai.get('blended')
    if ai.get('where') != 'none' and blended:
        pre = total / blended
        granted = int(round(pre - total))
        internal.append(('Delivery-model discount already granted',
                         '%d h  (effective x%.2f, %s). Applied %s, so it must not be taken '
                         'again' % (granted, blended, ai.get('note', 'per task type'),
                                    'inside the base numbers'
                                    if ai.get('where') == 'in_base' else 'as factor entries')))

    reuse = spec.get('reuse') or {}
    shared = [n for n in (reuse.get('shared_sheets') or [])]
    consumers = reuse.get('consumers') or 0
    if shared and consumers > 1:
        sheet_mods = {}
        for sh in spec['sheets']:
            sheet_mods[sh['name']] = {str(m) for m in sh['modules']}
        shared_mods = set()
        for n in shared:
            shared_mods |= sheet_mods.get(n, set())
        shared_h = sum(r.get(c) or 0 for r in wbs_schema.leaf_rows(spec) for c in cols
                       if wbs_schema.module_of(r) in shared_mods)
        saved = shared_h * (consumers - 1)
        naive = total + saved
        client.append(('Shared platform quoted once, not %d times' % consumers,
                       '%d h of shared work serves %d products, so %d h are not charged'
                       % (shared_h, consumers, saved)))
        if naive:
            client.append(('Against a build with no reuse',
                           '%d h. This estimate is %.0f%% of it' % (naive, 100.0 * total / naive)))

    comp = spec.get('competitive', 1.0)
    sit = str(spec.get('bid_situation') or '').strip()
    lo = hi = None
    for key, (a, b) in SITUATION_FACTOR.items():
        if key in sit.lower():
            lo, hi = a, b
            break
    line = 'x%.2f' % comp
    if lo is not None:
        line += '. The situation "%s" suggests x%.2f to x%.2f' % (sit, lo, hi)
        if comp > hi:
            line += '. HOLDING ABOVE THE RANGE: say why in the report, or take the discount'
    internal.append(('Competitive factor', line))
    realised = spec.get('_competitive_realised')
    if realised is not None and comp < 1.0:
        intended = 1 - comp
        internal.append(('Discount actually realised',
                         '-%.1f%% of %d h, against -%.0f%% intended'
                         % (realised * 100, spec.get('_competitive_before') or 0,
                            intended * 100)))
        if realised < intended * 0.5:
            internal.append(('WHY THE DISCOUNT DID NOT LAND',
                             'whole-hour rounding absorbed it: at this factor a task '
                             'of 1 to 5 hours does not move, and most tasks are in '
                             'that band. A percentage cannot be expressed per task on '
                             'a fine-grained WBS. Take it as a stated discount on the '
                             'total, on the rate, or by moving scope into phase 1, and '
                             'do not report a reduction the hours do not contain'))
    return client, internal


def phase1_total(spec):
    """Hours in the cheaper option. A subset of the same ids, so the two options can never
    disagree about what a task costs."""
    p1 = spec.get('phase1') or {}
    inc = [str(x) for x in (p1.get('include') or [])]
    if not inc:
        return None, None
    cols = spec['columns']
    rows = [r for r in wbs_schema.leaf_rows(spec)
            if any(str(r['id']) == p or str(r['id']).startswith(p + '.') for p in inc)]
    return sum(r.get(c) or 0 for r in rows for c in cols), len(rows)


def print_competitive_position(spec, total):
    client, internal = competitive_position(spec, total)
    if not (client or internal):
        return
    print('=' * 96)
    print('COMPETITIVE POSITION  (the figures that argue the price, not adjectives)')
    print('=' * 96)
    for label, value in client:
        print('  [bid]      %-44s %s' % (label, value))
    for label, value in internal:
        print('  [internal] %-44s %s' % (label, value))
    p1, n1 = phase1_total(spec)
    if p1:
        # Only printed when the spec actually defines one. Offering a cut-down option is
        # a commercial choice, so the build states it when asked and stays quiet when not.
        p1o = spec['phase1']
        print()
        print('    Full scope   %6d h   %d task(s)'
              % (total, len(wbs_schema.leaf_rows(spec))))
        print('    %-12s %6d h   %d task(s)   %.0f%% of full'
              % (p1o.get('name', 'phase 1')[:12], p1, n1, 100.0 * p1 / total))
        print('    gives up: %s' % p1o.get('note', ''))
    print()
    print('  [bid] lines may be quoted to the client. [internal] lines are grounds for')
    print('  defending the number and are deliberately kept out of the workbook: a delivery')
    print('  discount a client can see is a discount they will ask for twice.')
    print()


# ------------------------------------------------------------------ WBS sheet
def build_sheet(ws, spec, modules):
    cols = spec['columns']
    T = TEXT[lang_of(spec)]
    labels = effort_labels(spec, T)
    n_eff = len(cols)
    first_eff = 6
    total_col = first_eff + n_eff              # K when there are five columns
    last_col = total_col

    ws.sheet_view.showGridLines = False
    ws.freeze_panes = 'A3'          # the two header rows stay visible while scrolling (house file)
    for letter in 'ABCDE':
        ws.column_dimensions[letter].width = WIDTHS[letter]
    # Effort widths follow the label, not the letter: adding a column shifts every
    # letter after it, and a fixed table then gives "Front-end Development" 10.5.
    for i, label in enumerate(labels):
        ws.column_dimensions[get_column_letter(first_eff + i)].width = (
            15.71 if len(label) > 12 else 12.57)
    ws.column_dimensions[get_column_letter(total_col)].width = 12.14

    for col, title in enumerate(T['heads'], start=1):
        ws.cell(1, col, title)
        for row in (1, 2):
            style(ws.cell(row, col), rgb=C_HEADER, bold=True, white=True)
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)

    ws.cell(1, first_eff, T['effort'])
    for col in range(first_eff, first_eff + n_eff):
        style(ws.cell(1, col), rgb=C_EFFORT, bold=True, white=True)
    ws.merge_cells(start_row=1, start_column=first_eff,
                   end_row=1, end_column=first_eff + n_eff - 1)
    for i, label in enumerate(labels):
        ws.cell(2, first_eff + i, label)
        style(ws.cell(2, first_eff + i), rgb=C_EFFORT, bold=True, white=True)

    ws.cell(1, total_col, T['total_effort'])
    for row in (1, 2):
        style(ws.cell(row, total_col), rgb=C_HEADER_TOT, bold=True, white=True)
    ws.merge_cells(start_row=1, start_column=total_col, end_row=2, end_column=total_col)

    eff_a, eff_z = get_column_letter(first_eff), get_column_letter(first_eff + n_eff - 1)
    r = 3
    spans, groups, group_open = [], [], None
    leaves = []

    def section(item, rgb):
        ws.cell(r, 1, item['id'])
        style(ws.cell(r, 1), rgb=rgb)
        ws.cell(r, 2, item['title'])
        style(ws.cell(r, 2), rgb=rgb, bold=True, align=A_LEFT_CENTER)
        style(ws.cell(r, 3), bd=B_TB)
        style(ws.cell(r, 4), bd=B_TB)
        style(ws.cell(r, 5), bd=B_RTB)
        for c in range(first_eff, last_col + 1):
            style(ws.cell(r, c), rgb=rgb)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)

    meta = None
    for item in spec['rows']:
        if int(str(item['id']).split('.')[0]) not in modules:
            continue
        kind = item['kind']
        if kind in ('L1', 'L2'):
            if group_open and group_open[1] > group_open[0]:
                groups.append(tuple(group_open))
            group_open = None
        if kind == 'L1':
            if meta:
                spans.append(meta + (r - 1,))
            meta = (item['id'], item['title'], r)
            section(item, C_L1)
            r += 1
        elif kind == 'L2':
            section(item, C_L2)
            r += 1
        else:
            leaves.append(item)
            ws.cell(r, 1, item['id'])
            style(ws.cell(r, 1), rgb=C_LEAF)
            if item.get('group'):
                if group_open and group_open[1] > group_open[0]:
                    groups.append(tuple(group_open))
                group_open = [r, r]
                ws.cell(r, 2, item['group'])
            elif group_open:
                group_open[1] = r
            style(ws.cell(r, 2), rgb=C_LEAF, align=A_LEFT_TOP)
            ws.cell(r, 3, item['feature'])
            style(ws.cell(r, 3), rgb=C_LEAF, align=A_LEFT_TOP)
            ws.cell(r, 4).value = bold_labels(item.get('desc', ''))   # house BA style: bold line labels
            style(ws.cell(r, 4), rgb=C_LEAF, align=A_LEFT_TOP)
            ws.cell(r, 5).value = bold_labels(column_e(item, lang_of(spec)))
            style(ws.cell(r, 5), rgb=C_LEAF, align=A_LEFT_TOP, bd=B_LTB)
            for i, c in enumerate(cols):
                v = item.get(c) or 0
                style(ws.cell(r, first_eff + i, v if v else None), rgb=C_LEAF)
            ws.cell(r, total_col, '=SUM(%s%d:%s%d)' % (eff_a, r, eff_z, r))
            style(ws.cell(r, total_col), rgb=C_LEAF)
            r += 1
    if group_open and group_open[1] > group_open[0]:
        groups.append(tuple(group_open))
    if meta:
        spans.append(meta + (r - 1,))
    for a, b in groups:
        ws.merge_cells(start_row=a, start_column=2, end_row=b, end_column=2)

    last = r - 1
    l1_rows = apply_rollup(ws, first_eff, n_eff, total_col, last)
    style(ws.cell(r, 1), rgb=C_TOTAL)
    ws.cell(r, 2, T['total'])
    style(ws.cell(r, 2), rgb=C_TOTAL, bold=True, align=A_LEFT_CENTER)
    style(ws.cell(r, 3), bd=B_TB)
    style(ws.cell(r, 4), bd=B_TB)
    style(ws.cell(r, 5), bd=B_RTB)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
    for c in range(first_eff, first_eff + n_eff):
        letter = get_column_letter(c)
        # Summing 3:last would now count every hour at task, group and module level.
        ws.cell(r, c, '=' + '+'.join('%s%d' % (letter, x) for x in l1_rows)
                if l1_rows else '=SUM(%s3:%s%d)' % (letter, letter, last))
        style(ws.cell(r, c), rgb=C_TOTAL, bold=True)
    ws.cell(r, total_col, '=SUM(%s%d:%s%d)' % (eff_a, r, eff_z, r))
    style(ws.cell(r, total_col), rgb=C_TOTAL, bold=True)

    autofit_row_heights(ws, WIDTHS, skip_rows={2})
    ws.row_dimensions[2].height = 36
    return {'name': ws.title, 'spans': spans, 'leaves': leaves, 'total_row': r,
            'total_col': get_column_letter(total_col), 'first_eff': first_eff}


def apply_rollup(ws, first_eff, n_eff, total_col, last):
    """Give every section row a total of its direct children; return the level-1 rows.

    Derived from the sheet that was just written rather than threaded through the writing
    loop, so it works the same for a module that has group rows and for one that carries its
    tasks a level higher.

    Naming each child cell is the whole point. A range would silently include the
    grandchildren as well, which is how the same hours come to be counted at three levels
    once section rows start carrying totals.
    """
    ids = []
    for r in range(3, last + 1):
        t = str(ws.cell(r, 1).value or '').strip()
        if t and t[0].isdigit():
            ids.append((r, t))

    def children_of(idx):
        row, ident = ids[idx]
        depth = ident.count('.')
        kids = []
        for nxt_row, nxt_id in ids[idx + 1:]:
            d = nxt_id.count('.')
            if d <= depth:
                break                      # a sibling or an uncle closes this section
            if d == depth + 1 and nxt_id.startswith(ident + '.'):
                kids.append(nxt_row)
        return kids

    l1_rows = []
    for i, (row, ident) in enumerate(ids):
        if '.' not in ident:
            l1_rows.append(row)
        kids = children_of(i)
        if not kids:
            continue                       # a leaf keeps the value it was given
        for c in range(first_eff, first_eff + n_eff):
            letter = get_column_letter(c)
            ws.cell(row, c, '=' + '+'.join('%s%d' % (letter, k) for k in kids))
            style(ws.cell(row, c), rgb=C_L1 if '.' not in ident else C_L2, bold=True)
        ws.cell(row, total_col,
                '=SUM(%s%d:%s%d)' % (get_column_letter(first_eff), row,
                                     get_column_letter(first_eff + n_eff - 1), row))
        style(ws.cell(row, total_col), rgb=C_L1 if '.' not in ident else C_L2, bold=True)
    return l1_rows


def column_e(item, lang='en'):
    """Assumptions, then the technical risk block when the task carries one.

    The risk lives beside the assumption it qualifies rather than on a separate sheet,
    because that is where the reader is when they ask "why is this number so big".
    """
    text = (item.get('assum') or '').rstrip()
    risk = item.get('risk')
    if risk:
        T = TEXT[lang]
        text += ('\n%s (%s):\n- %s\n- %s: %s'
                 % (T['risk'], T['levels'].get(risk['level'], risk['level']), risk['risk'],
                    T['mitigation'], risk['mitigation']))
    return text


# --------------------------------------------------------------- language
# The Cover, the Out of Scope sheet and the risk block follow the language the WBS is
# written in, and so does every label the builder writes: never a mix of the two.
TEXT = {
    'en': {
        'title': 'WORK BREAKDOWN STRUCTURE AND EFFORT ESTIMATE',
        'subtitle': 'Development effort only: development, developer unit testing and '
                    'code-review fixes. Whole hours.',
        'project': 'Project', 'unit': 'Unit', 'unit_default': 'man-hours', 'mode': 'Mode',
        'mode_fill': 'Structure supplied by the client; effort columns filled',
        'mode_author': 'Breakdown authored from the source documents',
        'zeros': 'Deliberate zeros', 'competitive': 'Competitive factor',
        'competitive_off': 'Not applied. The hours are the engineering position; any '
                           'discount is a commercial decision.',
        'sheet_module': 'Sheet / Module', 'total': 'TOTAL', 'notes_title': 'NOTES',
        'heads': ('ID', 'Module', 'Feature/Screen', 'Description',
                  'Assumptions, Constraints, Tech Solutions'),
        'effort': 'EFFORT (man-hour)', 'total_effort': 'Total Effort',
        'labels': DEFAULT_LABELS,
        'notes': (
            'Every estimate covers development, developer unit testing and code-review fixes. '
            'A dedicated QA function, project management and business analysis are not in '
            'these numbers; allow roughly 20-25% and 15-20% respectively on top.',
            'Assumptions that move the hours are recorded per task in column E, including the '
            'assumed COUNT of any external integration. Anything beyond that count is a change '
            'request at the same unit effort.',
            'Tasks carrying real technical risk have a "Technical risk" block in column E with '
            'the risk, its level and the mitigation already built into the approach.',
            'The Out of Scope sheet records what is deliberately excluded and why, so the '
            'boundary of this estimate is explicit rather than inferred.'),
        'oos_heads': ('No', 'Item', 'Reason for Deferral'), 'oos_module': 'Related Module',
        'risk': 'Technical risk', 'mitigation': 'Mitigation',
        'levels': {'High': 'High', 'Medium': 'Medium'},
    },
    'vi': {
        'title': 'CẤU TRÚC PHÂN RÃ CÔNG VIỆC VÀ ƯỚC LƯỢNG NỖ LỰC',
        'subtitle': 'Chỉ gồm nỗ lực phát triển: lập trình, unit test của lập trình viên và '
                    'sửa lỗi sau code review. Giờ nguyên.',
        'project': 'Dự án', 'unit': 'Đơn vị', 'unit_default': 'giờ công', 'mode': 'Cách lập',
        'mode_fill': 'Cấu trúc do khách hàng cung cấp; điền các cột nỗ lực',
        'mode_author': 'Phân rã từ tài liệu đầu vào',
        'zeros': 'Cố ý để 0', 'competitive': 'Hệ số cạnh tranh',
        'competitive_off': 'Không áp dụng. Số giờ là đánh giá kỹ thuật; giảm giá (nếu có) '
                           'là quyết định thương mại.',
        'sheet_module': 'Sheet / Hạng mục', 'total': 'TỔNG CỘNG', 'notes_title': 'GHI CHÚ',
        'heads': ('Mã', 'Module', 'Chức năng / Màn hình', 'Mô tả',
                  'Giả định, Ràng buộc, Giải pháp kỹ thuật'),
        'effort': 'NỖ LỰC (giờ công)', 'total_effort': 'Tổng nỗ lực',
        'labels': {'ui': 'Thiết kế UI/UX', 'devops': 'Devops', 'be': 'Phát triển Back-end',
                   'fe': 'Phát triển Front-end', 'mob': 'Mobile', 'ai': 'AI'},
        'notes': (
            'Mỗi ước lượng gồm lập trình, unit test của lập trình viên và sửa lỗi sau code '
            'review. Kiểm thử (QA) chuyên trách, quản lý dự án và phân tích nghiệp vụ không nằm '
            'trong các con số này; cộng thêm khoảng 20-25% và 15-20% tương ứng.',
            'Các giả định làm thay đổi số giờ được ghi theo từng task ở cột E, gồm cả SỐ LƯỢNG '
            'tích hợp bên ngoài đã giả định. Phần vượt quá số lượng đó là change request với '
            'cùng đơn giá nỗ lực.',
            'Task có rủi ro kỹ thuật thật có khối "Rủi ro kỹ thuật" ở cột E: rủi ro, mức độ và '
            'cách giảm thiểu đã tính sẵn trong giải pháp.',
            'Sheet Out of Scope ghi những gì cố ý không làm và lý do, để ranh giới của ước '
            'lượng này rõ ràng thay vì phải suy đoán.'),
        'oos_heads': ('STT', 'Hạng mục', 'Lý do chưa thực hiện'), 'oos_module': 'Module liên quan',
        'risk': 'Rủi ro kỹ thuật', 'mitigation': 'Giảm thiểu',
        'levels': {'High': 'Cao', 'Medium': 'Trung bình'},
    },
}
VI_CHARS = re.compile('[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]', re.I)


def effort_labels(spec, T):
    """Effort column labels in the WBS language. `column_labels` is honoured only for a
    client-supplied WBS (mode fill), where the client's own wording must be kept."""
    if spec.get('mode') == 'fill' and spec.get('column_labels'):
        return spec['column_labels']
    return [T['labels'].get(c, c.upper()) for c in spec['columns']]


def lang_of(spec):
    """'vi' or 'en': the spec's `lang`, else the language the task texts are written in."""
    if spec.get('lang') in TEXT:
        return spec['lang']
    text = ' '.join(str(r.get(k) or '') for r in wbs_schema.leaf_rows(spec)[:40]
                    for k in ('feature', 'desc'))
    return 'vi' if len(VI_CHARS.findall(text)) > len(text) * 0.02 else 'en'


# ------------------------------------------------------------------ Cover
def build_cover(ws, spec, sheets):
    # Sheet/Module + one column per effort discipline + Total, so the banners and the
    # notes cover the Total column whatever the column set is.
    span = len(spec['columns']) + 2
    ws.sheet_view.showGridLines = False
    ws.column_dimensions['A'].width = COVER_WIDTHS['A']
    for c in range(2, span + 1):
        ws.column_dimensions[get_column_letter(c)].width = 15

    T = TEXT[lang_of(spec)]
    banner(ws, 1, '%s  -  %s' % (spec['project'].upper(), T['title']), C_HEADER, span, 14)
    ws.row_dimensions[1].height = 26
    banner(ws, 2, T['subtitle'], C_EFFORT, span)

    r = 4
    info = [(T['project'], spec['project']),
            (T['unit'], T['unit_default'] if spec.get('currency_note') in
             (None, '', 'man-hours', 'giờ công') else spec['currency_note']),
            (T['mode'], T['mode_fill'] if spec.get('mode') == 'fill' else T['mode_author'])]
    if spec.get('zero_note'):
        info.append((T['zeros'], spec['zero_note']))
    if spec.get('competitive', 1.0) == 1.0:
        info.append((T['competitive'], T['competitive_off']))
    for label, value in info:
        ws.cell(r, 1, label)
        style(ws.cell(r, 1), rgb=C_L2, bold=True, align=A_LEFT_CENTER)
        ws.cell(r, 2, value)
        for c in range(2, span + 1):
            style(ws.cell(r, c), align=A_LEFT_CENTER)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=span)
        r += 1

    r += 1
    labels = effort_labels(spec, T)
    for c, h in enumerate([T['sheet_module']] + labels + [T['total_effort']], start=1):
        ws.cell(r, c, h)
        style(ws.cell(r, c), rgb=C_HEADER if c == 1 else (
            C_HEADER_TOT if c == len(labels) + 2 else C_EFFORT), bold=True, white=True)
    r += 1

    tot_rows = []
    for sh in sheets:
        q = "'%s'!" % sh['name']
        ws.cell(r, 1, sh['name'])
        style(ws.cell(r, 1), rgb=C_L1, bold=True, align=A_LEFT_CENTER)
        for i in range(len(labels) + 1):
            src = get_column_letter(sh['first_eff'] + i) if i < len(labels) else sh['total_col']
            ws.cell(r, 2 + i, '=%s%s%d' % (q, src, sh['total_row']))
            style(ws.cell(r, 2 + i), rgb=C_L1, bold=True)
        tot_rows.append(r)
        r += 1
        for sid, title, a, b in sh['spans']:
            ws.cell(r, 1, '      %s. %s' % (sid, title))
            style(ws.cell(r, 1), align=A_LEFT_CENTER)
            for i in range(len(labels) + 1):
                src = get_column_letter(sh['first_eff'] + i) if i < len(labels) else sh['total_col']
                # `a` is the module's level-1 row, which now carries its own roll-up.
                # Summing a:b would count the module's hours three times over.
                ws.cell(r, 2 + i, '=%s%s%d' % (q, src, a))
                style(ws.cell(r, 2 + i))
            r += 1

    ws.cell(r, 1, T['total'])
    style(ws.cell(r, 1), rgb=C_TOTAL, bold=True, align=A_LEFT_CENTER)
    for i in range(len(labels) + 1):
        letter = get_column_letter(2 + i)
        ws.cell(r, 2 + i, '=' + '+'.join('%s%d' % (letter, x) for x in tot_rows))
        style(ws.cell(r, 2 + i), rgb=C_TOTAL, bold=True)
    r += 2

    lines = list(T['notes'])
    if spec.get('zero_note'):
        lines.insert(1, spec['zero_note'])
    notes(ws, r, span, T['notes_title'], lines)
    autofit_row_heights(ws, {get_column_letter(c): ws.column_dimensions[get_column_letter(c)].width
                             for c in range(1, span + 1)}, skip_rows={1})


def build_oos(ws, spec):
    T = TEXT[lang_of(spec)]
    entries = spec.get('out_of_scope', [])
    widths = dict(OOS_WIDTHS)
    heads = list(T['oos_heads'])
    if any(e.get('module') for e in entries):
        heads.append(T['oos_module'])
        widths['D'] = 30.0
    for letter, width in widths.items():
        ws.column_dimensions[letter].width = width
    for c, h in enumerate(heads, start=1):
        ws.cell(1, c, h)
        style(ws.cell(1, c), rgb=C_OOS_HDR, bold=True)
    for i, entry in enumerate(entries, start=1):
        ws.cell(i + 1, 1, i)
        style(ws.cell(i + 1, 1))
        ws.cell(i + 1, 2, entry['item'])
        style(ws.cell(i + 1, 2), align=A_LEFT_CENTER)
        ws.cell(i + 1, 3, entry['reason'])
        style(ws.cell(i + 1, 3), align=A_LEFT_CENTER)
        if len(heads) == 4:
            ws.cell(i + 1, 4, entry.get('module') or '')
            style(ws.cell(i + 1, 4), align=A_LEFT_CENTER)
    autofit_row_heights(ws, widths)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    spec = wbs_schema.validate(json.load(open(a.spec, encoding='utf-8')))
    log = apply_factors(spec)
    print_factor_log(log, spec.get('competitive', 1.0))
    grand = sum(r.get(c) or 0 for r in wbs_schema.leaf_rows(spec)
                for c in spec['columns'])
    print_competitive_position(spec, grand)

    wb = Workbook()
    cover = wb.active
    cover.title = 'Cover'
    sheets = [build_sheet(wb.create_sheet(s['name'][:31]), spec, set(s['modules']))
              for s in spec['sheets']]
    build_cover(cover, spec, sheets)
    build_oos(wb.create_sheet('Out of Scope'), spec)
    wb.save(a.out)

    cols = spec['columns']
    leaves = wbs_schema.leaf_rows(spec)
    grand = sum(r.get(c) or 0 for r in leaves for c in cols)
    cells = sum(1 for r in leaves for c in cols if r.get(c))
    print('Written: %s' % a.out)
    print('Sheets : %s' % ', '.join(wb.sheetnames))
    print()
    print('%-34s %7s %9s' % ('Sheet', 'tasks', 'hours'))
    for sh in sheets:
        h = sum(r.get(c) or 0 for r in sh['leaves'] for c in cols)
        print('%-34s %7d %9d' % (sh['name'][:34], len(sh['leaves']), h))
    print('%-34s %7d %9d' % ('TOTAL', len(leaves), grand))
    print()
    if cells:
        print('Average per leaf task       : %.1f h' % (grand / len(leaves)))
        print('Average per populated cell  : %.1f h  (%d cells)' % (grand / cells, cells))
    for c in cols:
        s = sum(r.get(c) or 0 for r in leaves)
        print('  %-5s %7d  %5.1f%%' % (c, s, 100.0 * s / grand if grand else 0))


if __name__ == '__main__':
    main()
