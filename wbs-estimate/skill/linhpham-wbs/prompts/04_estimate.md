# Phase 4 — Estimate

Write `wbs.json` against the contract in `scripts/wbs_schema.py`. The judgement goes in the
JSON; the rendering is Python's job. That way a re-run produces the same workbook, and a
challenged number is changed in one place.

## Every leaf task needs

- **`feature`** — what it is, in the client's vocabulary where they have one.
- **`desc`** — in the house style below (shape by task type). Enough that a developer could
  scope it, a tester could write cases from it, and a reviewer could challenge it.
- **`assum`** — the blocks below, in order (`Assumption:` first), stating what you assumed
  because the documents did not say. **Including the assumed COUNT of any external integration.** An unstated
  assumption is an unpriced risk.
- **hours per discipline**, whole numbers.
- **`refs`** — the requirement ids this task satisfies.
- **`risk`** — where the task carries real technical risk: the risk, its level, and the
  mitigation already built into the approach. A risk without a mitigation is a worry, not a
  plan.

## Writing style for Description and Assumptions (house BA style)

Every WBS uses this style. **One language per workbook, never mixed**: a Vietnamese WBS is
Vietnamese everywhere (sheet headers, effort column labels, Cover, Out of Scope, every text you
write), an English WBS is English everywhere. The builder writes its own labels in the language
of the task text (or `lang` in the spec); you write the task text, `zero_note` and Out of Scope
reasons in that same language. Technical terms stay in English inside Vietnamese text (see the
rules below). The shapes show the Vietnamese labels with the English label in brackets, and an
English WBS uses only the English labels:

| Tiếng Việt | English |
|---|---|
| Chức năng: | Function: |
| N. Mục đích: | N. Purpose: — one sentence, "Allows <who> to <do what> so that <value>." |
| N. Đối tượng sử dụng: | N. Users: |
| N. Thao tác trên hệ thống: | N. User actions: |
| N. Thành phần giao diện: | N. UI components: |
| N. Trường dữ liệu: | N. Data fields: |
| N. Điều kiện kích hoạt: | N. Trigger: |
| N. Xử lý của hệ thống: | N. System processing: |
| N. Phạm vi công việc: | N. Scope of work: |
| Ràng buộc hệ thống: | Business rules: |

### Module order

1. Infrastructure (cloud, environments, CI/CD, monitoring, security baseline) is always module 1.
2. Then the shared back-end or platform services.
3. Then one module per app or portal (web, admin portal, mobile app...).
4. **Non-Functional Requirements is always the last module, kept with all its rows at zero
   hours** (`zero_modules: ["<its number>"]`). The non-functional work is already inside the
   feature and infrastructure tasks; the module shows the client it was considered.

There is no kickoff/design module: design hours sit on the screen rows (below).

### Sheet format

- Effort columns, always this set in this order: UI/UX Design, Devops, Back-end Development,
  Front-end Development, Mobile, AI, then Total Effort (`["ui", "devops", "be", "fe", "mob",
  "ai"]`). A discipline the project does not need keeps its column with zeros. Only a
  client-supplied WBS keeps the client's own columns and labels.
- **No separate design tasks** (when the sheet has a UI/UX column). Every function row already has all the effort columns, so the
  design of a screen goes in the UI/UX Design column of that screen's own task, on the same row as
  its Front-end or Mobile hours (e.g. the Login task carries UI/UX + Back-end + Front-end hours).
  The designer reads the screen task to know what to design. Design-system and prototype effort
  goes on the app's framework task (web shell, app shell), not on a task of its own.
- **Whole hours only, everywhere.** No decimals in any effort cell. When hours are converted to
  another unit for a client sheet (man-days), the converted figures are whole numbers too: round
  the total once, then distribute so the cells add up to it, never round each cell up.
- **Every task row carries hours.** A task with no hours in any column is either missing an
  estimate or should not be in the WBS. The only exceptions are the Non-Functional module and a
  module or section zeroed on purpose at the gate, both declared in `zero_modules`.
- Infrastructure work (cloud, IaC, CI/CD, monitoring, backup, secrets) is booked in the Devops
  column, not Back-end.
- Column B (Module) carries the module name on every task row: set `group` on every leaf, no
  vertical merge.
- Inside the Description and Assumptions cells, the label at the start of a line is bold and the
  text after it is not ("Chức năng:", "1. Mục đích:", "Ràng buộc hệ thống:", "Assumption:",
  "Constraint:"). The build does this (`xlsx_style.bold_labels`); write plain text in the spec.

### Description (column D): pick the shape by task type

**Screen task** (anything a person operates in a web app, portal or mobile app):

