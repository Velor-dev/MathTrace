const {test} = require('node:test');
const assert = require('node:assert/strict');
const {PassThrough} = require('node:stream');
const {options, choice, select} = require('../lib/selection.cjs');
const harnesses = require('../../coding-harnesses/research.json').harnesses;

test('every menu item and explicit harness is selectable', () => {
  harnesses.forEach((h, i) => {
    assert.equal(choice(String(i + 1), harnesses), h.id);
    assert.equal(options(['--harness', h.id]).harness, h.id);
  });
  for (const bad of ['', '0', '19', '1x', '-1']) assert.throws(() => choice(bad, harnesses));
  assert.throws(() => options(['--harness']));
  assert.throws(() => options(['--bad']));
  assert.throws(() => options(['--execution-mode', 'bubblewrap']));
});

test('noninteractive requires explicit selection; EOF cancels', async () => {
  await assert.rejects(select(harnesses, {stdin: {isTTY: false}}));
  const input = new PassThrough(); input.isTTY = true;
  const output = new PassThrough(); output.resume();
  const promise = select(harnesses, {stdin: input, stdout: output}); input.end();
  assert.equal(await promise, null);
});

test('menu displays clean names without duplicate parenthetical IDs', async () => {
  const input = new PassThrough(); input.isTTY = true;
  const output = new PassThrough();
  let text = '';
  output.on('data', chunk => { text += chunk.toString(); });
  const promise = select(harnesses, {stdin: input, stdout: output});
  input.write('1\n');
  assert.equal(await promise, harnesses[0].id);
  assert.ok(text.includes(`1. ${harnesses[0].name}\n`));
  assert.ok(!text.includes(`(${harnesses[0].id})`));
});
