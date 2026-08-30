# The workbook schema

Seven sheets over one dataset, joined on `ID`. The split is deliberate: a
thirty-column flat sheet is unreadable, and each audience needs a different slice.

| Sheet | Audience | Answers |
|---|---|---|
| `START HERE` | a first-time reader | what is this, what's the verdict, what are the worst problems? |
| `HOW TO READ` | a first-time reader | what does every column and every coded value mean? |
| `BUG-CLASSES` | tech lead / product | what is the *systemic* problem? |
| `DEFECTS` | developer / lead | what must be fixed, worst first? |
| `COVERAGE` | everyone | how much of this is actually tested? |
| `SPEC` | business / BA / client | what should every field do? |
| `RESULTS` | tester / next auditor | what did it actually do, and how well was that proven? |

Tab order **is** the reading order. `SPEC` deliberately mirrors the familiar
hand-written field-inventory format so a business reviewer can read it without
retraining.

## The self-explanation rule — non-negotiable

**A reader who knows nothing about this audit must need nothing but the workbook.**
The vocabulary in this skill (`money-moves`, `Rung 4`, `Negative: PASS`) is
private jargon; handing it over unexplained wastes the whole audit. `make_workbook.py`
therefore enforces four things, and a new sheet must not break them:

1. **`START HERE`** — what was audited, against which build, the verdict, the counts,
   the tab reading order, and the worst findings *in plain words*.
2. **`HOW TO READ`** — every coded value spelled out, with the two most-misread
   items called out explicitly: that `Negative: PASS` means bad input was correctly
   *rejected*, and that marker-vs-enforced are separate because they fail separately.
3. **Hover comments on every column header**, from the `HELP` dictionary.
4. **Self-describing cell text** for the columns that are easiest to misread —
   risk level, severity, rung, and the pass/fail columns are expanded in place
   (`6 money moves — real money can be paid wrong`). The numeric prefix preserves
   sort order while the words carry the meaning.

**`In plain words` is a required column on `DEFECTS`.** One jargon-free sentence
saying what happens and why it matters. The builder prints a warning naming any
defect that lacks one — treat that warning as a build failure, because a finding
nobody can understand will not get fixed.

*Origin: the first two workbooks were handed over without any of this. The reader's
verdict was "these are not self-explanatory" — entirely correct, and a reminder that
the audit's product is comprehension, not rows.*

---

## Sheet 1 · `SPEC` — what the field should do

| # | Column | Notes |
|---|---|---|
| 1 | `ID` | `<MODULE>-<SCREEN>-<SECTION>-<NNN>`. Stable forever. Retire, never renumber. |
| 2 | `Nav Group` | top-level sidebar group |
| 3 | `Module` | audit unit |
| 4 | `Screen` | route / page name |
| 5 | `Section` | the on-screen grouping (card / fieldset / tab) |
| 6 | `Field Label` | **exactly** as rendered, including case |
| 7 | `Control Type` | see allowed values below |
| 8 | `Purpose` | one plain sentence; what a business user would say it's for |
| 9 | `Mandatory` | `Yes` / `Conditional: <exact condition>` / `Optional` |
| 10 | `Validation / Business Rule` | stated **testably** — a regex, a range, an enum |
| 11 | `Oracle Source` | `code:<file>:<line>` / `statute:<§>` / `doc:<ref>` / `NONE` |
| 12 | `Statutory Ref` | Act + section where one governs it |
| 13 | `Impact if Incorrect` | plain-words consequence |
| 14 | `Downstream Surfaces` | concrete artifacts to open — `Invoice PDF; Regulatory Filing Annex I; External Registry Export` |
| 15 | `Blast Radius` | see allowed values below |
| 16 | `Remarks` | free text |

### `Control Type` allowed values
`text` · `textarea` · `number` · `currency` · `percent` · `date` · `date-range` ·
`single-select` · `multi-select` · `toggle` · `checkbox` · `radio` · `file` ·
`computed-readonly` · `lookup` (async search) · `rich-text`

Control type is not decoration — it selects which hostile inputs apply
(`negative-battery.md`).

### `Blast Radius` allowed values — ordered, and this is the risk sort key
| Value | Meaning |
|---|---|
| `cosmetic` | appearance only; no data, no money |
| `one-record` | wrong on one employee/record, visible and fixable in place |
| `one-run` | corrupts a single processing run or period |
| `all-employees` | wrong for everyone on the next run (an org-level default) |
| `statutory-external` | flows into a filing/return that leaves the company (a regulatory or compliance export) |
| `money-moves` | drives an actual payment — a payment file, account number, routing code, net amount |

**Never sort an audit by module.** Sort by blast radius. `money-moves` and
`statutory-external` rows are the audit; everything else is context.

---

## Sheet 2 · `RESULTS` — what actually happened

