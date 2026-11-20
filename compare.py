"""Pairwise function-level comparison of OpenRCT2 releases."""
import json, collections, os, sys, csv, argparse

def load(ver, reports):
    path = os.path.join(reports, f'fingerprints_{ver}.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data['functions']

def clean_record(f, i):
    r = dict(f)
    r['_i'] = i
    name = r['name'].rstrip('\x00')
    # PDB names occasionally contain an unpaired UTF-16 surrogate; normalize it
    # so the result is valid JSON/CSV text.
    name = name.encode('utf-8', 'replace').decode('utf-8')
    r['name'] = name
    return r

def code_relation(a, b):
    if a['code_sha'] == b['code_sha']:
        return 'identical'
    if a['norm_sha'] == b['norm_sha']:
        if a['prefix_sha'] == b['prefix_sha']:
            return 'data_tail_changed'
        return 'relocated'
    return 'changed'

def src_str(v):
    if not v:
        return ''
    return '%s:%s' % (v.get('file', ''), v.get('line', ''))

def make_pair(a, b, method, confidence, relation=None):
    return {
        'name_a': a['name'], 'name_b': b['name'],
        'rva_a': a['rva'], 'rva_b': b['rva'],
        'size_a': a['size'], 'size_b': b['size'],
        'insn_a': a['insn_count'], 'insn_b': b['insn_count'],
        'code_bytes_a': a['code_bytes'], 'code_bytes_b': b['code_bytes'],
        'truncated_a': a['truncated'], 'truncated_b': b['truncated'],
        'source_a': src_str(a.get('source')), 'source_b': src_str(b.get('source')),
        'code_sha_a': a['code_sha'], 'code_sha_b': b['code_sha'],
        'norm_sha_a': a['norm_sha'], 'norm_sha_b': b['norm_sha'],
        'prefix_sha_a': a['prefix_sha'], 'prefix_sha_b': b['prefix_sha'],
        'tail_sha_a': a['tail_sha'], 'tail_sha_b': b['tail_sha'],
        'match_method': method,
        'code_relation': relation or code_relation(a, b),
        'confidence': confidence,
    }

def match_group(aids, b_ids, A, B, pairs):
    """Match a group of records sharing the same symbol name."""
    if len(aids) == 1 and len(b_ids) == 1:
        pairs.append(make_pair(A[aids[0]], B[b_ids[0]], 'name', 'high'))
        return set(), set()
    a_left, b_left = set(aids), set(b_ids)

    # 1. exact full-code matches (identical bytes)
    ga = collections.defaultdict(list)
    gb = collections.defaultdict(list)
    for i in a_left:
        ga[A[i]['code_sha']].append(i)
    for i in b_left:
        gb[B[i]['code_sha']].append(i)
    for h in set(ga) & set(gb):
        aa = sorted(ga[h], key=lambda i: A[i]['rva'])
        bb = sorted(gb[h], key=lambda i: B[i]['rva'])
        for x, y in zip(aa, bb):
            pairs.append(make_pair(A[x], B[y], 'name_alias', 'high', 'identical'))
            a_left.discard(x); b_left.discard(y)

    # 2. normalized-code matches (relocated / embedded-data-only changes)
    ga = collections.defaultdict(list)
    gb = collections.defaultdict(list)
    for i in a_left:
        ga[A[i]['norm_sha']].append(i)
    for i in b_left:
        gb[B[i]['norm_sha']].append(i)
    for h in set(ga) & set(gb):
        aa = sorted(ga[h], key=lambda i: A[i]['rva'])
        bb = sorted(gb[h], key=lambda i: B[i]['rva'])
        for x, y in zip(aa, bb):
            pairs.append(make_pair(A[x], B[y], 'name_alias', 'medium'))
            a_left.discard(x); b_left.discard(y)

    # 3. remaining same-name records: pair equal-size records by address order
    ga = collections.defaultdict(list)
    gb = collections.defaultdict(list)
    for i in a_left:
        ga[A[i]['size']].append(i)
    for i in b_left:
        gb[B[i]['size']].append(i)
    for sz in set(ga) & set(gb):
        aa = sorted(ga[sz], key=lambda i: A[i]['rva'])
        bb = sorted(gb[sz], key=lambda i: B[i]['rva'])
        for x, y in zip(aa, bb):
            pairs.append(make_pair(A[x], B[y], 'name_alias', 'low'))
            a_left.discard(x); b_left.discard(y)

    return a_left, b_left

def compare(A_raw, B_raw, label_a, label_b):
    A = [clean_record(f, i) for i, f in enumerate(A_raw)]
    B = [clean_record(f, i) for i, f in enumerate(B_raw)]
    by_name_a = collections.defaultdict(list)
    by_name_b = collections.defaultdict(list)
    for f in A:
        by_name_a[f['name']].append(f['_i'])
    for f in B:
        by_name_b[f['name']].append(f['_i'])

    pairs = []
    a_left_all = set()
    b_left_all = set()
    shared_names = set(by_name_a) & set(by_name_b)
    for name in shared_names:
        a_left, b_left = match_group(by_name_a[name], by_name_b[name], A, B, pairs)
        a_left_all |= a_left
        b_left_all |= b_left
    # Records whose name is entirely absent are candidates for cross-name matching
    # (rename) as well as added/removed.
    only_a = {f['_i'] for f in A if f['name'] not in by_name_b}
    only_b = {f['_i'] for f in B if f['name'] not in by_name_a}
    a_left_all |= only_a
    b_left_all |= only_b

    # Symbols folded onto an already-matched code range (ICF aliases) are
    # accounted for by their code unit, not counted as added/removed.
    used_units_a = {(p['rva_a'], p['size_a']) for p in pairs}
    used_units_b = {(p['rva_b'], p['size_b']) for p in pairs}
    alias_a = {i for i in a_left_all if (A[i]['rva'], A[i]['size']) in used_units_a}
    alias_b = {i for i in b_left_all if (B[i]['rva'], B[i]['size']) in used_units_b}
    a_left_all -= alias_a
    b_left_all -= alias_b

    # Cross-name code-fingerprint matching for leftovers. Only unique hashes are
    # accepted; collisions are the main source of false matches for tiny stubs.
    for key in ('code_sha', 'norm_sha'):
        ga = collections.defaultdict(list)
        gb = collections.defaultdict(list)
        for i in a_left_all:
            ga[A[i][key]].append(i)
        for i in b_left_all:
            gb[B[i][key]].append(i)
        for h in set(ga) & set(gb):
            if len(ga[h]) == 1 and len(gb[h]) == 1:
                x, y = ga[h][0], gb[h][0]
                if A[x]['name'] == B[y]['name']:
                    continue
                pairs.append(make_pair(A[x], B[y], 'code_fingerprint', 'medium'))
                a_left_all.discard(x); b_left_all.discard(y)

    # Classify leftovers.
    removed = []
    added = []
    unresolved_a = []
    unresolved_b = []
    for i in sorted(a_left_all):
        rec = A[i]
        if rec['name'] not in by_name_b:
            removed.append(rec)
        else:
            unresolved_a.append(rec)
    for i in sorted(b_left_all):
        rec = B[i]
        if rec['name'] not in by_name_a:
            added.append(rec)
        else:
            unresolved_b.append(rec)

    # Summary.
    rel = collections.Counter(p['code_relation'] for p in pairs)
    methods = collections.Counter(p['match_method'] for p in pairs)
    summary = {
        'from': label_a,
        'to': label_b,
        'symbols_a': len(A),
        'symbols_b': len(B),
        'unique_names_a': len(by_name_a),
        'unique_names_b': len(by_name_b),
        'unique_code_ranges_a': len({(f['rva'], f['size']) for f in A}),
        'unique_code_ranges_b': len({(f['rva'], f['size']) for f in B}),
        'matched_pairs': len(pairs),
        'matched_by_name': methods['name'] + methods['name_alias'],
        'matched_by_code_fingerprint': methods['code_fingerprint'],
        'identical_bytes': rel['identical'],
        'relocated_equivalent': rel['relocated'],
        'code_equivalent_data_tail_changed': rel['data_tail_changed'],
        'changed': rel['changed'],
        'removed': len(removed),
        'added': len(added),
        'alias_of_matched_a': len(alias_a),
        'alias_of_matched_b': len(alias_b),
        'unresolved_a': len(unresolved_a),
        'unresolved_b': len(unresolved_b),
        'accounted_a': len(pairs) + len(removed) + len(alias_a) + len(unresolved_a),
        'accounted_b': len(pairs) + len(added) + len(alias_b) + len(unresolved_b),
    }
    result = {
        'summary': summary,
        'pairs': pairs,
        'removed': removed,
        'added': added,
        'unresolved_a': unresolved_a,
        'unresolved_b': unresolved_b,
    }
    return result

def write_csv(result, path):
    fields = ['name_a', 'name_b', 'rva_a', 'rva_b', 'size_a', 'size_b', 'insn_a', 'insn_b',
              'source_a', 'source_b',
              'code_bytes_a', 'code_bytes_b', 'truncated_a', 'truncated_b', 'match_method',
              'code_relation', 'confidence', 'code_sha_a', 'code_sha_b']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in result['pairs']:
            w.writerow({k: p[k] for k in fields})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reports', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports'))
    ap.add_argument('--from', dest='va', required=True)
    ap.add_argument('--to', dest='vb', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    A = load(args.va, args.reports)
    B = load(args.vb, args.reports)
    result = compare(A, B, args.va, args.vb)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(result, f)
    csv_path = args.out.replace('.json', '_pairs.csv')
    write_csv(result, csv_path)
    print(json.dumps(result['summary'], indent=2))
    print('wrote', args.out, csv_path)

if __name__ == '__main__':
    main()
