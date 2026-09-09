import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

// Exercise the shipped handlers with the null relatedTarget sequence seen on touch.
function fixture() {
  const handlers = new Map();
  const summary = { focus() { summary.focused = true; } };
  const item = {
    open: true,
    contains(target) { return target === summary || target === control; },
    querySelector() { return summary; },
    addEventListener(type, handler) { handlers.set(type, handler); },
  };
  const control = {};
  const documentHandlers = new Map();
  const document = {
    querySelectorAll(selector) { return selector === '[data-disclosure]' ? [item] : []; },
    querySelector() { return null; },
    addEventListener(type, handler) { documentHandlers.set(type, handler); },
  };
  const source = readFileSync('app/templates/partials/navigation_script.html', 'utf8')
    .replace(/<\/?script>/g, '').replace(/\{\{.*?\}\}/g, '"Discard changes?"');
  runInNewContext(source, { document });
  return { item, summary, control, handlers, documentHandlers };
}

test('touch focus loss does not hide controls before their click', () => {
  for (const action of ['theme radio', 'Swagger link', 'logout button']) {
    const f = fixture();
    f.handlers.get('focusout')?.({ relatedTarget: null });
    assert.equal(f.item.open, true, action);
    f.documentHandlers.get('click')({ target: f.control });
    assert.equal(f.item.open, true, action);
  }
});

test('outside click closes menu', () => {
  const f = fixture();
  f.documentHandlers.get('click')({ target: {} });
  assert.equal(f.item.open, false);
});

test('Escape closes menu and restores summary focus', () => {
  const f = fixture();
  let prevented = false;
  f.handlers.get('keydown')({ key: 'Escape', preventDefault() { prevented = true; } });
  assert.equal(f.item.open, false);
  assert.equal(f.summary.focused, true);
  assert.equal(prevented, true);
});
