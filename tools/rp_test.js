#!/usr/bin/env node
/* Local wrapper/test for RomPatcher.js (MIT). */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = __dirname;
global.BinFile = require(path.join(root, 'RomPatcher.js-master', 'rom-patcher-js', 'modules', 'BinFile.js'));
const RomPatcher = require(path.join(root, 'RomPatcher.js-master', 'rom-patcher-js', 'RomPatcher.js'));

function sha(p) {
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}

const work = path.join(root, 'test');
fs.mkdirSync(work, { recursive: true });
const orig = path.join(work, 'original.bin');
const mod = path.join(work, 'modified.bin');
const data = Buffer.alloc(4096, 0x41);
for (let i = 0; i < data.length; i++) data[i] = (i * 37 + 11) & 0xff;
const modified = Buffer.from(data);
modified[100] ^= 0xff;
modified[2000] = 0x42;
modified[3000] ^= 0x55;
fs.writeFileSync(orig, data);
fs.writeFileSync(mod, modified);

const result = { original_sha: sha(orig), modified_sha: sha(mod), formats: {} };
for (const fmt of ['ips', 'bps', 'ups']) {
  try {
    const patch = RomPatcher.createPatch(new BinFile(orig), new BinFile(mod), fmt);
    const pf = patch.export();
    const patchPath = path.join(work, `patch.${fmt}`);
    pf.fileName = patchPath;
    pf.save();

    const parsed = RomPatcher.parsePatchFile(new BinFile(patchPath));
    const patched = RomPatcher.applyPatch(new BinFile(orig), parsed, { outputSuffix: false });
    const outPath = path.join(work, `patched.${fmt}.bin`);
    patched.fileName = outPath;
    patched.save();

    result.formats[fmt] = {
      patch: patchPath,
      patch_bytes: fs.statSync(patchPath).size,
      output_sha: sha(outPath),
      match: sha(outPath) === result.modified_sha,
    };
  } catch (e) {
    result.formats[fmt] = { error: String(e && e.message || e) };
  }
}
console.log(JSON.stringify(result, null, 2));
