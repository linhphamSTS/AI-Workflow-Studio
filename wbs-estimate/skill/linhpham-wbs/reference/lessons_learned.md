# Reference figures from delivered estimates

Real numbers from bids that were priced and submitted. Use them to sanity-check a new
estimate: if a module here came out at 230 hours and yours says 60 for the same shape of
work, one of you is wrong and it is worth finding out which before the bid goes out.

Client names are removed on purpose. What travels between projects is the shape of the
work and the hours it took, not who bought it.

---

## Delivered totals

| Shape of system | Front-end targets | Total | Notes |
|---|---|---|---|
| Invoice processing platform, OCR + accounting sync | 1 web | 475h | Cut from 562h; multi-tenant, OCR, 2-way sync |
| Food-court ordering platform | 2 web + 1 native mobile | 725h | Multi-vendor cart, POS integration, split payment |
| Interior design marketplace | 1 web + iOS + Android | ~1,590h | Mobile was ~40% of total |
| AI salon diagnostic SaaS | 1 web/tablet | 909h full / 613h MVP | Vision + OCR AI was 90h of it |
| Ride-hailing and food-delivery super app | 2 mobile + 2 web | 1,174h full / 831h MVP | Engine-heavy; AI column zero, all ML deferred |
| B2B airline booking portal | 2 web + 1 mobile | 1,974h | Aggregator integration, bank API, credit ledger |
| Three products on one shared platform | 3 mobile + 4 web | 4,108h | Shared platform was 40% of the total |

Reconcile a new total against the size bands in `estimation_rules.md` section 7 before
trusting it. All the above are development only: development, developer unit testing and
code-review fixes.

---

## Module reference figures

Hours for a module of that shape, already net of an AI-assisted factor.

### Platform and infrastructure

| Module | Hours | What was in it |
|---|---|---|
| Cloud infrastructure, 3-4 environments | 190-210 | Landing zone, network, Kubernetes, data stores, event bus, IaC, CI/CD, observability, DR |
| Shared platform services for several products | 1,400-1,500 | Identity, payments, notification, partner platform, connectors, CMS, analytics, AI platform, design system, compliance |
| Identity and access including national digital ID | 185-200 | OAuth2 server, federated national ID, signature, OTP, MFA, RBAC, ABAC, unified profile, admin console |
| Payments and wallet | 200-225 | Provider abstraction, acquiring, wallet, unified checkout, refunds, ledger, reconciliation, invoicing |
| Partner platform with settlement | 230-245 | Registry, onboarding, KYC, catalogue, commission engine, settlement, payout, reconciliation, disputes, partner API |
| AI platform | 265-275 | Model gateway, RAG, assistant, document AI, recommendation, matching, fraud, guardrails, evaluation |
| Design system across web and mobile | 160-165 | Tokens, two component libraries, RTL, i18n, accessibility |
| Admin / back-office for a many-role platform | 255-260 | Finance, reconciliation, payout approval, dispute, 11 roles |

### Single features that are consistently under-estimated

| Feature | Hours | Why it is bigger than it looks |
|---|---|---|
| OCR / document extraction, production grade | 12 BE + 16 AI | Confidence thresholds, human review queue, per-document schemas |
| Two-way sync with an external record system | 14 | Field mapping and conflict resolution, not just calls |
| Messaging rule engine | 8-10 | The rules are the work, not the send |
| Multi-vendor cart with split settlement | 8 BE + 6 mobile | One basket, several merchants, several settlements |
| Payments with per-merchant connected accounts | 10-12 BE | Not a standard gateway integration |
| Camera scanning on mobile, two modes | 6+ mobile | Permission flow, failure UX, torch, retake |
| Cross-partner loyalty redemption | 16-24 BE | Moves a balance-sheet liability between legal entities |
| Append-only double-entry ledger | 16-20 BE | The financial source of truth; defects are expensive |
| Government or authority gateway, per authority | 12-20 BE | Access, credentials and approval sit outside the vendor |
| National digital identity integration | 18-23 BE | No public sandbox; accreditation is on the client's timeline |
| A row that says "two payment gateways" | 8-10 each | See below |

