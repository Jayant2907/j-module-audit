#!/usr/bin/env python3
"""
Build the audit workbook from row JSON.

    python make_workbook.py rows.json out.xlsx

Design rule: **a first-time reader must need nothing but this file.** Every sheet, column
and coded value explains itself, three ways over:
  1. a START HERE sheet — what was audited, the verdict, the headline findings in plain words
  2. a HOW TO READ sheet — every column and every allowed value, in plain English
  3. a hover comment on every column header, and self-describing text inside the cells that
     are easiest to misread (risk level, how-well-proven, and the pass/fail columns)

Input JSON:
{
  "module": "...",
  "build":  {"branch","commit","backend","frontend","tenant","date"},
  "rows":   [ {SPEC + RESULTS fields, flat — see references/columns.md} ],
  "defects":[ {... plus "In plain words": "one jargon-free sentence"} ],
  "coverage":[ {...} ]
}

Bug-class rollup is DERIVED from defects so it can never disagree with them.
"""
import json
import sys
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ─────────────────────────────────────────────── plain-English value dictionaries

# Risk level. The number keeps the sort order; the words explain it.
BLAST = {
    "cosmetic":           "1 cosmetic — looks wrong, no data or money affected",
    "one-record":         "2 one record — wrong for a single person, fixable in place",
    "one-run":            "3 one run — corrupts one processing run/period",
    "all-employees":      "4 all-employees — wrong for everyone on the next run",
    "statutory-external": "5 statutory — flows into a return that leaves the company",
    "money-moves":        "6 money moves — real money can be paid wrong",
}

SEVERITY = {
    "Blocker":  "Blocker — someone cannot do their job, or money/filing is at risk",
    "Major":    "Major — real damage is possible; fix before this ships",
    "Minor":    "Minor — worth fixing, but nothing breaks today",
    "Cosmetic": "Cosmetic — presentation only",
}

RUNG = {
    "1": "1 — clicked it in the browser myself (strongest)",
    "2": "2 — read it out of the live page",
    "3": "3 — called the API directly",
    "4": "4 — confirmed the row in the database",
    "5": "5 — read the source code only (weakest — not yet tested)",
}

POSNEG = {
    "PASS":    "PASS — behaved correctly",
    "FAIL":    "FAIL — behaved wrongly",
    "BLOCKED": "BLOCKED — something else stopped the test",
    "NOT-RUN": "NOT-RUN — not tested yet",
}
NEG = {
    "PASS":    "PASS — bad input was correctly REJECTED",
    "FAIL":    "FAIL — bad input was ACCEPTED and saved",
    "BLOCKED": "BLOCKED — could not attempt it",
    "NOT-RUN": "NOT-RUN — no bad input was tried yet",
}
YN = {"Y": "Y — yes", "N": "N — no", "NA": "NA — does not apply"}

FIXSHAPE = {
    "shared-component": "shared component — one change fixes every instance",
    "backend-rule":     "backend rule — a server-side validation or query change",
    "per-screen":       "per screen — a local fix on this screen",
    "spec-decision":    "DECISION NEEDED — nobody has decided the right answer yet",
}

STATUS_HELP = {
    "Open":       "Open — not fixed",
    "Fixed":      "Fixed — fixed and re-verified during this audit",
    "Not-A-Bug":  "Not-a-bug — checked and healthy; recorded so nobody re-checks it",
    "Waived":     "Waived — accepted as-is on purpose",
    "Wont-Fix":   "Won't fix",
}

# ─────────────────────────────────────────────── column help (hover comments)

