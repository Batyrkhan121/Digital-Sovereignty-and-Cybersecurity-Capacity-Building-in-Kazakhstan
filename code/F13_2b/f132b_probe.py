"""Phase F13.2b - structure probe (counts and institution/country strings only; no author field is kept). Writes
run_logs/probe.json and run_logs/probe_kz_keys.csv / probe_foreign_keys.csv, used to build the institutions thesaurus."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132b_lib as L


def main():
    L.install_r17_guard()
    ncols, recs = L.parse_e1()
    lines = parts_n = 0
    last = Counter()
    nparts = Counter()
    levels = Counter()
    kz_rec = defaultdict(set)
    kz_forms = defaultdict(list)
    kz_level = defaultdict(Counter)
    fo_rec = defaultdict(set)
    fo_forms = defaultdict(list)
    unres = Counter()
    lines_per_rec = Counter()
    no_auth = 0
    for r in recs:
        ls = L.aff_lines(r["affiliations"])
        lines_per_rec[len(ls)] += 1
        no_auth += r["n_authors"] == 0
        for line in ls:
            lines += 1
            p = L.parse_line(line)
            last[p["country_part"]] += 1
            nparts[p["n_parts"]] += 1
            levels[p["level"]] += 1
            if p["unresolved"]:
                unres[p["first_part"]] += 1
            if p["country_part"] == L.KZ:
                k = L.norm_kz(p["institution"])
                kz_rec[k].add(r["eid"])
                kz_forms[k].append(p["institution"])
                kz_level[k][p["level"]] += 1
            elif p["country_part"] in L.COUNTRY_SET:
                k = (L.norm_foreign(p["institution"]), p["country_part"])
                fo_rec[k].add(r["eid"])
                fo_forms[k].append(p["institution"])
    L.write_csv(L.RUN_LOGS / "probe_kz_keys.csv", ["key", "records", "lines", "level", "forms"],
                [{"key": k, "records": len(v), "lines": len(kz_forms[k]), "level": kz_level[k].most_common(1)[0][0],
                  "forms": " || ".join(f"{a} ({b})" for a, b in Counter(kz_forms[k]).most_common(4))}
                 for k, v in sorted(kz_rec.items(), key=lambda kv: (-len(kv[1]), kv[0]))])
    L.write_csv(L.RUN_LOGS / "probe_foreign_keys.csv", ["key", "country", "records", "form"],
                [{"key": k[0], "country": k[1], "records": len(v), "form": L.most_common_form(fo_forms[k])}
                 for k, v in sorted(fo_rec.items(), key=lambda kv: (-len(kv[1]), kv[0]))])
    out = {"columns": ncols, "records": len(recs), "unique_eid": len({r["eid"] for r in recs}), "affiliation_lines": lines,
           "records_without_author_names": no_auth, "lines_per_record": dict(sorted(lines_per_rec.items())),
           "parts_per_line": dict(sorted(nparts.items())), "levels": dict(sorted(levels.items())),
           "last_parts": dict(sorted(last.items(), key=lambda kv: (-kv[1], kv[0]))),
           "last_parts_not_in_list": sorted(k for k in last if k not in L.COUNTRY_SET),
           "kz_keys": len(kz_rec), "kz_keys_2plus": sum(1 for v in kz_rec.values() if len(v) >= 2),
           "unresolved_first_parts_2plus": dict(sorted(((k, v) for k, v in unres.items() if v >= 2), key=lambda kv: (-kv[1], kv[0])))}
    L.jdump(out, L.RUN_LOGS / "probe.json")
    print(json.dumps({k: out[k] for k in ("columns", "records", "unique_eid", "affiliation_lines", "records_without_author_names",
                                          "kz_keys", "kz_keys_2plus")}, indent=1))
    print("distinct last parts:", len(last), "; not in list:", len(out["last_parts_not_in_list"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