```
Chức năng: <exactly the Feature text>                                  [Function]
1. Mục đích: Cho phép <ai> <làm gì> để <giá trị nhận được>.             [Purpose]
2. Đối tượng sử dụng: <vai trò>                                         [Users]
3. Thao tác trên hệ thống:                                              [Actions]
- <bước người dùng làm>
4. Thành phần giao diện:                                                [UI components]
- <thành phần>; trạng thái: đang tải, trống, lỗi
5. Trường dữ liệu:                                                      [Data fields]
- <trường> (bắt buộc / không bắt buộc, quy tắc)
6. Xử lý của hệ thống:                                                  [System processing]
- <hệ thống làm gì>, dẫn task thực hiện: (3.2.1)
Ràng buộc hệ thống:                                                     [Constraints]
a. <quy tắc nghiệp vụ hoặc trường hợp biên>
b. <...>
```

**Backend API or service task**: `Chức năng`, `1. Mục đích`, `2. Đối tượng sử dụng` (the app or
role that calls it), `3. Trường dữ liệu`, `4. Xử lý của hệ thống`, `Ràng buộc hệ thống`. An
endpoint list (REST/SOAP operations) goes under `Trường dữ liệu` as one bullet per operation.

**Job, event-driven or internal service task** (nothing calls it from a screen):
`2. Đối tượng sử dụng: Hệ thống (job nền)` or `Hệ thống (dịch vụ xử lý sự kiện)`, then
`3. Điều kiện kích hoạt:` [Trigger] instead of user actions, then `4. Xử lý của hệ thống`, then
`Ràng buộc hệ thống`.

**A task that is both a screen and a job** (a screen plus the background work behind it): use the
screen shape and put the trigger and the background work under `Xử lý của hệ thống`.

```
Chức năng: Job đối soát thanh toán hằng ngày
1. Mục đích: Cho phép hệ thống phát hiện giao dịch lệch giữa cổng thanh toán và đơn hàng để kế toán xử lý kịp.
2. Đối tượng sử dụng: Hệ thống (job nền)
3. Điều kiện kích hoạt:
- Chạy hằng ngày theo lịch cấu hình.
4. Xử lý của hệ thống:
- Tải file đối soát của cổng, so với giao dịch đã ghi nhận, đánh dấu giao dịch lệch.

Ràng buộc hệ thống:
a. Mỗi giao dịch lệch chỉ báo một lần cho tới khi được xử lý.
```

**Framework, infrastructure, testing, migration, project management and non-functional
tasks**: no frame. Short bullets, one concrete deliverable each, with the tool named when it
has been chosen (do not invent one the documents do not support):

```
- Bộ module Terraform dùng chung cho môi trường dev, staging, prod; state lưu ở storage có khóa.
- Mỗi môi trường một project riêng, gắn nhãn tài nguyên, cảnh báo ngân sách hằng tháng.
```

Use `2. Phạm vi công việc:` [Scope of work] only when a framework task sits inside a functional
module and needs a frame.

**Design** is never a task of its own: each screen task carries its UI/UX hours, and the screen
task's description (components, fields, states) is what the designer works from (see Sheet format).

Rules for every shape:
- Number the headings in order and skip any heading that does not apply; the next heading takes
  the number.
- `Mục đích` is always one sentence: "Cho phép <ai> <làm gì> để <giá trị>".
- `Xử lý` cites the task that does the work by id `(x.y.z)` instead of repeating its logic.
- `Ràng buộc hệ thống` [Business rules] holds the product's business rules and edge cases as
  `a.`, `b.`, `c.`, one rule per line. Limits on OUR scope go in the Assumptions `Constraint:`
  block instead; never write the same rule in both.
- Every heading is written only from facts in the documents. A data field says required or
  optional, and screen states (loading, empty, error), only where the documents say so or the
  assumption states the choice; never invent them to fill the frame.
- Keep a description short enough that the row stays under Excel's 409pt limit (about 25
  lines across the widest cell); the verifier reports any row the builder cannot fit.
- Prefer plain Vietnamese where a word exists ("dịch vụ", "biểu mẫu", "nhật ký ghi nhận hoạt
  động"), but keep product, protocol and cloud terms in English (Cloud Run, OAuth 2.0, service
  account, Import). Never machine-translate them.

### Assumptions (column E): up to five blocks, in this order, each only when it has content

```
Assumption:
- <điều khách cung cấp, quyết định, hoặc mặc định mình chọn>
Constraint:
- <giới hạn phạm vi hoặc thiết kế>
Tech solution:
- <công nghệ chọn>: <lý do một dòng>
Bổ sung so với SOW:                       [Added vs client SOW]
- <vì sao task này có dù SOW của khách không có>
Điều chỉnh so với SOW:                    [Changed vs client SOW]
- <khác SOW của khách ở đâu, vì sao>
```

The last two blocks exist only when the client supplied a SOW or WBS; a self-authored WBS
never has them.

- **Assumption** names who provides, decides or pays, and cites the client's Q&A answer when one
  exists ("(Q&A câu N)"). A parameter the client has not fixed: "do <khách> chốt; cấu hình được".
  Include the assumed COUNT of any external integration.