HELP = {
    "ID": "Our stable reference for this field. It never changes, so a later audit can be "
          "compared against this one line by line.",
    "Nav Group": "Which top-level section of the sidebar this screen sits under.",
    "Module": "The area of the product being audited.",
    "Screen": "The page (and tab) the field lives on.",
    "Section": "The heading or card on that page that contains the field.",
    "Field Label": "The label exactly as it appears on screen, so you can go and find it.",
    "Control Type": "What kind of input it is (typing box, dropdown, on/off switch...). This "
                    "decides which bad values are worth trying.",
    "Purpose": "What the field is for, in one plain sentence.",
    "Mandatory": "Does the product require a value? 'Conditional' means only in the stated "
                 "situation.",
    "Validation / Business Rule": "The rule the value SHOULD obey, written so it can actually "
                                  "be tested (a pattern, a range, a list) rather than 'must be valid'.",
    "Oracle Source": "Where that rule came from — a line of source code, a law, or a spec. "
                     "'NONE' means no rule exists anywhere, which is itself a problem.",
    "Statutory Ref": "The Act or rule that governs this field, where one does.",
    "Impact if Incorrect": "What goes wrong if this value is wrong.",
    "Downstream Surfaces": "The documents and reports this value flows into — the places to go "
                           "and look to prove it actually arrived.",
    "Blast Radius": "How much damage a wrong value can do. This is the column to sort by: it "
                    "matters far more than which screen the field is on.",
    "Remarks": "Anything else a reader needs, including where this audit corrected itself.",
    "Route + Locator": "The address of the field, precise enough to re-test it automatically.",
    "Test Data Used": "The value actually typed in. Recorded so anyone can repeat the test.",
    "Expected": "What should have happened, taken from the rule — not from opinion.",
    "Actual": "What really happened.",
    "Positive": "Did a sensible, valid value work?",
    "Negative": "Did a deliberately WRONG value get refused? Careful: 'PASS' here means the "
                "app correctly rejected bad input. This is the single most valuable column — a "
                "tick-box review scores almost nothing here.",
    "Mandatory Marker": "Is there a visible mark (usually *) telling the user the field is "
                        "required?",
    "Mandatory Enforced": "Does saving actually fail when it is left blank? Marker and "
                          "enforcement are separate on purpose: a marker with no enforcement "
                          "means the form LIES; enforcement with no marker means it AMBUSHES you.",
    "Persistence": "Leave the screen, come back — is the value still right?",
    "Downstream Verified": "Did we actually OPEN the generated document / export / report and confirm the "
                           "value arrived? 'N' on a high-risk row means the claim is unproven.",
    "Rung": "How strongly this is proven, 1 (best) to 5 (weakest). A 5 means we only read the "
            "code and have not tested it — treat those as suspicions, not facts.",
    "Evidence": "What backs the result up — a screenshot, a database row, a network response.",
    "Confidence": "How sure we are of this particular finding.",
    "Defect ID": "Our reference for this problem. Quote it when discussing or fixing.",
    "Severity": "How bad it is, and therefore how urgently it needs attention.",
    "Bug Class": "The FAMILY of problem. Grouping by this is the point: twenty findings in one "
                 "family usually share a single fix.",
    "Row ID": "The audited field this problem came from (see the SPEC sheet).",
    "Field": "The field or control that is broken.",
    "Steps to Reproduce": "Numbered steps to see it yourself. Follow these before judging it.",
    "In plain words": "The whole problem in one jargon-free sentence — what happens, and why it "
                      "matters. Read this column first.",
    "Status": "Whether it is still outstanding.",
    "Owner": "Who is fixing it. Blank = unassigned.",
    "Date Found": "When we found it.",
    "Fixed In": "The commit that fixed it, where one exists.",
    "Likely Single Fix": "Our suggested fix, and how big it is.",
    "Fix Shape": "What KIND of change is needed — and whether it is even a developer's job. "
                 "'DECISION NEEDED' means somebody has to decide the right behaviour first.",
    "Est. Effort": "Rough size: S small, M medium, L large.",
    "Count": "How many separate findings are in this family.",
    "Modules Affected": "Which areas of the product show this family of problem.",
    "Screens Affected": "How many screens, and which ones.",
    "Worst Severity": "The most serious finding in this family.",
    "Worst Blast Radius": "The most damage this family can do.",
    "Screens": "How many screens were audited, out of how many exist.",
    "Fields Harvested": "How many input controls we found on the screens, read out of the live "
                        "page rather than listed by eye.",
    "Fields In Prior Sheet": "How many the earlier hand-written checklist listed, for comparison.",
    "Fields Tested": "How many we actually exercised.",
    "Rung-1 %": "What share was proven by genuinely clicking it in the browser.",
    "Positive Pass %": "Of the fields tested, how many behaved correctly with a good value.",
    "Negative Run %": "How many fields we deliberately fed BAD input. This is the most "
                      "diagnostic number in the workbook — a tick-box checklist scores near "
                      "zero here while still showing all ticks.",
    "Negative Pass %": "Of the bad values we tried, how many were correctly refused.",
    "Downstream Verified %": "Of the rows that claim a value reaches a document, how many we "
                             "actually opened and checked.",
    "Not Tested + Why": "Everything we did NOT do, and the reason. Deliberately blunt — "
                        "overstated coverage is worse than thin coverage.",
    "Verdict": "Our overall call on this module.",
}

