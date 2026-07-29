#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One command: both workbooks, both gates.

    python build_all.py --spec wbs.json --project "Acme Platform"
    python build_all.py --spec wbs.json --sizing sizing.json --project "Acme Platform"

Produces `WBS_<Project>.xlsx`, and `Cost Estimation - <Project>.xlsx` when a sizing file is
given, then runs the verifier for each and exits non-zero if anything failed. The cost run
re-fetches the vendor's list prices into a separate file first, so the gate compares the
estimate against the vendor rather than against itself.

Running the steps separately still works and is what to do while iterating on one of them.
This exists because a delivery is both workbooks passing both gates, and doing that in six
commands invites shipping the fifth.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(label, args, quiet=False):
    print()
    print('=' * 78)
    print(label)
    print('=' * 78)
    p = subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:],
                       capture_output=True, text=True)
    out = (p.stdout or '') + (p.stderr or '')
    if quiet and p.returncode == 0:
        tail = [ln for ln in out.splitlines() if ln.strip()][-3:]
        print('\n'.join(tail))
    else:
        print(out.rstrip())
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True, help='wbs.json')
    ap.add_argument('--sizing', help='sizing.json; omit when there is no cloud estimate')
    ap.add_argument('--project', required=True)
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--client', help="the client's own WBS workbook. Given this, or a "
                                     "spec whose mode is 'fill', the hours go into their "
                                     "structure and nothing else is touched")
    ap.add_argument('--provider', choices=['aws', 'azure'])
    ap.add_argument('--region')
    ap.add_argument('--skip-price-refetch', action='store_true',
                    help='use an existing prices_recheck.json instead of fetching. Only for '
                         'a rerun in the same session: the freshness gate exists because a '
                         'price carried forward under today date is invisible to a reader')
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    wbs_xlsx = os.path.join(a.out_dir, 'WBS_%s.xlsx' % a.project)
    cost_xlsx = os.path.join(a.out_dir, 'Cost Estimation - %s.xlsx' % a.project)
    recheck = os.path.join(a.out_dir, 'prices_recheck.json')

    failed = []

    # Two situations, told apart by the spec rather than by the operator remembering.
    # When the client supplied the breakdown, their workbook is the deliverable and the
    # only thing this writes is the effort columns.
    spec_mode = ''
    try:
        spec_mode = (json.load(open(a.spec, encoding='utf-8')).get('mode') or '').lower()
    except Exception:
        pass
    fill = bool(a.client) or spec_mode == 'fill'
    if fill and not a.client:
        print()
        print("The spec says mode 'fill', so --client must point at the workbook the "
              "client supplied.")
        return 2

    if fill:
        step = ['fill_wbs.py', '--spec', a.spec, '--client', a.client, '--out', wbs_xlsx]
        label = '1/4  FILL THE CLIENT WBS'
    else:
        step = ['build_wbs.py', '--spec', a.spec, '--out', wbs_xlsx]
        label = '1/4  BUILD WBS'
    if run(label, step):
        failed.append('fill_wbs' if fill else 'build_wbs')
        print('\nThe build refuses a spec it cannot render faithfully. Fix the spec; the '
              'message above says what is wrong.')
        return 1

    if a.sizing:
        if not (a.provider and a.region) and not a.skip_price_refetch:
            print('\n--provider and --region are required with --sizing, because the gate '
                  're-fetches the list prices to compare against.')
            return 2
        if not a.skip_price_refetch:
            if run('2/4  RE-FETCH LIST PRICES', ['cloud_prices.py', '--provider', a.provider,
                                                 '--region', a.region, '--out', recheck],
                   quiet=True):
                failed.append('cloud_prices')
        if run('2/4  BUILD COST', ['build_cost.py', '--sizing', a.sizing, '--out', cost_xlsx]):
            failed.append('build_cost')

    if run('3/4  VERIFY WBS', ['verify_wbs.py', '--spec', a.spec, '--xlsx', wbs_xlsx]):
        failed.append('verify_wbs')

    if a.sizing and os.path.exists(cost_xlsx):
        args = ['verify_cost.py', '--sizing', a.sizing, '--xlsx', cost_xlsx]
        if os.path.exists(recheck):
            args += ['--prices', recheck]
        if run('4/4  VERIFY COST', args):
            failed.append('verify_cost')

    print()
    print('=' * 78)
    if failed:
        print('NOT READY. Failed: %s' % ', '.join(failed))
        print('Nothing here is a suggestion. A gate that fails means the workbook would show '
              'a client something the estimate does not support.')
        return 1
    print('READY')
    print('  %s' % wbs_xlsx)
    if a.sizing and os.path.exists(cost_xlsx):
        print('  %s' % cost_xlsx)
    return 0


if __name__ == '__main__':
    sys.exit(main())
