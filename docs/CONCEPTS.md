# Plain-Language Concepts

This page maps the everyday way I described the idea to the closest technical
terms. The names are useful, but they are not a credential.

| What I called it | Closer term | What it means |
|---|---|---|
| “the update handshake” | **release transition / update delta** | the change from one shipped build to the next |
| “network handshake” | **update protocol / TLS handshake** | client-server negotiation; **not** what this tool currently analyses |
| “match past and recent” | **binary diff / release diff** | compare two builds |
| “same function, new build” | **function matching** | pair functions across versions |
| “known pattern” | **signature / pattern library** | catalog of known paths or code shapes |
| “puzzle pieces” | **unmatched regions / novelty** | parts the library cannot explain |
| “fingerprint” | **code fingerprint / fuzzy hash** | stable summary of a function’s code |
| “weighted priority” | **risk or triage scoring** | rank what to inspect first |
| “source line mapping” | **debug-symbol / PDB mapping** | map an address to file and line |
| “what it does” | **static analysis** | inspect without executing |

## The logic in one paragraph

Take two builds. Match what you can by symbol, name, code fingerprint or
normalized instructions. Map matched functions to source when debug symbols are
available. Put known sequences in a library. Whatever is left over is not a
failure; it is the unknown part. Give those unknown runs stable IDs, count them
when they recur, and rank them so a human can decide what to study first.

That is the whole idea. The technical names just make it easier to talk to other
people about it.

## What this tool does not do

- It does not capture network update traffic.
- It does not execute the binary.
- It does not automatically prove that a match is correct.
- It does not replace a debugger, decompiler or human review.

## Why the names matter

Using the wrong name can imply a capability the tool does not have. For example:

```text
“network handshake analysis”  → implies packet/protocol capture
“release diff”                → what the tool actually does
```

Being precise is not about sounding expert. It is about not overclaiming.