# ─────────────────────────────────────────────── sheet definitions

SPEC_COLS = [("ID", 22), ("Nav Group", 12), ("Module", 16), ("Screen", 20), ("Section", 20),
             ("Field Label", 28), ("Control Type", 14), ("Purpose", 44), ("Mandatory", 22),
             ("Validation / Business Rule", 44), ("Oracle Source", 28), ("Statutory Ref", 16),
             ("Impact if Incorrect", 44), ("Downstream Surfaces", 28), ("Blast Radius", 34),
             ("Remarks", 40)]

RESULT_COLS = [("ID", 22), ("Field Label", 28), ("Route + Locator", 34), ("Test Data Used", 24),
               ("Expected", 34), ("Actual", 44), ("Positive", 26), ("Negative", 34),
               ("Mandatory Marker", 14), ("Mandatory Enforced", 16), ("Persistence", 24),
               ("Downstream Verified", 16), ("Rung", 34), ("Evidence", 28), ("Confidence", 11)]

DEFECT_COLS = [("Defect ID", 12), ("Severity", 42), ("In plain words", 62), ("Bug Class", 26),
               ("Blast Radius", 34), ("Row ID", 20), ("Module", 16), ("Screen", 22),
               ("Field", 26), ("Steps to Reproduce", 50), ("Expected", 34), ("Actual", 54),
               ("Evidence", 26), ("Status", 26), ("Owner", 12), ("Date Found", 12),
               ("Fixed In", 12), ("Likely Single Fix", 50), ("Fix Shape", 34), ("Est. Effort", 10)]

CLASS_COLS = [("Bug Class", 26), ("Count", 7), ("In plain words", 58), ("Modules Affected", 22),
              ("Screens Affected", 30), ("Worst Severity", 42), ("Worst Blast Radius", 34),
              ("Likely Single Fix", 48), ("Fix Shape", 34), ("Est. Effort", 10)]

COVER_COLS = [("Module", 18), ("Screens", 26), ("Fields Harvested", 15),
              ("Fields In Prior Sheet", 17), ("Fields Tested", 13), ("Rung-1 %", 10),
              ("Positive Pass %", 13), ("Negative Run %", 13), ("Negative Pass %", 13),
              ("Downstream Verified %", 17), ("Not Tested + Why", 70), ("Verdict", 20)]

SEV_ORDER = ["Cosmetic", "Minor", "Major", "Blocker"]
BLAST_ORDER = ["cosmetic", "one-record", "one-run", "all-employees",
               "statutory-external", "money-moves"]

