'use strict';
function options(argv) {
  const result = {mode: 'direct'};
  const names = {'--harness': 'harness', '--python': 'python', '--host-executable':'hostExecutable', '--codex-skills': 'codexSkills'};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--help') { result.help = true; continue; }
    const key = names[argv[i]];
    if (!key || !argv[i + 1] || argv[i + 1].startsWith('--')) throw Error('Unknown option or missing value: ' + argv[i]);
    result[key] = argv[++i];
  }
  if (result.codexSkills && !['.codex/skills', '.agents/skills'].includes(result.codexSkills)) throw Error('Invalid Codex skill directory');
  return result;
}
function choice(answer, harnesses) {
  if (!/^\d+$/.test(answer.trim())) throw Error('Select a numbered harness, or cancel with Ctrl+C');
  const value = harnesses[Number(answer.trim()) - 1];
  if (!value) throw Error('Harness number is outside the menu');
  return value.id;
}
async function select(harnesses, io = process) {
  if (!io.stdin.isTTY) throw Error('Non-interactive installation requires --harness <id>');
  const readline = require('node:readline');
  const rl = readline.createInterface({input: io.stdin, output: io.stdout});
  io.stdout.write(harnesses.map((h, i) => `${i + 1}. ${h.name}`).join('\n') + '\n');
  return new Promise(resolve => {
    let answered = false;
    rl.on('close', () => { if (!answered) resolve(null); });
    rl.on('SIGINT', () => rl.close());
    function ask() {
      rl.question('Select coding harness: ', answer => {
        try { const id = choice(answer, harnesses); answered = true; rl.close(); resolve(id); }
        catch (e) { io.stdout.write(e.message + '\n'); ask(); }
      });
    }
    ask();
  });
}
module.exports = {options, choice, select};
