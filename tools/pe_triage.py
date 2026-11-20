#!/usr/bin/env python3
"""Static PE triage: imports, strings, encoded PowerShell, injection indicators.

Defensive/static only. Never executes the sample.
"""
import argparse
import base64
import json
import os
import re
import sys

sys.path.insert(0, r'C:\Users\Windows 11 PRO\Documents\deepseek-harness\default-workspace\.pylibs')

IMPORTANT_APIS = [
    'CreateProcessA', 'CreateProcessW', 'VirtualAllocEx', 'WriteProcessMemory',
    'NtUnmapViewOfSection', 'SetThreadContext', 'ResumeThread', 'CreateRemoteThread',
    'LoadLibraryA', 'LoadLibraryW', 'GetProcAddress', 'WinExec', 'ShellExecuteA',
    'ShellExecuteW', 'URLDownloadToFileA', 'URLDownloadToFileW', 'InternetOpenA',
    'InternetOpenW', 'HttpSendRequestA', 'HttpSendRequestW', 'NtCreateThreadEx',
    'RtlCreateUserThread', 'QueueUserAPC', 'SetWindowsHookExA', 'SetWindowsHookExW',
]

INJECTION_CHAIN = ['CreateProcess', 'NtUnmapViewOfSection', 'WriteProcessMemory',
                   'SetThreadContext', 'ResumeThread']

def pe_imports(path):
    import pefile
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    names = []
    for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
        for imp in entry.imports:
            if imp.name:
                names.append(imp.name.decode('latin-1', 'replace'))
    return pe, sorted(set(names))

def strings(data):
    ascii_s = [m.group().decode('latin-1') for m in re.finditer(rb'[ -~]{6,}', data)]
    utf16_s = [m.group().decode('utf-16le', 'replace') for m in re.finditer(rb'(?:[ -~]\x00){6,}', data)]
    return ascii_s, utf16_s

def decode_blobs(texts):
    out = []
    seen = set()
    for t in texts:
        for m in re.finditer(r'[A-Za-z0-9+/]{40,}={0,2}', t):
            b64 = m.group()
            if b64 in seen:
                continue
            seen.add(b64)
            try:
                raw = base64.b64decode(b64, validate=False)
            except Exception:
                continue
            decoded = None
            if raw.count(b'\x00') > len(raw) // 4:
                try:
                    decoded = raw.decode('utf-16le', 'ignore')
                except Exception:
                    pass
            if not decoded:
                decoded = raw.decode('utf-8', 'ignore')
            if decoded and any(c.isprintable() for c in decoded):
                ratio = sum(c.isprintable() for c in decoded) / max(1, len(decoded))
                interesting = re.search(r'(https?://|powershell|invoke-|cmd\.exe|\.exe|\.dll|-enc)', decoded, re.I)
                if ratio >= 0.85 and interesting:
                    out.append({'base64_prefix': b64[:32], 'decoded_prefix': decoded[:400]})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pe')
    a = ap.parse_args()
    try:
        pe, imports = pe_imports(a.pe)
        data = open(a.pe, 'rb').read()
        ascii_s, utf16_s = strings(data)
        all_text = '\n'.join(ascii_s + utf16_s)
        decoded = decode_blobs(ascii_s + utf16_s)
        low = {x.lower() for x in imports}
        suspicious = [x for x in IMPORTANT_APIS if x.lower() in low]
        chain_hits = [x for x in INJECTION_CHAIN if any(x.lower() in y for y in low)]
        urls = sorted(set(re.findall(r'https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s"\'<>]*)?', all_text)))[:20]
        domains = sorted(set(re.findall(r'\b[a-zA-Z0-9.-]+\.(?:com|net|org|io|ru|cn|xyz|top|info|biz)\b', all_text)))[:20]
        mitre = []
        if len(chain_hits) >= 4:
            mitre.append('T1055.012 Process Hollowing')
        dynamic = any(x.lower() in low for x in ['loadlibrarya', 'loadlibraryw']) and 'getprocaddress' in low
        download_api = any(x.lower() in low for x in ['urldownloadtofilea', 'urldownloadtofilew', 'internetopena', 'internetopenw', 'httpsendrequesta', 'httpsendrequestw', 'winhttpopen', 'wininet'])
        powershell = 'powershell' in all_text.lower() or 'invoke-webrequest' in all_text.lower()
        if dynamic and (chain_hits or decoded or powershell):
            mitre.append('T1027 / dynamic API resolution (contextual)')
        if powershell:
            mitre.append('T1059.001 PowerShell')
        if urls and (powershell or 'urldownloadtofilea' in low or 'urldownloadtofilew' in low or decoded):
            mitre.append('T1105 Ingress Tool Transfer (possible)')
        result = {
            'file': os.path.abspath(a.pe),
            'machine': hex(pe.FILE_HEADER.Machine),
            'entry': hex(pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            'sections': [s.Name.rstrip(b'\0').decode('latin-1', 'replace') for s in pe.sections],
            'imports_count': len(imports),
            'suspicious_apis': suspicious,
            'injection_chain_hits': chain_hits,
            'dynamic_api_resolution': dynamic,
            'download_api': download_api,
            'powershell_text': powershell,
            'urls': urls,
            'domains': domains,
            'decoded_blobs': decoded[:10],
            'mitre': mitre,
            'note': 'static only; no execution; indicators are not proof',
        }
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({'ok': False, 'error': str(e)}), file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