# plain-English description of each bug family
CLASS_HELP = {
    "MANDATORY-MARKER-MISSING": "A required field gives the user no visible sign that it is required.",
    "MANDATORY-NOT-ENFORCED": "The form says a field is required but saving it blank works anyway.",
    "MANDATORY-WRONG": "A field is marked required when the business says it is optional, or the reverse.",
    "VALIDATION-ABSENT": "There is a rule on paper, but the app accepts anything and saves it.",
    "VALIDATION-OVERTIGHT": "The app refuses values that are perfectly legitimate in real life.",
    "VALIDATION-CLIENT-ONLY": "The rule is enforced only in the browser, so anything bypassing the screen gets through.",
    "VALIDATION-SERVER-ONLY": "The server refuses it but the screen gives no hint why.",
    "VALIDATION-WRONG-MESSAGE": "It is correctly refused, but the message does not tell the user what to do.",
    "CONDITION-UNDEFINED": "The field is 'sometimes required' and nobody can say when.",
    "FIELD-UNDOCUMENTED": "The field exists on screen with no rule defined anywhere at all.",
    "SILENT-SAVE-FAILURE": "It looks like it saved. It did not.",
    "VALUE-REVERTS": "The value quietly disappears when you come back to the screen.",
    "DEFAULT-WRONG": "The value it starts with is the wrong one.",
    "DEFAULT-MISSING": "It starts blank when it should start with a sensible value.",
    "DOWNSTREAM-DRIFT": "Saved correctly, but the document or report shows something different.",
    "DOWNSTREAM-ABSENT": "The value never reaches the document it is supposed to appear on.",
    "AUDIT-MISSING": "The change was made with no record of who did it or when.",
    "STALE-DENORM": "Two copies of the same fact disagree, and the wrong one is being used.",
    "ID-LEAK": "An internal database code is shown to the user instead of a name.",
    "JARGON-LABEL": "Internal developer wording is showing on screen.",
    "FORMAT-INCONSISTENT": "Money, dates or numbers are formatted differently in different places.",
    "UNIT-UNSTATED": "A number with no indication of whether it is rupees, a percentage or days.",
    "MASKING-GAP": "Personal data shown in full where it is supposed to be hidden.",
    "HELP-ABSENT": "Something important is unexplained, unlabelled, or invisible to a screen reader.",
    "EMPTY-STATE-MUTE": "An empty screen says 'no data' instead of what to do next.",
    "UNREACHABLE": "The page exists but no menu leads to it.",
    "PLACEMENT-WRONG": "The control is in a place the user would not think to look, or cannot reach.",
    "DEAD-CONTROL": "The control looks real and does nothing.",
    "RBAC-GAP": "Someone can see or change something their role should not allow.",
    "RBAC-OVERBLOCK": "Someone who needs access cannot get it.",
    "ORPHAN-STATE": "The system can end up in a state that no screen shows or can escape.",
    "CONSOLE-ERROR": "The page reports an error, or a request fails, on load.",
    "ENDPOINT-500": "A core operation returns a server error and cannot be completed.",
}

# ─────────────────────────────────────────────── styling

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(color="FFFFFF", bold=True, size=10)
BAD_FILL = PatternFill("solid", fgColor="F8CBAD")
WARN_FILL = PatternFill("solid", fgColor="FFE699")
GOOD_FILL = PatternFill("solid", fgColor="C6E0B4")
BLOCK_FILL = PatternFill("solid", fgColor="FF6B6B")
INFO_FILL = PatternFill("solid", fgColor="DDEBF7")
TITLE_FONT = Font(bold=True, size=14, color="1F3864")
H2_FONT = Font(bold=True, size=11, color="1F3864")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def decorate(col, val):
    """Expand a coded value into something a first-time reader understands."""
    s = str(val).strip()
    if col == "Blast Radius":
        return BLAST.get(s, val)
    if col in ("Severity", "Worst Severity"):
        return SEVERITY.get(s, val)
    if col == "Worst Blast Radius":
        return BLAST.get(s, val)
    if col == "Rung":
        return RUNG.get(s, val)
    if col in ("Positive", "Persistence"):
        return POSNEG.get(s, val)
    if col == "Negative":
        return NEG.get(s, val)
    if col == "Status":
        return STATUS_HELP.get(s, val)
    if col == "Fix Shape":
        return FIXSHAPE.get(s, val)
    return val


def tint(col, raw):
    s = str(raw).strip()
    if col == "Severity" and s == "Blocker":
        return BLOCK_FILL
    if s in ("FAIL", "NOT-READY"):
        return BAD_FILL
    if s in ("NOT-RUN", "BLOCKED", "Low", "FIX-BEFORE-DEMO"):
        return WARN_FILL
    if s in ("PASS", "CLEAN", "Fixed", "Not-A-Bug"):
        return GOOD_FILL
    if col == "Downstream Verified" and s == "N":
        return WARN_FILL
    if col == "Blast Radius" and s in ("money-moves", "statutory-external"):
        return WARN_FILL
    return None


def write_sheet(wb, title, cols, rows, freeze="A2"):
    ws = wb.create_sheet(title)
    for i, (name, width) in enumerate(cols, start=1):
        c = ws.cell(row=1, column=i, value=name)
        c.fill, c.font = HDR_FILL, HDR_FONT
        c.alignment = Alignment(vertical="center", wrap_text=True)
        if name in HELP:
            c.comment = Comment(HELP[name], "audit")
            c.comment.width, c.comment.height = 330, 150
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[1].height = 34

    for r, row in enumerate(rows, start=2):
        for i, (name, _) in enumerate(cols, start=1):
            raw = row.get(name, "")
            if isinstance(raw, (list, tuple)):
                raw = "; ".join(str(x) for x in raw)
            c = ws.cell(row=r, column=i, value=decorate(name, raw))
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = BORDER
            f = tint(name, raw)
            if f:
                c.fill = f
            if name == "Severity" and str(raw).strip() == "Blocker":
                c.font = Font(bold=True, size=10)
            if name == "In plain words":
                c.font = Font(size=10, bold=True)
    ws.freeze_panes = freeze
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
    return ws


