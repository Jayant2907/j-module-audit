---
name: j-module-audit
description: >-
  Field-by-field conformance audit of a WHOLE module — the breadth sibling of
  j-QA. Where j-QA takes a git diff and goes deep on a few changed features,
  this walks every screen of one module and produces one row per user-visible
  field: what the field is for, whether it is mandatory, the testable rule that
  should govern it, which downstream surface breaks if it is wrong (an export,
  a generated document, a report, a dependent record), and then the PROVEN
  result of entering both a valid and a deliberately invalid value into it live.
  Harvests the field list
  mechanically from the DOM so nothing is missed by eye, derives every "expected"
  from code / statute / spec rather than from memory, runs a hostile-input
  battery no human would sit through, and classifies every finding into a
  controlled bug-class vocabulary so hundreds of rows collapse into a handful of
  systemic fixes. Ships an Excel workbook (SPEC / RESULTS / DEFECTS /
  BUG-CLASSES / COVERAGE), a plain-words report, and BACKLOG entries. Invoke
  when the user says "j-module-audit", "audit this module", "check every field",
  "make a QA sheet for module X", "field-level test matrix", "go through the
  whole module", or hands over a field-inventory spreadsheet to extend or verify.
  Sub-agents run on the Sonnet model.
---

# j-module-audit — every field in a module, proven

A module is not "verified" because someone opened its screens and ticked a
column. It is verified when **every field on every screen has a named owner of
truth, a testable rule, a proven positive result, a proven negative result, and
a named downstream surface that was actually opened and checked.**

This skill exists because a hand-written field inventory — even a very good one
— has two structural leaks:

1. **The tick is a claim, not evidence.** A sheet can say "PAN should be in the
   valid format" on 40 rows and be entirely silent on whether anybody ever typed
   `ABCD1234E` and watched the app swallow it. Every row that asserts a rule
   without a recorded rejection is an untested row wearing a tick.
2. **A hand-listed field list has holes, and the holes are invisible.** Fields
   are listed by eye, so conditional fields, fields below the fold, and fields
   behind a toggle get missed — and the sheet gives no signal that they are
   missing.

Both are mechanical problems with mechanical fixes: **harvest the field list
from the DOM**, and **make every rule produce a negative test**.

## Where it sits in the family

| Skill | Question | Scope |
|---|---|---|
| `j-QA` | Does this **change** work and tell the truth? | a git diff, deep |
| `j-user-readiness` | Can a stranger **understand** this screen? | a few screens, visual |
| **`j-module-audit`** | Is **every field** in this module correct, enforced, and connected? | one whole module, broad |

Reuse, don't restate: the verification ladder, the "rule out your own probe"
discipline, and the environment-specific gotchas all live in `j-QA` — read that
skill's *Execution model* and *Notes to adapt per codebase* sections before
driving a browser here. When a single field turns out to need deep sequence testing
(round-trip, superseding writes), hand that field to `j-QA` rather than
re-deriving its method.

---

## The three rules

**1. Every "expected" is attributable.** A row's rule must cite where it came
from: `code:<file>:<line>`, `statute:<act §section>`, or `doc:<ADR/spec>`. A
field with no oracle in any of the three is itself a finding
(`FIELD-UNDOCUMENTED`) — do not invent the rule and then test against your own
invention. Authority order is the project's: source code > ADR > SystemModels.

**2. Every rule produces a negative test.** "Mandatory" means *clear it and try
to save*. "Valid PAN format" means *type an invalid PAN and confirm rejection*.
"Day between 1–28" means *try 0 and 29*. A rule with no attempted violation is
recorded as `NOT-RUN`, never as PASS.

**3. Every "Impact if Incorrect" gets opened.** If a row claims the value flows
to a generated statement and a regulatory export, then go and look at that
statement and that export. An unverified impact claim is prose, and prose is
what let the bug through.

---

## Phase 0 — Scope the module and prepare the ground *(always)*

