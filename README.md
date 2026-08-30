# j-module-audit

> **Agent Harness** — a field-level module audit harness for Cursor and Claude Code.

A **field-level audit harness** for whole-module conformance. Where `j-QA` goes deep on a git diff, this walks every screen of one module and proves every user-visible field.

Compatible with **Claude Code** and **Cursor** (both use a `SKILL.md` skill folder). Needs a **running app**, browser tools, and Python if you generate the Excel workbook.

## What this skill does

A module is verified when every field has a named owner of truth, a testable rule, a proven valid value, a proven invalid value, and a named downstream surface that was actually opened.

The skill:

1. **Harvests fields from the DOM** (`assets/harvest.js`) so conditional / below-the-fold fields are not missed by eye
2. Derives every expected rule from **code / statute / spec** (`code:file:line`, `statute:…`, or `doc:…`) — never from memory
3. Runs a **hostile-input battery** (valid + deliberately invalid) and records PASS only when the violation was actually attempted
4. Opens every claimed **downstream impact** (export, generated document, dependent record)
5. Classifies findings into a controlled **bug-class** vocabulary so hundreds of rows collapse into a few systemic fixes
6. Ships:
   - an **Excel workbook** (SPEC / RESULTS / DEFECTS / BUG-CLASSES / COVERAGE) via `assets/make_workbook.py`
   - a plain-words report
   - **backlog** entries

## When to use it

Invoke when you say `j-module-audit`, `audit this module`, `check every field`, `make a QA sheet for module X`, `field-level test matrix`, or you hand over a field-inventory spreadsheet to extend or verify.

## Install

### Cursor

**User-level:**

```bash
git clone https://github.com/Jayant2907/j-module-audit.git ~/.cursor/skills/j-module-audit
```

Windows (PowerShell):

```powershell
git clone https://github.com/Jayant2907/j-module-audit.git "$env:USERPROFILE\.cursor\skills\j-module-audit"
```

**Project-level:**

```bash
git clone https://github.com/Jayant2907/j-module-audit.git .cursor/skills/j-module-audit
```

### Claude Code

**User-level:**

```bash
git clone https://github.com/Jayant2907/j-module-audit.git ~/.claude/skills/j-module-audit
```

Windows (PowerShell):

```powershell
git clone https://github.com/Jayant2907/j-module-audit.git "$env:USERPROFILE\.claude\skills\j-module-audit"
```

**Project-level:**

```bash
git clone https://github.com/Jayant2907/j-module-audit.git .claude/skills/j-module-audit
```

Keep the whole folder: `SKILL.md`, `assets/`, and `references/` must stay together.

Restart the agent session so the skill is picked up.

### Workbook helper (optional)

`assets/make_workbook.py` needs Python 3 and typically `openpyxl`:

```bash
pip install openpyxl
```

Replace the example domain formats in `references/negative-battery.md` and `references/columns.md` with your project's ID / checksum / validation formats.

## How to run it

- `Run j-module-audit on the billing module`
- `Check every field on these screens and produce the QA workbook`

Reuse `j-QA` for verification-ladder and browser gotchas; hand a single field that needs deep sequence testing back to `j-QA`.

## What's in this repo

```
j-module-audit/
├── SKILL.md
├── README.md
├── assets/
│   ├── harvest.js         # DOM field harvest
│   └── make_workbook.py   # Excel SPEC/RESULTS/DEFECTS workbook
└── references/
    ├── bug-classes.md
    ├── columns.md
    └── negative-battery.md
```

## Agent Harness collection

Part of the **Agent Harness** suite by [@Jayant2907](https://github.com/Jayant2907) — installable skills that wrap structured agent workflows (review harnesses, QA harnesses, impact sweeps) for Cursor and Claude Code.

| Harness | Role |
|---|---|
| [adversarial-review](https://github.com/Jayant2907/adversarial-review) | Merge-review harness |
| [p-code-review](https://github.com/Jayant2907/p-code-review) | Whole-codebase review harness |
| [feature-impact-sweep](https://github.com/Jayant2907/feature-impact-sweep) | Cross-cutting impact harness |
| [j-QA](https://github.com/Jayant2907/j-QA) | Manual UI QA harness |
| [j-user-readiness](https://github.com/Jayant2907/j-user-readiness) | Visual demo-readiness harness |
| [j-module-audit](https://github.com/Jayant2907/j-module-audit) | Field-level module audit harness (this repo) |
