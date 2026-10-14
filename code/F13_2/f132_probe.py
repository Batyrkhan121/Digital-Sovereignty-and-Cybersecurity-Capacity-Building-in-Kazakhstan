"""Phase F13.2 - probe of field values needed for the normalisation rules: conference names, funder first elements, publishers,
OA categories, languages, publication stages, document types (organisation names and codes only; no author name, abstract or
reference). Written to run_logs/probe.json."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132_lib as L

header, E1 = L.parse_e1()
E2 = L.parse_e2()
out = {
    "E1_rows": len(E1), "E2_records": len(E2), "E2_keys": sorted({k for r in E2 for k in r}),
    "doc_types": Counter(r["Document Type"] for r in E1).most_common(),
    "stages": Counter(r["Publication Stage"] for r in E1).most_common(),
    "languages": Counter(r["Language of Original Document"] for r in E1).most_common(),
    "oa": Counter(x.strip() for r in E1 for x in r["Open Access"].split(";") if x.strip()).most_common(),
    "authors_missing": sum(r["authors_missing"] for r in E1),
    "conference_names_of_conf_papers": Counter(r["Conference name"] for r in E1 if r["Document Type"].lower() == "conference paper").most_common(),
    "funder_first": Counter(f.split(",")[0].strip() for r in E1 for f in r["Funding Details"].split("; ") if f.strip()).most_common(80),
    "publishers": Counter(r["Publisher"] for r in E1).most_common(25),
    "wos_dt": Counter(r.get("DT", "") for r in E2).most_common(),
}
L.jdump(out, L.RUN_LOGS / "probe.json")
print(json.dumps({k: out[k] for k in ("E1_rows", "E2_records", "E2_keys", "doc_types", "stages", "languages", "oa", "authors_missing", "wos_dt")},
                 ensure_ascii=False))
print("conference names:", len(out["conference_names_of_conf_papers"]), "distinct")
