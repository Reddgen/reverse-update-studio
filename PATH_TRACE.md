# Path Tracing

## Model

```text
trace = ordered node labels
      → library matches
      → unmatched runs = puzzle pieces
      → features
      → priority 0..1 + level
```

Example:

```text
LoadConfig
ResolvePath
ParseXML
ApplyConfig
UnknownA
UnknownB
Serialize
WriteFile
Flush
```

Result:

```text
matches:  lib_config_load[0:4], lib_save[6:9]
puzzles:  pz_<hash> = UnknownA -> UnknownB
trace:    tr_<id>
priority: 0.15 low
```

## Stable IDs

- `trace_id`: `tr_` + 12 hex, unique per trace.
- `puzzle_id`: `pz_` + first 12 hex of SHA-256 of the normalized signature.

The same unknown run always gets the same puzzle ID, so it can be counted,
logged and reused across traces.

## Library format

```json
{
  "paths": [
    {
      "id": "lib_config_load",
      "name": "Config load",
      "sequence": ["LoadConfig", "ResolvePath", "ParseXML", "ApplyConfig"],
      "tags": ["config"],
      "confidence": 0.95
    }
  ]
}
```

Matching is longest contiguous match first, then by position. Overlapping matches
are rejected.

## Features

| Feature | Meaning |
|---|---|
| `novelty` | unknown nodes / total |
| `coverage` | matched nodes / total |
| `library_hits` | number of known paths matched |
| `reuse` | highest occurrence count of a puzzle piece |
| `unknown_count` | number of unmatched nodes |

## Priority

Default heuristic:

```text
sigmoid(-0.15
  + 0.45*novelty
  - 0.25*coverage
  - 0.15*min(1,hits/3)
  + 0.25*min(1,reuse/5)
  + 0.10*min(1,unknown/10))
```

Levels:

```text
>=0.75 critical
>=0.55 high
>=0.35 medium
<0.35  low
```

## Train

Training data is JSONL:

```json
{"features":{"novelty":0.9,"coverage":0.1,"library_hits":0,"reuse":1,"unknown_count":8},"label":0.95}
```

Train:

```text
python path_cli.py train --data path_training.jsonl --out path_model.json
```

Use:

```text
python path_cli.py trace --db traces.sqlite --nodes "A,B,C" ^
  --library path_library.json --model path_model.json
```

## Studio

**Trace** in the sidebar:

- enter nodes;
- see library matches;
- see stable puzzle IDs;
- see priority;
- browse the puzzle catalog.

API:

```text
POST /api/trace       {"nodes": ["A", "B"]}
GET  /api/traces
GET  /api/puzzles
```

## Limits

- Matching is exact after normalization; no fuzzy symbol matching yet.
- The priority model is a simple logistic regression.
- Puzzle status is `unknown` until manually annotated.
- Production should review matches before treating a library ID as ground truth.
