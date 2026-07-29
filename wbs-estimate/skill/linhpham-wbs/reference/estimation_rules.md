# Estimation rules

The reference the estimate is built from. Read it at Phase 0 and apply it; do not
re-derive these numbers from intuition each time.

Everything here is vendor- and client-neutral on purpose, so the skill works for any
bid. Reference figures from past projects live in `lessons_learned.md`.

---

## 1. What a good estimate optimises for

```
Final = Base  ×  risk factors (up)  ×  AI-assisted factor (down)  ×  competitive factor
```

| Too high | Right | Too low |
|:-:|:-:|:-:|
| Lose the bid | Win it, and deliver it | Win it, and lose money |
| A cheaper vendor takes it | Price defensible, scope explicit | Overtime, quality drops, reputation goes |

Losing a bid costs one opportunity. Winning an underpriced one costs the margin on
every month of delivery, and usually the relationship. When the two errors are not
symmetric, do not treat them as if they are.

### Competitive factor

| Situation | Factor |
|---|---|
| Existing client, follow-on work | ×0.9 |
| New client, relationship worth building | ×0.85 - 0.9 |
| Many vendors bidding | ×0.85 - 0.9 |
| Sole bidder, referral or exclusive | ×0.95 - 1.0 |
| Complex, few vendors capable | ×0.95 - 1.0 |

**Default to ×1.0 and leave the discount to the commercial decision.** A discount buried
in engineering hours cannot be undone later, and it hides how much room there actually
is. On a fixed-price bid with unclear requirements, discounting the hours is how a team
wins and then loses money.

### Winning on something other than price

1. **Phase it.** A smaller, cheaper phase 1 with the rest scoped for later.
2. **Show the depth.** A detailed technical solution beats a bare number.
3. **Name the productivity.** AI-assisted delivery is a real 20-30% on the right tasks.
4. **Cut scope intelligently.** Propose dropping what earns least.
5. **Offer two options.** Full and optimised, so the client chooses.
6. **Compress the calendar.** Same effort, more parallelism, earlier delivery.

### Floors that do not move

| Work | Minimum | Why |
|---|---|---|
| Simple CRUD | 3h | Below that there is no testing |
| Auth flow | 6h | Security is not where you save |
| Third-party integration | 6h per endpoint | Retry, errors, rate limits |
| Infrastructure task | 4h | Wrong infra takes the project with it |
| Compliance feature | unchanged | Legal exposure beats a saved hour |

---

## 2. Rules

1. **Estimate leaf tasks only** (`x.x.x`), never a module row.
2. **Separate back-end, front-end, mobile and AI.** Different people, different rates.
3. **Each estimate = development + developer unit test + code-review fixes.** No separate
   unit-test line.
4. **No mobile hours when there is no mobile requirement.** Zero, not a token number.
5. **Buffer integration tasks 10-15%.** Third-party behaviour is not yours to control.
6. **Whole hours only.** Round half up. No 2.5, no 0.25, in any column, on any sheet.
7. **A row bundling N integrations costs N × one integration.** See `lessons_learned.md`;
   this is the most repeated and most expensive mistake in the log.

---

## 3. Effort reference by task type

### Which column a task lands in

The tables below give BE and FE because those two carry most work. A workbook usually has
more columns than that, and putting hours in the wrong one distorts every ratio afterwards.

| Task shape | Column(s) |
|---|---|
| Landing zone, network, cluster, pipeline, environments, observability | **Devops** (or BE when the workbook has no Devops column) |
| A shared engine several products call: identity, payments, ledger, notification, connector | **BE** only. The consuming screens are estimated separately |
| A screen in a mobile app | **Mobile**, plus light BE for any endpoint that exists only for it |
| A screen in a web portal or admin console | **FE** + **BE**. Each management screen needs list, detail, action and export APIs |
| Cross-platform mobile (Flutter, React Native) | **one Mobile column for both iOS and Android**, not two |
| Native mobile | one column per platform, and **Mobile ≈ 1.2-1.5× the FE web** for the same feature: camera and permissions, GPS, push in foreground and background, deep links, biometrics, secure storage, offline handling, store submission, real-device testing |
| Design system, component library, bilingual and right-to-left layout, accessibility | **UI/UX** if the workbook prices it, otherwise absorbed into FE and Mobile |