def pct(n, d):
    return "n/a" if not d else f"{round(100 * n / d)}%"


def derive_classes(defects):
    by = defaultdict(list)
    for x in defects:
        by[x.get("Bug Class", "UNCLASSIFIED")].append(x)
    out = []
    for cls, items in sorted(by.items(), key=lambda kv: -len(kv[1])):
        sevs = [i.get("Severity", "Cosmetic") for i in items]
        blasts = [i.get("Blast Radius", "cosmetic") for i in items]
        screens = sorted({i.get("Screen", "") for i in items if i.get("Screen")})
        out.append({
            "Bug Class": cls, "Count": len(items),
            "In plain words": CLASS_HELP.get(cls, ""),
            "Modules Affected": sorted({i.get("Module", "") for i in items}),
            "Screens Affected": f"{len(screens)}: " + "; ".join(screens),
            "Worst Severity": max(sevs, key=lambda s: SEV_ORDER.index(s) if s in SEV_ORDER else -1),
            "Worst Blast Radius": max(blasts, key=lambda b: BLAST_ORDER.index(b)
                                      if b in BLAST_ORDER else -1),
            "Likely Single Fix": items[0].get("Likely Single Fix", ""),
            "Fix Shape": items[0].get("Fix Shape", ""),
            "Est. Effort": items[0].get("Est. Effort", ""),
        })
    return out


def derive_coverage(module, rows, prior=""):
    tested = [r for r in rows if r.get("Positive") not in (None, "", "NOT-RUN")]
    rung1 = [r for r in rows if str(r.get("Rung", "")) == "1"]
    pos = Counter(r.get("Positive") for r in rows)
    neg_run = [r for r in rows if r.get("Negative") not in (None, "", "NOT-RUN")]
    neg_ok = [r for r in neg_run if r.get("Negative") == "PASS"]
    ds = [r for r in rows if r.get("Downstream Surfaces")]
    ds_ok = [r for r in ds if r.get("Downstream Verified") == "Y"]
    screens = sorted({r.get("Screen", "") for r in rows if r.get("Screen")})
    return [{"Module": module, "Screens": len(screens), "Fields Harvested": len(rows),
             "Fields In Prior Sheet": prior, "Fields Tested": len(tested),
             "Rung-1 %": pct(len(rung1), len(rows)),
             "Positive Pass %": pct(pos.get("PASS", 0), len(tested)),
             "Negative Run %": pct(len(neg_run), len(rows)),
             "Negative Pass %": pct(len(neg_ok), len(neg_run)),
             "Downstream Verified %": pct(len(ds_ok), len(ds)),
             "Not Tested + Why": "", "Verdict": ""}]


# ─────────────────────────────────────────────── narrative sheets

