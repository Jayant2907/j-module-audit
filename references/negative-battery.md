# The hostile-input battery

For each field, the control type selects which inputs to try. This is the part no
human tester sits through, and it is where `VALIDATION-ABSENT` and
`VALIDATION-OVERTIGHT` come from.

## How to read a result

Three outcomes, and the middle one is the one people mis-file:

| Outcome | Meaning | Class |
|---|---|---|
| rejected, message says what to do | correct | `Negative: PASS` |
| rejected, message unhelpful (`Invalid input`, `Error`, a raw 400) | half-correct | `VALIDATION-WRONG-MESSAGE` |
| accepted and stored | wrong | `VALIDATION-ABSENT` |
| rejected but the value was legitimate | wrong the other way | `VALIDATION-OVERTIGHT` |

**Always check what was stored, not just what the screen said.** A field that
shows an error and saves anyway is the worst version of this.

---

## Universal — every field

1. **blank** (mandatory sweep — clear all, save once per form)
2. **whitespace only** — `"   "`. A rule checking length before trimming passes
   this and stores a blank-looking value that is not blank.
3. **leading/trailing whitespace on a valid value** — `" ABCDE1234F "`. Should be
   trimmed and accepted, not rejected.
4. **over-length** — the declared max + 1 character. Confirm the limit exists and
   that hitting it is explained rather than silently truncating.
5. **paste rather than type** — some validators only fire on keystroke. Paste a
   bad value and save.
6. **the same value twice** — for anything that should be unique (codes, PAN,
   employee number, account number).

## `text`

7. unicode + emoji — `Ravi 😀 Kumar` (should store or reject cleanly, never
   mangle to `?`)
8. real-world punctuation that naive regexes reject — `O'Brien`, `Ram-Kumar`,
   `S. Iyer`, `D'Souza`. **A name field rejecting these is
   `VALIDATION-OVERTIGHT`.**
9. HTML/script-looking string — `<b>x</b>` — confirm it is escaped on display,
   not rendered
10. very long single word (no spaces) — checks layout, not just validation

## `number` / `currency` / `percent`

11. `0`
12. negative — `-1`
13. the boundary either side of each declared limit — for `1..28`, try `0`, `1`,
    `28`, `29`
14. decimals where only integers make sense — `2.5` days, `1.7` months
15. more decimals than money has — `100.999` → what got stored, and is it
    rounded or truncated?
16. thousands separators typed by a human — `1,00,000`
17. a percent over 100 (where the domain forbids it)
18. text in a number field — `abc`
19. very large — `999999999999`. Checks for overflow and for a missing sane
    upper bound; a currency field accepting a trillion is a real finding.

## `date` / `date-range`

20. past date where only future is valid, and the reverse
21. the boundary — the first and last day of the period, and one day outside
22. `29 Feb` in a non-leap year
23. fiscal-year boundary (whatever it is for your domain — calendar year end,
    a specific mid-year date). **This is often the single highest-yield date
    test**; it separates a reporting period and almost every date rule has an
    edge here.
24. end before start (for a range)
25. a date before the record's start date / after its end date
26. ambiguous format typed by hand — `01/02/2026` — which did it take, and does
    the screen show the interpretation back?

## `single-select` / `multi-select` / `radio`

27. the empty/placeholder option — can it be submitted?
28. an option that should be filtered out by another field's value (a state's PT
    slab under a different state) — is the dependency enforced?
29. option list completeness — compare rendered options against the enum in code.
    A missing enum value is `ORPHAN-STATE`; an extra one is a stale option.
30. clear a previously chosen value — can it be returned to empty, and should it
    be?

## `toggle` / `checkbox`

31. **both states, and what each reveals.** Toggle on, harvest; toggle off,
    harvest. Dependent fields appearing/disappearing is the conditional
    inventory.
32. **the off-branch is a real test, not a skip.** For a statutory toggle, off
    must disable *both* employee and employer sides, and the downstream surface
    must show nothing rather than a zero row.
33. turn it off after data exists behind it — is the existing data kept, hidden,
    or destroyed? Silent destruction is a Blocker.

## `file`

34. wrong extension; 35. zero-byte file; 36. over the size limit;
37. a valid extension with the wrong content inside; 38. a file with a very long
name or unicode name. For each: is the rejection explained before or after
upload?

## `lookup` (async search)

39. no results — does it say so, or spin forever?
40. a query that returns many — is it capped, and does it say it was capped?
41. select a value, then change the field it depends on — is the now-invalid
    selection cleared or left stale? **Left stale is `STALE-DENORM`.**

## `computed-readonly`

42. Not typed into — instead, change each input it derives from and confirm it
    recomputes on screen, and that the recomputed value matches the oracle to the
    rupee. A read-only field that does not refresh is `DOWNSTREAM-DRIFT` on its
    own screen.

---

## Domain formats worth their own row

Any field with a checksum, a government/institutional ID format, or a
jurisdiction-specific structure deserves its own row in this table, tested
with one valid and at least two near-miss invalid values — the near-misses
are what catch a regex that is merely *approximately* right. Build this table
once per project; keep it here as a living reference. A few illustrative
generic examples to seed it:

| Field | Rule | Near-miss invalids that catch weak regexes |
|---|---|---|
| Tax/national ID | fixed alphanumeric format, e.g. `[A-Z]{5}[0-9]{4}[A-Z]{1}` | wrong letter/digit count, wrong case, checksum failure if one exists |
| Bank routing code | fixed alphanumeric format | a well-formed code for the wrong institution/branch than selected |
| Bank account number | **varies by institution, e.g. 9–18 digits** | a valid short number and a valid long number — **if either is rejected, that is `VALIDATION-OVERTIGHT`** |
| National registration number | fixed digit count + checksum | correct length but failing checksum — **a length-only check passes this** |
| Postal/PIN code | fixed digit count, jurisdiction rules | a code one digit short/long, a code starting with a digit the format forbids |
| Company/entity registration number | fixed structured format | correct length, wrong internal structure |
| Email | RFC-ish | `a@b`, `a@@b.com`, unicode local part |
| Phone | fixed digit count for the jurisdiction | with/without country code, with spaces, one digit over/under |
| Recurring calendar day | e.g. `1..28` for a monthly cycle | `0`, `29`, `31` — and confirm *why* 28: months with fewer days |

**The bank-account row is the canonical `VALIDATION-OVERTIGHT` case** and worth
running on every product: a fixed-length assumption is wrong for most real
institutions, passes every happy-path test, and blocks real onboarding.

---

## Budgeting the battery

A full battery on 200 fields is thousands of interactions — more than a night.
Prioritise:

1. **Every field at blast radius `money-moves` or `statutory-external`** — full
   battery, no exceptions.
2. **Every mandatory field** — the blank case, at least (this is the one-action
   form sweep, so it is nearly free).
3. **Every field with a declared format** — one valid + two near-misses.
4. **Every numeric field with a range** — the two boundaries either side.
5. Everything else — the universal cases 1–4 only.

Record what you skipped in `COVERAGE`. A battery honestly reported at 40% is
worth more than an implied 100%.