### The AI column is narrower than it looks

Put hours in **AI** only for work whose output is a model's: vision, OCR and document
extraction, embeddings and retrieval, ranking or matching learned from data, generation,
guardrails and evaluation sets.

Everything a reader might call "smart" but which is in fact **rule-based belongs in BE**:
dispatch and assignment, surge or dynamic pricing, ETA from historical averages, scoring
from a written rule set, a heatmap over aggregates. Calling one of these AI overstates the
AI column and understates BE, and it also promises the client a capability the build does
not contain.

**Read the out-of-scope list before allocating anything to AI.** When the engagement defers
the model work, the AI column is legitimately zero even on a product that talks about AI
throughout, and the in-scope rule-based version of each feature belongs in BE.


Hours are for one task, already assuming a competent team and normal complexity. Move
within the range on evidence from the documents, not on feel.

### Infrastructure and setup

| Task | BE | FE |
|---|---|---|
| Cloud environment setup (3-4 envs) | 5-8 | 0 |
| App hosting, auto-scale, SSL, domain | 4-6 | 0 |
| CI/CD pipeline | 6-8 | 0 |
| Database setup and migration strategy | 4-6 | 0 |
| Object storage configuration | 3-5 | 0 |
| Monitoring, logging, alerting | 4-6 | 0 |
| Security baseline: CORS, rate limit, headers | 4-6 | 0 |
| Secret and key management | 2-4 | 0 |
| Container platform / managed Kubernetes | 8-12 | 0 |
| Event backbone with schema registry | 8-12 | 0 |
| Infrastructure as code | 10-16 | 0 |
| Backup and disaster recovery | 8-14 | 0 |

### Identity and access

| Task | BE | FE |
|---|---|---|
| Login, email and password | 4-6 | 3-4 |
| Registration with email verification | 4-6 | 3-4 |
| Forgot and reset password | 3-4 | 2-3 |
| Social or federated login, per provider | 3-5 | 2-3 |
| Role-based access control | 4-6 | 2-3 |
| Attribute-based policy engine | 8-12 | 2-4 |
| Two-factor authentication | 6-8 | 4-5 |
| Session and device management | 2-3 | 1-2 |
| National or government digital identity | 14-20 | 3-5 |

### CRUD and screens

| Task | BE | FE |
|---|---|---|
| Simple CRUD, one entity, no relations | 3-4 | 3-4 |
| Medium CRUD, 2-3 relations, validation | 5-8 | 5-8 |
| Complex CRUD, nested, wizard, upload | 8-12 | 8-12 |
| List with search, filter, pagination | 3-4 | 3-5 |
| Detail or read-only view | 1-2 | 2-3 |
| Bulk actions | 2-3 | 2-3 |

### Files and documents

| Task | BE | FE |
|---|---|---|
| Single file upload | 2-3 | 2-3 |
| Multi-file upload with progress | 4-5 | 4-5 |
| OCR / document extraction | 8-12 | 3-5 |
| PDF generation | 4-6 | 0-2 |
| Spreadsheet import | 4-6 | 2-3 |
| Spreadsheet export | 2-4 | 1-2 |
| Document vault with retention and audit | 8-12 | 5-8 |

### Third-party integration

| Task | BE | FE |
|---|---|---|
| REST API, simple, 2-3 endpoints | 4-6 | 0-2 |
| REST API, full CRUD sync | 8-14 | 0-2 |
| Payment gateway | 10-16 | 4-6 |
| Email service | 3-4 | 0-1 |
| SMS or messaging API | 6-10 | 2-4 |
| OAuth2 to an external service | 4-6 | 1-2 |
| Webhook receiver | 3-5 | 0 |
| Legacy SOAP or file transfer | 8-12 | 0 |
| Government or authority gateway | 12-20 | 0-3 |