def sheet_start_here(wb, module, build, defects, coverage):
    ws = wb.create_sheet("START HERE")
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 112
    r = 1

    def title(t):
        nonlocal r
        c = ws.cell(row=r, column=1, value=t); c.font = TITLE_FONT
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        r += 2

    def kv(k, v, bold=False):
        nonlocal r
        a = ws.cell(row=r, column=1, value=k); a.font = H2_FONT if bold else Font(bold=True, size=10)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        b = ws.cell(row=r, column=2, value=v)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        r += 1

    def gap():
        nonlocal r
        r += 1

    def para(t):
        nonlocal r
        c = ws.cell(row=r, column=1, value=t)
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        r += 1

    title(f"Field-by-field audit — {module}")
    para("This workbook checks EVERY input on every screen of one part of the product. For each "
         "one it records what the field is for, the rule it should obey, and what actually "
         "happened when a correct value AND a deliberately wrong value were entered.")
    gap()
    para("Why that last part matters: a normal review ticks a box saying 'the rule exists'. This "
         "one tries to break the rule on purpose. Most of the findings below could only be found "
         "that way.")
    gap()

    kv("What was audited", module, bold=True)
    for k, lbl in (("date", "When"), ("branch", "Code branch"), ("commit", "Commit"),
                   ("tenant", "Test tenant / data"), ("backend", "Server"),
                   ("frontend", "Website")):
        if build.get(k):
            kv(lbl, build[k])
    gap()

    cov = (coverage or [{}])[0]
    kv("VERDICT", cov.get("Verdict", ""), bold=True)
    sev = Counter(x.get("Severity") for x in defects)
    st = Counter(x.get("Status") for x in defects)
    kv("Problems found", ", ".join(f"{sev[s]} {s}" for s in
                                   ["Blocker", "Major", "Minor", "Cosmetic"] if sev.get(s)))
    if st.get("Fixed"):
        kv("Already fixed", f"{st['Fixed']} (fixed and re-checked during this audit)")
    if st.get("Not-A-Bug"):
        kv("Checked and healthy", f"{st['Not-A-Bug']} — recorded so nobody re-investigates them")
    kv("Inputs found on screen", str(cov.get("Fields Harvested", "")))
    if cov.get("Fields In Prior Sheet"):
        kv("The earlier checklist listed", f"{cov['Fields In Prior Sheet']} — the difference is "
                                           "what listing fields by eye misses")
    kv("Inputs actually tested", str(cov.get("Fields Tested", "")))
    gap()

    kv("Read the tabs in this order", "", bold=True)
    for n, d_ in [
        ("1. HOW TO READ", "What every column and every coded value means. Read once."),
        ("2. BUG-CLASSES", "The problems grouped into FAMILIES. Start here — twenty findings "
                           "often share one fix."),
        ("3. DEFECTS", "Every problem, worst first. The 'In plain words' column is the summary; "
                       "everything else is the proof."),
        ("4. COVERAGE", "How much of this is genuinely proven, and what was NOT done. Blunt on purpose."),
        ("5. SPEC", "Every field and the rule it should obey — the reference list."),
        ("6. RESULTS", "What happened to each field when tested, and how strongly it was proven."),
    ]:
        kv(n, d_)
    gap()

    kv("The worst problems", "", bold=True)
    ordered = sorted(defects, key=lambda x: (
        -(SEV_ORDER.index(x.get("Severity", "Cosmetic"))
          if x.get("Severity") in SEV_ORDER else -1),
        -(BLAST_ORDER.index(x.get("Blast Radius", "cosmetic"))
          if x.get("Blast Radius") in BLAST_ORDER else -1)))
    for x in [d_ for d_ in ordered if d_.get("Status") != "Not-A-Bug"][:6]:
        kv(f"{x.get('Defect ID')} · {x.get('Severity')}",
           x.get("In plain words") or x.get("Actual", "")[:300])
    gap()

    kv("One warning", "Any row marked 'Rung 5' was found by reading the source code and has NOT "
                      "been tested yet. Treat those as strong suspicions, not established facts. "
                      "The COVERAGE tab says exactly which.", bold=True)
    ws.freeze_panes = "A2"
    return ws


