"""Phase F13.1 - structure probe: column names of E1/E1b, tag names and counts of E2, the I1/I3 column names. Names and
counts only - no value of any record is written or printed."""
import sys
sys.dont_write_bytecode = True

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f131_lib as L

c1, r1 = L.parse_scopus(L.E1)
c1b, r1b = L.parse_scopus(L.E1B)
seen, r2 = L.parse_wos(L.E2)
out = {"E1_columns": c1, "E1_rows": len(r1), "E1b_columns": c1b, "E1b_rows": len(r1b), "E2_records": len(r2),
       "E2_tag_line_counts": dict(sorted(seen.items())), "E2_tags_per_record": {}}
for t in sorted(seen):
    out["E2_tags_per_record"][t] = sum(1 for r in r2 if t in r)
L.jdump(out, L.RUN_LOGS / "probe.json")
print(json.dumps({k: v for k, v in out.items() if k != "E2_tag_line_counts"}, ensure_ascii=False))
