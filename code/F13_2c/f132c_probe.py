"""Phase F13.2c - structure probe of Authors with affiliations: counts only (no name, no affiliation text). Writes run_logs/probe.json."""
import sys
sys.dont_write_bytecode = True

import json
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132c_lib as L


def main():
    L.install_r17_guard()
    ncols, recs = L.parse_e1()
    cset = L.countries()
    how, nent, npos, mism, nonconsec, multi, empty = Counter(), 0, 0, 0, 0, 0, 0
    entries_per_rec = Counter()
    for r in recs:
        ents = L.author_entries(r)
        nent += len(ents)
        entries_per_rec[min(len(ents), 20)] += 1
        empty += not ents
        how.update(h for _, _, h in ents)
        au = L.authors(r, cset)
        npos += len(au)
        multi += sum(1 for a in au if len(a["affs"]) >= 2)
        names = [a["name"] for a in au]
        nonconsec += len(names) - len(set(names))
        mism += len(au) != r["n_authors"]
    out = {"columns": ncols, "records": len(recs), "entries": nent, "author_positions": npos, "authors_with_2plus_affiliations": multi,
           "records_without_entries": empty, "entry_parse": dict(how), "repeated_name_not_consecutive": nonconsec,
           "records_author_count_differs": mism}
    L.jdump(out, L.RUN_LOGS / "probe.json")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