### Money

Under-estimated more often than anything else. A defect here is a financial defect.

| Task | BE |
|---|---|
| Payment abstraction across providers | 14-18 |
| Append-only double-entry ledger | 16-20 |
| Commission or revenue-share rule engine | 16-24 |
| Settlement cycle and batch processing | 12-18 |
| Payout calculation and disbursement | 12-18 |
| Reconciliation and statements | 14-18 |
| Dispute and adjustment handling | 10-14 |
| Wallet with balance, top-up, hold | 14-18 |
| Loyalty points ledger with tiers | 14-18 |

### Dashboards, notification, multi-tenancy

| Task | BE | FE |
|---|---|---|
| Dashboard, 3-5 widgets | 4-6 | 4-6 |
| Chart, each | 2-3 | 2-3 |
| Report with date range | 4-6 | 3-5 |
| In-app notification | 4-6 | 4-6 |
| Email notification | 3-4 | 0-1 |
| Push notification | 4-6 | 2-3 |
| Notification preferences | 3-4 | 3-4 |
| Multi-tenant, shared DB, row isolation | 4-6 | 0 |
| Multi-tenant, database per tenant | 8-12 | 0 |
| Tenant provisioning | 6-10 | 3-5 |
| Tenant administration screens | 5-8 | 5-8 |
| Tenant switching or support impersonation | 3-5 | 2-3 |

### Non-functional

| Task | BE | FE |
|---|---|---|
| Performance optimisation | 4-6 | 2-4 |
| SEO | 0-2 | 3-5 |
| Accessibility to WCAG AA | 0 | 4-8 |
| Internationalisation | 3-5 | 4-8 |
| Data-protection compliance | 4-8 | 2-4 |
| Load testing | 4-6 | 0 |
| Security audit | 4-8 | 2-4 |
| API documentation | 4-8 | 0 |
| UAT support | 8-16 | 4-8 |

---

## 4. Factors

### Upward, from the situation

| Condition | Factor |
|---|---|
| Team new to the stack | ×1.2 - 1.3 |
| Requirements unclear | ×1.2 - 1.5 |
| Third-party API with no sandbox | ×1.3 |
| High compliance regime | ×1.3 - 1.5 |
| Legacy integration | ×1.3 - 1.5 |
| Deadline under three months | ×1.1 - 1.2 |
| Team has domain experience | ×0.8 - 0.9 |

**Apply "requirements unclear" selectively, not across the board.** If the estimate was
built bottom-up from what each feature actually needs, a blanket multiplier double-counts.
Apply it where one line of requirement hides a whole multi-step journey. If the engagement
funds a discovery phase, use the low end and say why.

### Downward, from AI-assisted development

Not every task benefits equally. A blended figure hides that.

| Work | Factor |
|---|---|
| CRUD and boilerplate | ×0.5 - 0.6 |
| UI components and forms | ×0.6 - 0.7 |
| Unit tests | ×0.5 - 0.6 |
| Standard REST integration | ×0.7 - 0.8 |
| Schema and migrations | ×0.7 - 0.8 |
| Documentation | ×0.5 - 0.6 |
| Infrastructure as code | ×0.45 - 0.55 |
| CI/CD configuration | ×0.7 - 0.8 |
| Complex business logic | ×0.85 - 0.95 |
| Security and auth flows | ×0.85 - 0.95 |
| Integration with no sandbox | ×0.9 - 0.95 |
| Infrastructure and cloud operations | ×0.8 - 0.9 |
| Performance tuning | ×0.9 - 1.0 |
| Production debugging | ×0.9 - 1.0 |

Blended: heavy use ×0.7, moderate ×0.8, light ×0.85.

What the factor does **not** reduce: review time, UAT support, or the effort to test
generated code, which needs more scrutiny at the edges rather than less.

