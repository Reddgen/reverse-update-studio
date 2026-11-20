#!/usr/bin/env python3
"""Validate the GameCube DOL -> ELF bridge across the local corpus."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rea_bridge
import dol_to_elf

ROOT = sys.argv[1] if len(sys.argv) > 1 else r'E:\GAMES'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test', 'rea_bridge_all')

def is_gamecube(path):
    with open(path, 'rb') as f:
        f.seek(0x1c)
        return f.read(4) == rea_bridge.GAMECUBE_MAGIC

def main():
    rows = []
    for dp, dn, fn in os.walk(ROOT):
        for name in fn:
            if not name.lower().endswith('.iso') or name.lower().endswith('.nkit.iso'):
                continue
            p = os.path.join(dp, name)
            try:
                if not is_gamecube(p):
                    continue
                r = rea_bridge.prepare(p, OUT)
                dol_to_elf.validate_elf(r['prepared'])
                rows.append({'game': os.path.basename(dp), 'ok': True, 'entry': r['entry'],
                             'sections': r['sections'], 'bss_skipped': r['bss_skipped'],
                             'elf': r['prepared']})
            except Exception as e:
                rows.append({'game': os.path.basename(dp), 'ok': False, 'error': str(e)})
    print(json.dumps(rows, indent=2))
    return 0 if all(r['ok'] for r in rows) else 1

if __name__ == '__main__':
    raise SystemExit(main())
