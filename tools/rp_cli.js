#!/usr/bin/env node
/*
 * Local CLI wrapper for RomPatcher.js (MIT, Marc Robledo).
 * Usage:
 *   node rp_cli.js apply  <rom> <patch> <output>
 *   node rp_cli.js create <original> <modified> <format> <output>
 *   node rp_cli.js detect <patch>
 *
 * This wrapper is local-only; it does not upload files.
 */
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const root = __dirname;
global.BinFile = require(path.join(root, 'RomPatcher.js-master', 'rom-patcher-js', 'modules', 'BinFile.js'));
const RomPatcher = require(path.join(root, 'RomPatcher.js-master', 'rom-patcher-js', 'RomPatcher.js'));

function sha(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}
function out(obj) {
  console.log(JSON.stringify(obj, null, 2));
}
function fail(msg) {
  out({ ok: false, error: msg });
  process.exit(2);
}

const [cmd, ...args] = process.argv.slice(2);
if (!cmd) fail('command required: apply | create | detect');

if (cmd === 'detect') {
  const p = args[0];
  if (!p || !fs.existsSync(p)) fail('patch not found');
  try {
    const patch = RomPatcher.parsePatchFile(new BinFile(p));
    out({ ok: true, patch: p, detected: !!patch, bytes: fs.statSync(p).size });
  } catch (e) { fail(String(e && e.message || e)); }
} else if (cmd === 'apply') {
  const [rom, patchPath, output] = args;
  if (!rom || !patchPath || !output) fail('usage: apply <rom> <patch> <output>');
  if (!fs.existsSync(rom)) fail('rom not found');
  if (!fs.existsSync(patchPath)) fail('patch not found');
  if (fs.existsSync(output)) fail('output already exists; choose a new path');
  try {
    const patch = RomPatcher.parsePatchFile(new BinFile(patchPath));
    if (!patch) fail('invalid patch');
    const patched = RomPatcher.applyPatch(new BinFile(rom), patch, { outputSuffix: false });
    patched.fileName = output;
    patched.save();
    out({ ok: true, command: 'apply', rom_sha256: sha(rom), patch: patchPath, output, output_sha256: sha(output), bytes: fs.statSync(output).size });
  } catch (e) { fail(String(e && e.message || e)); }
} else if (cmd === 'create') {
  const [original, modified, format, output] = args;
  if (!original || !modified || !format || !output) fail('usage: create <original> <modified> <format> <output>');
  if (!fs.existsSync(original)) fail('original not found');
  if (!fs.existsSync(modified)) fail('modified not found');
  if (fs.existsSync(output)) fail('output already exists; choose a new path');
  try {
    const patch = RomPatcher.createPatch(new BinFile(original), new BinFile(modified), format);
    const pf = patch.export();
    pf.fileName = output;
    pf.save();
    out({ ok: true, command: 'create', original_sha256: sha(original), modified_sha256: sha(modified), format, output, patch_bytes: fs.statSync(output).size });
  } catch (e) { fail(String(e && e.message || e)); }
} else {
  fail('unknown command: ' + cmd);
}