def sheet_how_to_read(wb):
    ws = wb.create_sheet("HOW TO READ")
    for i, (n, w) in enumerate([("Term", 30), ("What it means", 108)], start=1):
        c = ws.cell(row=1, column=i, value=n)
        c.fill, c.font = HDR_FILL, HDR_FONT
        ws.column_dimensions[get_column_letter(i)].width = w
    r = 2

    def section(t):
        nonlocal r
        c = ws.cell(row=r, column=1, value=t)
        c.font = H2_FONT; c.fill = INFO_FILL
        c2 = ws.cell(row=r, column=2, value=""); c2.fill = INFO_FILL
        r += 1

    def item(k, v):
        nonlocal r
        a = ws.cell(row=r, column=1, value=k); a.font = Font(bold=True, size=10)
        a.alignment = Alignment(vertical="top", wrap_text=True)
        b = ws.cell(row=r, column=2, value=v)
        b.alignment = Alignment(vertical="top", wrap_text=True)
        a.border = b.border = BORDER
        r += 1

    section("The two ideas behind the whole workbook")
    item("Positive vs Negative test",
         "A positive test enters a SENSIBLE value and checks it works. A negative test enters a "
         "deliberately WRONG value and checks the app refuses it. Almost every serious finding "
         "here came from a negative test. On the Negative column, 'PASS' means the app correctly "
         "REFUSED the bad value — which is the good outcome.")
    item("How well is it proven? (Rung)",
         "1 to 5, where 1 is strongest. 1 = we clicked it in the browser. 5 = we only read the "
         "source code and have not tested it. Never treat a 5 as established fact.")
    section("Risk level — 'Blast Radius'")
    item("What it is", "How much damage a wrong value can do. This matters far more than which "
                       "screen the field is on, so it is what the findings are sorted by.")
    for k in BLAST_ORDER:
        item(BLAST[k].split(" — ")[0], BLAST[k].split(" — ", 1)[1])
    section("How serious — 'Severity'")
    for k in ["Blocker", "Major", "Minor", "Cosmetic"]:
        item(k, SEVERITY[k].split(" — ", 1)[1])
    section("Result words")
    for k, v in [("PASS", "Behaved correctly."), ("FAIL", "Behaved wrongly."),
                 ("BLOCKED", "The test could not be completed because something else got in the way "
                             "— NOT the same as passing."),
                 ("NOT-RUN", "We have not tested this yet. An honest gap, not a pass.")]:
        item(k, v)
    section("Status")
    for k, v in STATUS_HELP.items():
        item(k, v.split(" — ", 1)[1] if " — " in v else v)
    section("What kind of fix — 'Fix Shape'")
    for k, v in FIXSHAPE.items():
        item(k, v.split(" — ", 1)[1] if " — " in v else v)
    section("Two columns people misread")
    item("Marker vs Enforced",
         "'Mandatory Marker' = is there a visible * telling you it is required. 'Mandatory "
         "Enforced' = does saving actually fail when blank. They are separate because they break "
         "separately: a marker with no enforcement means the form LIES and bad data gets saved; "
         "enforcement with no marker means the form AMBUSHES you after you have filled it in.")
    item("Negative Run % (on COVERAGE)",
         "The share of fields we deliberately fed bad input to. This is the most diagnostic "
         "number in the workbook. A traditional tick-box checklist scores near zero here while "
         "still showing every row ticked — which is exactly the gap this audit exists to close.")
    section("Bug families — 'Bug Class'")
    item("Why they exist", "Findings are grouped into families so that twenty symptoms sharing "
                           "one cause get fixed once. The BUG-CLASSES tab is the rollup.")
    for k in sorted(CLASS_HELP):
        item(k, CLASS_HELP[k])
    ws.freeze_panes = "A2"
    return ws


# ─────────────────────────────────────────────── main

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = data.get("rows", [])
    defects = data.get("defects", [])
    module = data.get("module", "module")
    build = data.get("build", {})
    coverage = data.get("coverage") or derive_coverage(
        module, rows, data.get("priorSheetFieldCount", ""))

    defects = sorted(defects, key=lambda x: (
        1 if x.get("Status") == "Not-A-Bug" else 0,
        -(SEV_ORDER.index(x.get("Severity", "Cosmetic"))
          if x.get("Severity") in SEV_ORDER else -1),
        -(BLAST_ORDER.index(x.get("Blast Radius", "cosmetic"))
          if x.get("Blast Radius") in BLAST_ORDER else -1)))

    wb = Workbook()
    wb.remove(wb.active)
    sheet_start_here(wb, module, build, defects, coverage)
    sheet_how_to_read(wb)
    write_sheet(wb, "BUG-CLASSES", CLASS_COLS, derive_classes(defects))
    write_sheet(wb, "DEFECTS", DEFECT_COLS, defects)
    write_sheet(wb, "COVERAGE", COVER_COLS, coverage)
    write_sheet(wb, "SPEC", SPEC_COLS, rows)
    write_sheet(wb, "RESULTS", RESULT_COLS, rows)

    wb.save(sys.argv[2])
    missing = [x["Defect ID"] for x in defects if not x.get("In plain words")]
    print(f"wrote {sys.argv[2]}: {len(rows)} rows, {len(defects)} defects, "
          f"{len(derive_classes(defects))} classes")
    if missing:
        print(f"  WARNING: {len(missing)} defects have no 'In plain words' summary: "
              f"{', '.join(missing[:12])}")


if __name__ == "__main__":
    main()