1. **Name the module and enumerate its screens.** One audit = one module a
   domain user would call one area ("Account Settings", "Customers", "Order
   Processing"). List every route, tab, sub-tab, drawer, modal and wizard step that
   belongs to it. Read the nav config; do not rely on the sidebar alone, since a
   registered route with no nav entry is itself a finding (`UNREACHABLE`).
2. **Confirm which build you are auditing, and say so.** An audit against a
   feature branch reports that branch's noise as product defects. Default to the
   project's trunk. Record branch + commit + backend host:port + frontend
   host:port in the report header. On a multi-lane machine, perform one write and
   read the network panel to confirm which backend actually answered — see
   `j-QA`'s Phase 3c·J.
3. **Seed realistic data.** An empty module hides its own problems: conditional
   fields never appear, tables never overflow, downstream surfaces have nothing
   to show. Use a tenant/account with real-shaped data — active records, a
   completed workflow cycle, dependent configuration enabled. Never audit a
   virgin/empty tenant.
4. **Set entry/exit criteria.** Entry: stack up, login works, data seeded. Exit:
   every field harvested is either tested or listed in COVERAGE with a reason.

## Phase 1 — Harvest the field list mechanically *(always)*

Do not list fields by eye. Drive the browser to each screen and run the harvest
script (`assets/harvest.js`) to dump every interactive control with its label,
control type, `required` state, options, placeholder, current value, and a stable
locator. Then:

- **Reveal what is hidden.** Re-harvest after: expanding every collapsed section,
  switching every tab, toggling every boolean both ways (a toggle usually reveals
  or hides dependent fields — harvest both states), and opening every modal.
  Diff the harvests; the delta *is* the conditional-field inventory.
- **Assign stable IDs.** `<MODULE>-<SCREEN>-<SECTION>-<NNN>`, e.g.
  `SETUP-COMPANY-ORG-012`. Stable across re-runs so a later audit can be diffed
  against this one. Never renumber on re-run; retire and append.
- **Diff against any existing sheet.** If the user supplied a spreadsheet, join
  on field label and report both directions: fields in the app that the sheet
  missed, and rows in the sheet whose field no longer exists. This is usually the
  fastest credibility win of the whole pass.
- **Capture free findings while you are there.** Console errors, failed network
  calls, and raw-UUID columns cost nothing extra to record.

## Phase 2 — Build the oracle *(always — parallel, code-only)*

Fan out **Sonnet** sub-agents, one per screen or per entity, **with no browser
access**. Each reads the DTOs, entities, validators, services, migrations and any
ADR/spec covering its screen, and returns for every harvested field:

- purpose in plain words,
- `Mandatory`: Yes / `Conditional: <the exact condition>` / Optional,
- the rule stated **testably** — `[A-Z]{5}[0-9]{4}[A-Z]{1}`, `1..28`,
  `> 0 and <= ceiling`, not "should be valid",
- `Oracle Source` for each of the above,
- `Statutory Ref` where an Act governs it,
- `Downstream Surfaces` — the concrete artifacts to open later,
- `Blast Radius` (see `references/columns.md`).

Two checks that pay for this phase on their own:

- **Frontend vs backend rule divergence.** Compare the client-side validation to
  the server DTO. Client-only enforcement is bypassable; server-only enforcement
  means the user hits a 400 with no inline hint. Both are findings.
- **Over-tight rules.** A rule can be wrong by being too strict. Read fixed
  lengths and hard-coded formats with suspicion — a bank account number is not 14
  digits for every bank, a name is not `[A-Za-z ]+` for every real person. These
  produce `VALIDATION-OVERTIGHT`, the class a checklist audit almost never
  catches because the happy path passes.

- **String literals compared against an enum's values.** Whenever a guard or a
  branch compares a status/type/mode field to a **quoted string**, check that the
  string is actually a member of the enum. A literal that no longer exists in the
  enum is dead in new data and alive in old — which breaks the check in *both*
  directions: it never fires where it should, and fires forever on any tenant
  still carrying the legacy value. Always diff `SELECT DISTINCT <column>` in live
  data against the enum definition; a value in the data with no enum member is an
  `ORPHAN-STATE` finding on its own.

- **Read the test's NAME as a statement of intent, then check what it mocks.**
  A unit test that mocks the very value the implementation looks for asserts the
  implementation, not the requirement — it is green whether or not the code is
  right, and its name is often the only surviving record of what was meant. When
  the name and the mock disagree, the name is usually the truth and the code is
  the bug.
  *Canonical:* a config-lock guard read `findOne({ where: { status: 'locked' } })`
  while the status enum was `DRAFT|PROCESSING|COMPLETE|PARTIAL_ERROR|FINALIZED|APPROVED`
  — `'locked'` was a legacy value the current code never writes. Its test was
  named *"should throw if a FINALIZED record exists"* and mocked
  `{ status: 'locked' }`. So: on tenants holding 37 legacy rows, the setting was
  permanently unchangeable with an error telling the user to "complete the
  record" that was already complete; on a fresh tenant the guard never fired at
  all. The test had been green throughout. **Two Blocker-grade directions, one
  string literal, and the test name was the clue.**

## Phase 3 — Execute, field by field *(always — serial, one browser driver)*

The browser is a single shared pane, so this phase is serial. One driver works
through the module screen by screen. For each screen, in this order:

**A · The mandatory sweep — one action, answers every row.** Clear every field
on the form, click Save. Record which fields raised an error and which did not.
Cross that against the oracle's Mandatory column and you have, in one step, the
`MANDATORY-NOT-ENFORCED` set for the entire screen. Separately, read the DOM for
the visible required marker (`*`, `aria-required`, "required" text) and record it
per field — **marker and enforcement are two different columns**, and either one
without the other is a distinct bug. *This single check is the highest-yield step
in the skill; run it before anything else on every form.*

**B · The negative battery.** For each field, apply the hostile inputs for its
control type from `references/negative-battery.md` — the invalid-format case, the
boundary either side of each limit, over-length, whitespace-only, and the
type-confusion case. Record what the app did and, critically, whether the error
message tells the user what to do. A rejection with an unhelpful message is
`VALIDATION-WRONG-MESSAGE`, not a pass.

**C · The positive path, then persistence.** Enter a realistic valid value, save,
and confirm the success signal actually means something. Then leave the screen
and come back: still there, still correct? A value that reverts silently is
`VALUE-REVERTS`; a toast over an unchanged database row is
`SILENT-SAVE-FAILURE`.

**D · Label the rung, per row.** `1 UI-live` > `2 DOM` > `3 API` > `4 DB` >
`5 code-only`. A field proven only by reading the validator is rung 5 and must
say so. Never let a code read wear a tested tick — that is the exact failure this
skill was built to remove.

**E · Rule out your own probe before filing.** Case-insensitive text matching,
selector precision, gated-panel preconditions, empty-because-correct — the full
list is in `j-QA`. A negative automated result gets confirmed a second way before
it reaches the defect log, and rows you are unsure about carry
`Confidence: Low`.

Efficiency note: batch by screen, not by field. Load the screen once, run the
mandatory sweep, then walk its fields. Do not re-navigate per field.

## Phase 4 — Verify downstream *(always, wherever a row names a surface)*

Parallel again, and mostly without the browser: **Sonnet** sub-agents confirm the
saved value in the database (right table, right column, `who/when` metadata,
soft-delete flag) and then open each named downstream surface and confirm the
value arrived — the generated statement, the register/report, the regulatory
export, the downstream file handoff.

A generated document gets the full treatment from `j-QA` Phase 3c·F: open the
file, check it can render the currency symbol, check for IDs where names belong,
internal URLs, and truncation. Exports escape the product, so they matter more
than a screen and are almost never opened.

Mark each row `Downstream Verified: Y / N / NA`. **An `N` on a row whose Blast
Radius is "statutory filing" or "money leaves the bank" is itself reportable** —
that is the definition of an unverified high-risk field.

**Expect this phase to disprove some of your own SPEC rows, and correct them out
loud.** The `Impact if Incorrect` column is written from the code that *binds* a
value; downstream asks whether anything ever *reads* it. Those differ more often
than feels reasonable. When a claim collapses, edit the row, drop its blast
radius, re-grade the defect that rested on it, and say in the report that the
audit corrected itself — that is the single most trust-building paragraph you can
write, and an audit that never revises a claim is not being checked.
*Canonical:* two fields carried "Impact: Invoice PDF" because the generator binds
them as template variables. The shipped default template interpolated only 2 of
the 8 bound company variables, so six — including the company's registration and
tax identifiers — reached no artifact at all. One field's blast radius fell from
`one-run` to `cosmetic` and its defect from Major to Minor; separately, "the
default invoice discloses none of the required company identifiers" became a
finding bigger than either.

**A trap specific to running Phase 4 in parallel with Phase 3.** The parallel
verifier reads the same database the serial browser driver is actively mutating.
It will observe a half-completed negative test — a deliberately corrupted value
mid-round-trip — and, having no way to know, may report the tenant as being
"actively mutated by something else". Either fence the two phases, or tell the
verifier which fields the driver is touching and that the live API is ground
truth. Never let that observation reach the report as an environment finding.
*Canonical:* a downstream agent flagged the tenant as unstable because it read
`registration_id='X'` seconds before the driver restored it — the "instability"
was the audit's own in-flight test.

## Phase 5 — Classify and roll up *(always — the phase that creates the value)*

Tag every finding with exactly one class from `references/bug-classes.md`, then
**aggregate by class before writing anything up.**

This is the step that turns an audit into a decision. Three hundred rows with a
remark each is a spreadsheet nobody acts on. The same findings grouped by class
read as: *"the required marker is missing on 91 fields across 14 screens — all of
them render through one shared `<FormLabel>`; one fix closes the class."* Report
the class first and the instances as its evidence.

For each class present, state: count, modules and screens affected, worst
severity, **the likely single fix**, and whether it is a shared-component fix, a
per-screen fix, or a spec gap needing a decision. Order the work list by
(systemic first) → (highest blast radius) → (cheapest fix).

Note when a class is *absent* too. "Zero `ID-LEAK` findings across 180 fields" is
a real result and stops someone re-litigating a solved problem.

## Phase 6 — Ship the artifacts *(always)*

1. **The workbook** — `tests/module-audits/<module>-<date>.xlsx`, five sheets per
   `references/columns.md`: `SPEC` (business-reviewable, mirrors the familiar
   hand-written format), `RESULTS` (the proof), `DEFECTS` (failures only,
   severity-sorted), `BUG-CLASSES` (the rollup), `COVERAGE` (the honesty sheet).
   Build it with `assets/make_workbook.py` from the row JSON so the format is
   identical across modules and re-runs are diffable.
2. **The plain-words report** — `tests/module-audits/<module>-<date>.md`: what was
   audited, against which build, the bug-class rollup as the headline, the
   must-fix list, and what was **not** covered and why.
3. **BACKLOG entries** — every Blocker and Major gets an entry in the project's
   defect register with its audit row ID, so the finding outlives the
   spreadsheet. A defect that exists only in a workbook cell will not be fixed.
4. **Verdict** — per module: **CLEAN / FIX-BEFORE-DEMO / NOT-READY**, with the
   must-fix list. Exit criterion for CLEAN: no open Blocker or Major, and no
   high-blast-radius row left `Downstream Verified: N`.

State coverage honestly. A module where 40 of 120 fields reached rung 1 is a
40-field audit with a 120-field inventory — say exactly that. Inflated coverage
is worse than thin coverage, because it stops the next pass from happening.

---

## Running many modules (the overnight loop)

Audits are queued, not parallel, because the browser is one pane. Keep the queue
in a git-tracked file (`tests/module-audits/QUEUE.md`) with one row per module:
`module | screens | est. fields | blast radius | status | last audited | verdict`.

- **Order by blast radius, never alphabetically.** The modules that compute
  money/critical values, and anything writing a regulatory or compliance
  record, come before Theme and Preferences. If the night ends early, it must
  end early on the low-risk end of the queue.
- **One module is one unit of work.** Finish its six phases and ship its
  artifacts before starting the next. A half-audited module is worth nothing and
  cannot be resumed by anyone else.
- **Update the queue file after every module** — status, verdict, defect count.
  This file is the resume point if the session dies; treat it the way the testing
  program treats its STATUS file.
- **Carry the bug-class ledger across modules.** Keep one cumulative
  `BUG-CLASSES.md`. The second and third module are where systemic classes prove
  themselves — a marker gap on one screen is a bug, the same gap on nine screens
  is an architecture finding, and only the cumulative ledger can tell you which
  you have.
- **Halt on a Blocker** if the standing halt-on-finding rule is active: file it
  and stop for a decision rather than auditing on around it.

### What parallelises, and what does not

| Work | Mode | Why |
|---|---|---|
| Oracle building (Phase 2) | **parallel** Sonnet, N agents | pure code reading, no shared resource |
| DB + downstream verification (Phase 4) | **parallel** Sonnet, N agents | API/DB only, no browser |
| Field harvest + execution (Phases 1, 3) | **serial**, one driver | one browser pane |
| Classification + write-up (Phases 5, 6) | orchestrator | needs the whole picture |

So a module's wall-clock is dominated by Phase 3. Two consequences: batch
browser work aggressively (one load per screen, not per field), and push anything
provable at rung 3–4 to the parallel phases instead of clicking it.

---

## What Playwright buys that a human tester cannot do

Say these out loud in the report — they are the argument for the whole approach.

1. **Complete field inventory instead of a hand-listed one.** The harvest finds
   the fields below the fold, behind the toggle, and inside the modal.
2. **A hostile-input battery per field.** Twelve invalid values across two
   hundred fields is twenty-four hundred negative tests. No human sits through
   that; it is the fastest path to the `VALIDATION-ABSENT` class.
3. **The whole-form mandatory sweep** — clear everything, save once, read the
   errors. Answers the mandatory column for a screen in one action.
4. **A replayable suite.** Stable row IDs plus stable locators means this audit
   re-runs next month and diffs against itself. The sheet stops being a one-off
   document and becomes a regression baseline.
5. **RBAC by re-harvest.** Log in as each role, harvest the same screens, diff
   the visible/editable field sets. Field-level permission drift, mechanically.
6. **Evidence for free** — screenshot, DOM snapshot, console log and network
   trace attached per row, with no extra effort.
7. **Cross-screen consistency checks a human cannot hold in their head** — the
   same logical field on four screens, compared for label, format, validation and
   masking. Divergence here is where duplicated logic surfaces.

## Reference files

- `references/columns.md` — the 5-sheet, ~30-column schema and every allowed value.
- `references/bug-classes.md` — the controlled bug-class vocabulary and severity mapping.
- `references/negative-battery.md` — hostile inputs per control type.
- `assets/harvest.js` — the DOM field-harvest script.
- `assets/make_workbook.py` — builds the workbook from row JSON.