---

## Mistakes that have recurred

### A row bundling N integrations priced as one

The most expensive and most repeated. A single WBS line reading "payment gateway
integration" covering five gateways was priced at 18 hours; the correct figure was about
8 hours per gateway, so 40. The same shape appeared later as "two free zone authorities"
at 16 hours total and "two partner banks" at 12.

**Before finalising, grep the assumptions for "two", "three", "multiple", "various".**
Every hit is a line that must be N times a unit price. Then state the assumed count in
the assumption so anything beyond it is a change request at the same unit rate.

### Applying only the downward factor

An estimate came out at 4,590 hours having applied the AI-assisted factor and none of the
upward ones: no integration buffer, no no-sandbox multiplier, no legacy multiplier, and no
correction for bundled-integration rows. Adding them moved it to 4,864.

The numbers looked plausible, so nothing else would have caught it. **Keep the upward
factors in an explicit table showing base, final and the rule, and print it when the
workbook builds.** An estimate whose reasoning is invisible cannot be reviewed.

### Mobile priced as if it were the web front-end

Native mobile ran 1.2-1.5× the web front-end for the same features once camera
permissions, background behaviour, deep links, biometrics, secure storage, store
submission and real-device testing were counted. One estimate had to move from 114 to 160
hours for exactly this. A cross-platform framework brings the ratio close to 1× and is
worth proposing when the client leaves the choice open.

### Coverage counted by tag instead of by requirement

A traceability script reported every requirement covered. Reading the actual requirement
text against the tasks then found five problems the count could not see, including a
**missing task**: the documents described the user journeys but never the account
structure those journeys hang off, so nothing created or managed the business entity.

**An RFP describes journeys, not the structures they attach to.** Ask, for every journey:
which entity, account or tenant owns this data, and who administers its users?

---

## Ratios that held, and why they were allowed to

| Project shape | Back-end vs client | Verdict |
|---|---|---|
| Engine-heavy super app, mobile-only clients | 63 / 37 | Accepted: dispatch, payment and real-time are shared |
| Three products on one shared platform | 60 / 40 | Accepted: the platform is engine-heavy by design |
| Portal with a public API tier | 66 / 34 | Accepted: the API tier is pure back-end |
| Standard web app, 1-2 front-end targets | 55-65 / 35-45 | The normal band |

A ratio outside the band is a question to answer in the report, not a number to fix by
inflating the other side. **Never pad the front end to make a ratio look right.**

Infrastructure below the 8-12% band is normal when the infrastructure-as-code factor is
applied strongly (×0.45-0.55) or when platform work sits in a shared-services module
rather than the infrastructure module. Say which, rather than leaving the reader to
wonder.

---

## Workbook craft

Learned by shipping files that were wrong in ways only the recipient noticed.

- **openpyxl writes no row height, and Excel Online and SharePoint never auto-fit.** Every
  wrapped cell renders as one line and the reader drags each row open. Measure the text and
  stamp a height on every row. Excel's own stored heights solve to `n * 15.0 + 0.75` for
  Calibri 11, so use `n * 15.0` plus real bottom padding.
- **Copying a reference workbook's format does not copy its row heights.** The reference
  works because Excel Desktop stamped them when a human last saved it.
- **Check every column header fits.** A column left at Excel's 8.43 default cut the tail off
  its own header, and the defect was inherited from the reference file, where nobody had
  noticed it either.
- **Deliberate zeros keep their rows and gain a cover note.** A section priced at zero reads
  as considered; an absent section reads as forgotten.
- **Roll-ups are formulas over the child rows, never hard-coded**, and section rows carry no
  value of their own so a total cannot double-count.
- **Report two averages when a row spans several disciplines**: per row, and per populated
  discipline cell. The first alone invites a correction that is not needed.

---

## How to add to this file

After every delivered estimate, append: the shape of the system and its front-end targets,
the total, the module figures worth reusing, which factors were applied, the actual ratios
and averages, and any mistake that had to be corrected before delivery. Keep client names
out. A figure with no context is not reusable, so say what was inside each module.
