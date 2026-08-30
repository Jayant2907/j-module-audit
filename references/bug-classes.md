# Bug-class vocabulary

Every finding gets **exactly one** class. This is a closed list — if a finding
genuinely fits none of them, add a class here with a canonical example rather
than inventing a one-off label, because an ad-hoc label cannot be rolled up and a
finding that cannot be rolled up cannot become a systemic fix.

The vocabulary is the point of the skill. One instance is a bug; nine instances
of one class across nine screens is an architecture finding with a single fix.

---

## A · Requirement & validation

| Class | Definition | How you find it |
|---|---|---|
| `MANDATORY-MARKER-MISSING` | field is required but no visible marker (`*`, `aria-required`) | DOM read vs oracle |
| `MANDATORY-NOT-ENFORCED` | marker shown (or rule documented) but saving blank succeeds | the whole-form mandatory sweep |
| `MANDATORY-WRONG` | field marked required that business says is optional (or vice versa) | oracle vs statute/spec |
| `VALIDATION-ABSENT` | documented rule not enforced; garbage is accepted and stored | negative battery |
| `VALIDATION-OVERTIGHT` | app rejects a legitimate real-world value | negative battery + domain knowledge |
| `VALIDATION-CLIENT-ONLY` | enforced in the browser, not on the server — bypassable | oracle: DTO vs FE |
| `VALIDATION-SERVER-ONLY` | server 400s with no inline field-level hint | oracle + live save |
| `VALIDATION-WRONG-MESSAGE` | correctly rejected, but the message does not say what to do | read the message |
| `CONDITION-UNDEFINED` | "as applicable" with no discoverable condition anywhere | oracle returns `NONE` |
| `FIELD-UNDOCUMENTED` | field exists in the UI with no oracle in code, statute or spec | Phase 2 |

**`VALIDATION-OVERTIGHT` deserves special attention** — it is invisible to a
checklist audit because the happy path passes. Canonical shape: a bank account
number validated as exactly 14 digits when Indian bank account lengths vary by
bank; a name field restricted to `[A-Za-z ]+` rejecting real names with dots or
hyphens; a PIN code regex that rejects a valid one.

## B · Persistence & truth

| Class | Definition |
|---|---|
| `SILENT-SAVE-FAILURE` | success signal shown, database unchanged |
| `VALUE-REVERTS` | value gone or changed on returning to the screen |
| `DEFAULT-WRONG` | default value contradicts statute, spec, or common sense |
| `DEFAULT-MISSING` | field that should have a sane default opens blank, forcing a guess |
| `DOWNSTREAM-DRIFT` | value saved correctly, downstream surface shows a different or stale value |
| `DOWNSTREAM-ABSENT` | value never reaches the surface the spec says it feeds |
| `AUDIT-MISSING` | change recorded with no who/when trail |
| `STALE-DENORM` | a denormalized copy of the field diverges from its authoritative source |

## C · Presentation & comprehension

| Class | Definition |
|---|---|
| `ID-LEAK` | raw UUID or internal key shown as reading matter |
| `JARGON-LABEL` | API field name, snake_case, or internal term leaking into a label |
| `FORMAT-INCONSISTENT` | money/date/number format differs from its siblings on the same screen |
| `UNIT-UNSTATED` | a number with no ₹ / % / days / months stated |
| `MASKING-GAP` | PII rendered unmasked where the policy masks it |
| `HELP-ABSENT` | consequential field with no explanation visible without hovering |
| `EMPTY-STATE-MUTE` | empty state says "no data" without saying what to do |

## D · Structure, access & flow

| Class | Definition |
|---|---|
| `UNREACHABLE` | route resolves but no menu path leads to it from a fresh login |
| `PLACEMENT-WRONG` | field is on the wrong screen / section for how a user thinks |
| `DEAD-CONTROL` | control renders and does nothing |
| `RBAC-GAP` | a role can see or edit a field it should not |
| `RBAC-OVERBLOCK` | a role that needs the field cannot see it |
| `ORPHAN-STATE` | a state the backend can produce that no screen renders |
| `CONSOLE-ERROR` | red console error or failed network call on load |
| `ENDPOINT-500` | a core endpoint returns a generic server error, blocking a whole operation |

**`ENDPOINT-500` carries an obligation**: before filing it as a product defect,
check whether it reproduces on a *second* tenant. A 500 that only happens on your
fixture tenant is a data problem wearing a code problem's clothes. Say which you
established. *Canonical:* a cluster of validate/recompute/export endpoints all
500'd for one tenant while the plain list endpoints worked — filed with trace
ids and an explicit "not root-caused, confirm on a second tenant" caveat rather
than as a confirmed code bug.

`PLACEHOLDER-WRONG` note: a hint used as a label, or a placeholder that
disappears leaving the user unable to recall what the field was — file as
`HELP-ABSENT`.

---

## Rollup guidance

**Look for the shared component first.** Before writing up N instances of a
presentation or requirement class, find the primitive they all render through. A
marker gap on 91 fields is one `<FormLabel>` fix; writing it as 91 tickets is a
failure of the audit, not a thorough audit.

**Distinguish the three fix shapes** — the rollup sheet's `Fix Shape` column:

- `shared-component` — one primitive, closes the class. Do these first; highest
  ratio of findings-closed to risk-taken.
- `backend-rule` — a DTO/validator/migration change. Watch the project rule
  against retroactively tightening validation on existing data: a tightening fix
  needs a same-PR data migration.
- `per-screen` — genuinely local. Order by blast radius.
- `spec-decision` — nobody knows what the right answer is. These are **not**
  developer tickets; they are questions for the product owner, and mixing them
  into a defect list stalls the whole list. Separate them explicitly.

**A class with one instance is not yet a class.** Report it as a defect. Promote
it to a class in the cumulative ledger once a second module produces the same
shape — that is the signal that the fix belongs in a shared place.
