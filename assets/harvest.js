/**
 * Field harvest — run in the page via browser_evaluate / evaluate_script.
 *
 * Returns one record per user-visible interactive control, with the label a
 * human reads, the control type, whether it claims to be required, its options,
 * its current value, its section heading, and a locator you can replay.
 *
 * Why a script and not a screenshot: fields below the fold, inside a collapsed
 * section, or behind a toggle are invisible to the eye and identical to the DOM.
 * Harvest, toggle something, harvest again — the diff is the conditional-field
 * inventory.
 *
 * Handles plain HTML controls and Radix/shadcn composites (which render a
 * <button role="combobox"> rather than a <select>, and role="switch" rather than
 * a checkbox), because judging by tag name alone misses most of a modern form.
 *
 * Usage:
 *   1. navigate to the screen, wait for it to settle
 *   2. evaluate this file's contents
 *   3. save the JSON; repeat per tab / per toggle state / per accordion state
 *   4. diff the runs
 */
() => {
  const MAX_TEXT = 160;

  const clean = (s) =>
    (s || '').replace(/\s+/g, ' ').trim().slice(0, MAX_TEXT);

  const visible = (el) => {
    if (!el.isConnected) return false;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0')
      return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 || r.height > 0;
  };

  /* ---------- the label a human actually reads ------------------------- */
  const labelFor = (el) => {
    // 1. aria-label / aria-labelledby win, they are explicit
    if (el.getAttribute('aria-label')) return clean(el.getAttribute('aria-label'));
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const txt = lb
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((n) => n.textContent)
        .join(' ');
      if (clean(txt)) return clean(txt);
    }
    // 2. <label for=id>
    if (el.id) {
      const l = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (l && clean(l.textContent)) return clean(l.textContent);
    }
    // 3. wrapping <label>
    const wrap = el.closest('label');
    if (wrap && clean(wrap.textContent)) return clean(wrap.textContent);
    // 4. shadcn FormItem: nearest previous label-ish sibling in the field wrapper
    const holder = el.closest('[data-slot="form-item"], .space-y-2, .grid, div');
    if (holder) {
      const l = holder.querySelector('label, [data-slot="form-label"]');
      if (l && clean(l.textContent)) return clean(l.textContent);
    }
    // 5. last resort — placeholder or name. Flagged, because a placeholder used
    //    as the only label IS a finding (HELP-ABSENT / label-by-placeholder).
    if (el.placeholder) return `[placeholder] ${clean(el.placeholder)}`;
    if (el.name) return `[name] ${clean(el.name)}`;
    return '[UNLABELLED]';
  };

  /* ---------- the section heading it sits under ------------------------ */
  const sectionFor = (el) => {
    // nearest card/fieldset/section ancestor, then its heading
    const box = el.closest(
      'section, fieldset, [data-slot="card"], [class*="card"], [role="tabpanel"]'
    );
    if (box) {
      const h = box.querySelector(
        'h1,h2,h3,h4,h5,legend,[data-slot="card-title"],[class*="CardTitle"]'
      );
      if (h && clean(h.textContent)) return clean(h.textContent);
    }
    // else walk back for the closest preceding heading in document order
    const heads = [...document.querySelectorAll('h1,h2,h3,h4,h5,legend')].filter(visible);
    let best = null;
    for (const h of heads) {
      if (h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) best = h;
    }
    return best ? clean(best.textContent) : '';
  };

  /* ---------- control type -------------------------------------------- */
  const typeOf = (el) => {
    const tag = el.tagName.toLowerCase();
    const role = el.getAttribute('role');
    if (role === 'switch') return 'toggle';
    if (role === 'combobox') return 'single-select';
    if (role === 'radio') return 'radio';
    if (role === 'checkbox') return 'checkbox';
    if (tag === 'select') return el.multiple ? 'multi-select' : 'single-select';
    if (tag === 'textarea') return 'textarea';
    if (el.isContentEditable) return 'rich-text';
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (t === 'checkbox') return 'checkbox';
      if (t === 'radio') return 'radio';
      if (t === 'file') return 'file';
      if (t === 'date' || t === 'month' || t === 'datetime-local') return 'date';
      if (t === 'number') return 'number';
      if (t === 'email' || t === 'tel' || t === 'password' || t === 'text' || t === 'search')
        return 'text';
      return t;
    }
    return tag;
  };

  /* ---------- required signal (the marker, NOT the enforcement) -------- */
  const requiredSignal = (el) => {
    const attr =
      el.required ||
      el.getAttribute('aria-required') === 'true' ||
      el.getAttribute('data-required') === 'true';
    // a visible asterisk in the label region is the marker a human sees
    let marker = false;
    const holder = el.closest('[data-slot="form-item"], .space-y-2, div');
    if (holder) {
      const lab = holder.querySelector('label, [data-slot="form-label"]');
      if (lab && /\*|\(required\)|required/i.test(lab.textContent || '')) marker = true;
    }
    return { attrRequired: !!attr, visibleMarker: marker };
  };

  /* ---------- options -------------------------------------------------- */
  const optionsOf = (el) => {
    if (el.tagName.toLowerCase() === 'select')
      return [...el.options].map((o) => clean(o.textContent)).slice(0, 60);
    // Radix trigger: options live in a portal only once opened. Record that we
    // could not read them WITHOUT opening — the driver must open and re-harvest.
    if (el.getAttribute('role') === 'combobox') return ['[CLOSED — open and re-harvest]'];
    return [];
  };

  /* ---------- current value -------------------------------------------- */
  const valueOf = (el) => {
    const role = el.getAttribute('role');
    if (role === 'switch' || role === 'checkbox')
      return el.getAttribute('aria-checked') ?? String(!!el.checked);
    if (el.type === 'checkbox' || el.type === 'radio') return String(!!el.checked);
    if (role === 'combobox') return clean(el.textContent);
    return clean(el.value);
  };

  /* ---------- a replayable locator ------------------------------------- */
  const locatorFor = (el, label) => {
    const tid = el.getAttribute('data-testid');
    if (tid) return `getByTestId('${tid}')`;
    if (el.id) return `locator('#${el.id}')`;
    if (label && !label.startsWith('[')) return `getByLabel(${JSON.stringify(label)})`;
    if (el.name) return `locator('[name="${el.name}"]')`;
    if (el.placeholder) return `getByPlaceholder(${JSON.stringify(el.placeholder)})`;
    return null; // no stable locator IS a finding: the field is not automatable
  };

  /* ---------- collect -------------------------------------------------- */
  const SEL = [
    'input:not([type=hidden])',
    'textarea',
    'select',
    '[role=switch]',
    '[role=combobox]',
    '[role=radio]',
    '[role=checkbox]',
    '[contenteditable=true]',
  ].join(',');

  const seen = new Set();
  const fields = [];

  [...document.querySelectorAll(SEL)].forEach((el, i) => {
    if (!visible(el)) return;
    if (seen.has(el)) return;
    seen.add(el);
    const label = labelFor(el);
    const req = requiredSignal(el);
    const r = el.getBoundingClientRect();
    fields.push({
      seq: i,
      label,
      section: sectionFor(el),
      controlType: typeOf(el),
      attrRequired: req.attrRequired,
      visibleMarker: req.visibleMarker,
      value: valueOf(el),
      options: optionsOf(el),
      placeholder: clean(el.placeholder || ''),
      maxLength: el.maxLength && el.maxLength > 0 ? el.maxLength : null,
      min: el.min || null,
      max: el.max || null,
      step: el.step || null,
      disabled: !!el.disabled || el.getAttribute('aria-disabled') === 'true',
      readOnly: !!el.readOnly,
      locator: locatorFor(el, label),
      // scroll depth of the field — feeds the "is the task below the fold" check
      docY: Math.round(r.top + window.scrollY),
    });
  });

  /* ---------- free findings while we are here -------------------------- */
  const tabs = [...document.querySelectorAll('[role=tab]')]
    .filter(visible)
    .map((t) => clean(t.textContent));

  const collapsed = [...document.querySelectorAll('[aria-expanded=false]')]
    .filter(visible)
    .map((t) => clean(t.textContent) || t.getAttribute('aria-controls'));

  const actionButtons = [...document.querySelectorAll('button, [role=button]')]
    .filter(visible)
    .map((b) => ({
      text: clean(b.textContent),
      disabled: !!b.disabled || b.getAttribute('aria-disabled') === 'true',
      docY: Math.round(b.getBoundingClientRect().top + window.scrollY),
    }))
    .filter((b) => b.text);

  // raw-UUID leak sweep on visible text (rung-8 check, free)
  const uuid = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi;
  const uuidLeaks = [
    ...new Set((document.body.innerText || '').match(uuid) || []),
  ].slice(0, 25);

  // snake_case / apiName leak sweep on labels and table headers
  const headers = [...document.querySelectorAll('th, [role=columnheader]')]
    .filter(visible)
    .map((h) => clean(h.textContent))
    .filter(Boolean);
  const jargon = [...fields.map((f) => f.label), ...headers].filter((t) =>
    /_[a-z]|^[a-z]+[A-Z]|(^|\s)(id|uuid|fk)(\s|$)/i.test(t)
  );

  return {
    url: location.pathname + location.search + location.hash,
    title: clean(document.title),
    harvestedAt: new Date().toISOString(),
    counts: {
      fields: fields.length,
      unlabelled: fields.filter((f) => f.label === '[UNLABELLED]').length,
      labelledByPlaceholderOnly: fields.filter((f) => f.label.startsWith('[placeholder]'))
        .length,
      noStableLocator: fields.filter((f) => !f.locator).length,
      requiredAttrNoMarker: fields.filter((f) => f.attrRequired && !f.visibleMarker).length,
      markerNoRequiredAttr: fields.filter((f) => !f.attrRequired && f.visibleMarker).length,
    },
    pageHeight: Math.round(document.body.scrollHeight),
    tabs,
    collapsedSections: collapsed,
    actionButtons,
    tableHeaders: headers,
    freeFindings: { uuidLeaks, jargonCandidates: [...new Set(jargon)] },
    fields,
  };
}