Two more limits on it. **The factor multiplies a base estimate; it does not replace
one.** Estimate the work first from section 3, then apply it, or the number has no
footing. And **a junior with these tools is not a senior**: the tools raise output on
work whose shape is already known, and they do not supply the architectural judgement
that decides what shape it should be, so the factor never justifies a thinner team.

### Both directions, or neither

An estimate that applies only the downward factor is not an optimistic estimate, it is a
wrong one. Record the upward factors in a table showing base, final and the rule, and
print it when the workbook builds. See `lessons_learned.md` for what happens otherwise.

---

## 5. Where estimates go wrong

### Usually too low

- Multi-tenant isolation, and the tests that prove it
- Error handling around third parties: retry, circuit breaker, fallback, dead letter
- Responsive HTML email templates
- File upload edge cases: size, type, virus scan, timeout, resume
- Search and filter: full text, combined filters, debounce, empty states
- Timezone handling across regions
- Data migration from an existing system
- Mobile: permissions, background behaviour, deep links, biometrics, secure storage,
  store submission, real-device testing. Native mobile is roughly 1.2-1.5× the web
  front-end for the same feature; a cross-platform framework brings it close to 1×.
- Camera and scanning flows: permission, modes, failure UX, torch. At least 6h on mobile.
- A basket spanning several vendors, with split settlement
- Payments where each merchant has its own connected account
- Anything whose row says "two" or "three" of something

### Usually too high

- Simple CRUD once the first screen sets the pattern
- Static pages
- Settings and configuration screens
- Soft delete

---

## 6. Process

**Before any number is written**, read every file in the folder, then present the analysis:
what kind of system this is, which front-end targets exist, what the client already
supplied, which modules look heavy or risky, what is unanswered, and which technical
recommendations move the hours. Confirm scope, factors and column layout at the gate.
Skipping this and going straight to numbers produces an estimate nobody can defend.

Then:

1. Map every feature to a leaf task
2. Classify each task against section 3
3. Estimate each discipline separately
4. Buffer the integration tasks
5. Apply the upward factors, explicitly
6. Apply the AI factor by task type
7. Apply the competitive factor, or leave it at 1.0
8. Run the sanity checks in section 7
9. Fix what they flag, or write down why the exception holds

---

## 7. Sanity checks

| Metric | Expected | Investigate |
|---|---|---|
| Average hours per leaf task | 4-7 | Under 3, or over 10 |
| Average per populated discipline cell | 4-7 | Same |
| Back-end share, 1-2 front-end targets | 55-65% | Front-end above back-end |
| Back-end share, 3+ front-end targets | 45-55% | |
| Infrastructure share | 8-12% | Over 15%, or under 5% |
| Non-functional share | 10-15% | Under 8%, unless deliberately zeroed |
| Native mobile vs web front-end | 1.2-1.5× | Mobile below web |
| Total, small system, 5-8 screens | 200-350h | |
| Total, medium, 10-20 screens | 400-700h | |
| Total, large, 20-40 screens | 700-1500h | |

**When a row of the workbook covers several disciplines, report both averages.** A leaf
carrying back-end, front-end, mobile and AI for one feature will show a high average per
row and a normal average per populated cell. Reporting only the first invites a correction
that is not needed; reporting only the second hides a genuinely oversized task.

A metric outside its range is a question, not a verdict. Answer it in the report: an
engine-heavy platform shared by several products legitimately runs a higher back-end
share, and a strong infrastructure-as-code factor legitimately pushes the infrastructure
share below the band.

---

## 8. Deliberate zeros

A client may want the UI/UX column and the non-functional module priced at zero, with the
work absorbed into the tasks that carry it. That is a presentation choice, not a claim the
work vanishes.

When zeroing:

- **Keep the rows.** An absent section reads as forgotten; a section priced at zero reads
  as considered.
- **Explain it on the cover.** Design sits with the front-end or mobile task that builds
  the screen; non-functional work sits inside each task because every estimate already
  covers development, unit testing and review.
- **Do it in one switch,** not by editing hundreds of tasks, so it can be reversed.