- **Constraint** draws the line around the hours ("Thay đổi sau khi SRS được duyệt xử lý qua
  change request.").
- **Tech solution** is one line: what was chosen instead of what, and why.
- **Bổ sung / Điều chỉnh so với SOW** is required on every task added to, or changed from, a
  client-supplied SOW, with the reason.
- Every task has at least one block, and the first block present comes first (a task with only
  a constraint starts with `Constraint:`). Leave out a block that has nothing in it; a filler
  assumption hides the real ones.
- An open item the client still has to decide goes in `Assumption:` as "do <khách> chốt"
  [to be confirmed by <client>], with the default this estimate used.
- When a column is zero for the whole project (for example UI/UX because the client supplies
  the design), say it once in `zero_note` on the Cover, not on every row.

### Self-check for Description and Assumptions (before the build)

- [ ] The `Chức năng:` line matches the Feature column exactly.
- [ ] The shape matches the task type (screen / API / job / infra-test-PM).
- [ ] There is no separate design task; every screen task with Front-end or Mobile hours also
      carries its UI/UX hours on the same row (zero only when the screen reuses an existing
      design, and the assumption says so).
- [ ] Every effort cell is a whole number, including any figure converted to man-days.
- [ ] Every task row has hours in at least one column, or is a deliberate zero whose assumption
      says why.
- [ ] `Mục đích` is one sentence in the form "Cho phép <ai> <làm gì> để <giá trị>".
- [ ] Headings are numbered in order with nothing skipped in the numbering; `a. b. c.` run in order.
- [ ] Every data field says required or optional and its rule.
- [ ] Every `(x.y.z)` points to a task that exists in this WBS and is the task the sentence means.
- [ ] Nothing describes a feature that is not a task in this WBS or that sits in Out of Scope.
- [ ] Nothing contradicts the chosen architecture or another task's description.
- [ ] The description does not promise more work than the task's hours.
- [ ] Assumption blocks are in the fixed order, each names who provides or decides, and empty
      blocks are left out.
- [ ] No doubled words, no machine-translated technical terms.

## Estimating

Classify each task against the ranges in `reference/estimation_rules.md` section 3, then
move within the range on evidence: number of entities and relations, whether the third
party has a sandbox, what compliance applies, whether it is real-time.

Check the module against `reference/lessons_learned.md`. If a comparable module came in at
230 hours and yours says 60, one of you is wrong.

**Flag technical risk while you estimate, not afterwards.** The moment you notice a task
depends on something outside the team's control, or has to be right about money, or makes
an automated decision with legal consequence, that is the risk entry. Written later it
becomes a formality.

Roughly a fifth to a quarter of tasks carrying a risk entry is normal for a complex bid.
Flagging everything is the same as flagging nothing.

## Then the factor layer, explicitly

Put the uplifts in `factors`, not in the task numbers, so the build prints base → final →
rule. Work through all of these; the recorded failure is applying only the downward one:

1. **Bundled integrations.** Search your own assumptions for "two", "three", "multiple".
   Every hit must be N × a unit price.
2. **No public sandbox** — ×1.3. Authority gateways, national identity, banks, acquirers.
3. **Legacy protocols** — ×1.3-1.5. SOAP, file transfer, anything undocumented until access
   is granted.
4. **Integration buffer** — +10-15% on every task that talks to something external.
5. **Requirements unclear** — ×1.15-1.5, **selectively**. Apply it where one line of
   requirement hides a whole multi-step journey, not across the board: a bottom-up estimate
   already accounts for the work each feature needs, so a blanket multiplier double-counts.
   If the engagement funds a discovery phase, use the low end and say so.
6. **AI-assisted factor** by task type, per section 4 of the rules. This one is already
   inside your base numbers if you estimated with it in mind; say which way you did it.
7. **Competitive factor**, or leave it at 1.0.

Every entry records `base`, `final`, the `rule` and a one-line `note`. The build fails if a
`base` no longer matches the row, so the audit trail cannot quietly become fiction.

## Deliberate zeros

If the gate agreed UI/UX or the non-functional module is absorbed, set `zero_columns` and
`zero_modules` and write the `zero_note` that will appear on the cover. Do not delete the
rows and do not edit hundreds of tasks by hand.

## Out of scope

Fill `out_of_scope` with everything deliberately excluded and the reason. Discovery, a
dedicated QA function, project management, licences, cloud consumption, a managed-service
period, deferred features, anything the client's contract covers rather than the build.

On a fixed-price bid this sheet is as important as the estimate. It is the boundary.

## Self-check before Phase 5

- Every leaf has an assumption
- Whole hours everywhere
- No task is all zeros unless it is deliberately zeroed
- Every requirement id appears in some task's `refs`
- Every "two" or "three" in an assumption has a matching factor entry
- Every NON-software deliverable the RFP or Q&A assigns to the vendor (an impact assessment,
  a processing inventory, a runbook, a data-protection input) has a task with hours. A row
  in the zeroed Non-Functional module does not count: it carries no hours. On a health bid,
  "the vendor prepares the cross-border transfer impact assessment" (Q&A) had only a zeroed
  NFR row and a passing mention until the thinnest-coverage table showed it at 10 hours
- The Description and Assumptions self-check above passes on every leaf