| # | Column | Notes |
|---|---|---|
| 1 | `ID` | joins to SPEC |
| 2 | `Field Label` | repeated for readability |
| 3 | `Route + Locator` | `/settings/company#organization` + `getByLabel('Legal Name')` — makes the row replayable |
| 4 | `Test Data Used` | the literal value typed. Reproducibility lives here. |
| 5 | `Expected` | from the oracle, not from your expectation |
| 6 | `Actual` | what the app did |
| 7 | `Positive` | `PASS` / `FAIL` / `BLOCKED` / `NOT-RUN` |
| 8 | `Negative` | `PASS` (correctly rejected) / `FAIL` (garbage accepted) / `NOT-RUN` |
| 9 | `Mandatory Marker` | `Y` / `N` / `NA` — is a visible required marker rendered? |
| 10 | `Mandatory Enforced` | `Y` / `N` / `NA` — does saving blank actually fail? |
| 11 | `Persistence` | `PASS` / `FAIL` / `NOT-RUN` — still correct after leaving and returning |
| 12 | `Downstream Verified` | `Y` / `N` / `NA` — was the named surface opened and checked |
| 13 | `Rung` | `1` UI-live · `2` DOM · `3` API · `4` DB · `5` code-only |
| 14 | `Evidence` | screenshot path / DB row / network capture ref |
| 15 | `Confidence` | `High` / `Med` / `Low` on the finding itself |

### Why columns 9 and 10 are separate
They fail independently and mean different things:

- marker `Y`, enforced `N` → the form **lies**. It promises a requirement it does
  not keep, so bad data reaches the database. `MANDATORY-NOT-ENFORCED`.
- marker `N`, enforced `Y` → the form **ambushes**. The user fills it in, saves,
  and only then learns what was required. `MANDATORY-MARKER-MISSING`.

Collapsing them into one "Mandatory: Yes" cell — as a hand-written sheet does —
hides both.

### Rung discipline
A row proven only by reading the validator is rung `5`. It is a legitimate
result; it is not a tested field. `COVERAGE` reports the rung-1 percentage
precisely so nobody can quietly bank code reads as live tests.

---

## Sheet 3 · `DEFECTS` — failures only, severity-sorted

| # | Column | Notes |
|---|---|---|
| 1 | `Defect ID` | the project's register ID (e.g. `F-xxx`), not a local number |
| 2 | `Severity` | `Blocker` / `Major` / `Minor` / `Cosmetic` (+ Nielsen 0–4 for usability items) |
| 3 | `Bug Class` | exactly one value from `bug-classes.md` |
| 4 | `Blast Radius` | inherited from the SPEC row |
| 5 | `Row ID` | the audit row it came from |
| 6 | `Module` / `Screen` / `Field` | where |
| 7 | `Steps to Reproduce` | numbered, replayable by someone who has never seen it |
| 8 | `Expected` | from the oracle, with its source |
| 9 | `Actual` | observed |
| 10 | `Evidence` | screenshot / DB row / network trace |
| 11 | `Status` | `Open` / `Fixed` / `Waived` / `Wont-Fix` / `Not-A-Bug` |
| 12 | `Owner` | who fixes it |
| 13 | `Date Found` | absolute date |
| 14 | `Fixed In` | commit SHA once closed |

### Severity is a function of blast radius, not of how odd it looks
| | `cosmetic` | `one-record` | `one-run` | `all-employees` | `statutory-external` | `money-moves` |
|---|---|---|---|---|---|---|
| silently wrong value | Cosmetic | Minor | Major | Major | **Blocker** | **Blocker** |
| rejected valid input | Minor | Major | Major | Major | Major | Major |
| accepted invalid input | Cosmetic | Minor | Major | **Blocker** | **Blocker** | **Blocker** |
| confusing but correct | Cosmetic | Cosmetic | Minor | Minor | Minor | Minor |

An accepted-invalid on a `money-moves` field is a Blocker even if it looks
trivial on screen. A wrong routing code does not look dramatic; it fails a
payment run.

---

## Sheet 4 · `BUG-CLASSES` — the rollup that makes the audit actionable

| # | Column | Notes |
|---|---|---|
| 1 | `Bug Class` | from the vocabulary |
| 2 | `Count` | instances |
| 3 | `Modules Affected` | list |
| 4 | `Screens Affected` | count + list |
| 5 | `Worst Severity` | max over instances |
| 6 | `Worst Blast Radius` | max over instances |
| 7 | `Likely Single Fix` | the one change that would close most of the class |
| 8 | `Fix Shape` | `shared-component` / `per-screen` / `backend-rule` / `spec-decision` |
| 9 | `Est. Effort` | `S` / `M` / `L` |

**Write this sheet before the report, and lead the report with it.** Three hundred
individual remarks is a document nobody acts on; the same findings as
*"required-marker missing on 91 fields, all rendering through one shared label
component, one `S` fix"* is a decision someone makes in a minute.

Record classes with **zero** findings too. "No `ID-LEAK` across 180 fields" is a
result worth keeping.

---

## Sheet 5 · `COVERAGE` — the honesty sheet

| # | Column | Notes |
|---|---|---|
| 1 | `Module` | |
| 2 | `Screens` | audited / total |
| 3 | `Fields Harvested` | from the DOM |
| 4 | `Fields In Prior Sheet` | if a hand-written sheet existed — the diff is the credibility win |
| 5 | `Fields Tested` | any rung |
| 6 | `Rung-1 %` | proportion actually clicked live |
| 7 | `Positive Pass %` | of those run |
| 8 | `Negative Run %` | **the number that exposes a checklist audit** — how many rules were actually violated on purpose |
| 9 | `Negative Pass %` | of those run |
| 10 | `Downstream Verified %` | of rows naming a surface |
| 11 | `Not Tested + Why` | one line per gap. Never blank. |
| 12 | `Verdict` | `CLEAN` / `FIX-BEFORE-DEMO` / `NOT-READY` |

Column 8 is the single most diagnostic number in the workbook. A traditional
field checklist scores near 0% there while showing all ticks — which is precisely
the failure mode this skill exists to remove.
