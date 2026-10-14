"""Phase F13.2d - step 1 (candidates): for each of the 348 institutions of F13.2c's T3a_v2, the normalised key (F13.2b's norm_kz), the
distinctive key (its tokens minus the generic stop-list) and candidate pairs: the same distinctive key, or rapidfuzz token_set_ratio of
the distinctive keys >= 80 (process.cdist). Clusters = union-find over the pairs; clusters of >= 2 names are written to
tables/T1a_candidate_clusters.csv (one row per name). The stop-list is written to tables/generic_tokens.csv. Deterministic.
Imported by f132d_thesaurus.py; run alone it writes the two tables and prints the clusters."""
import sys
sys.dont_write_bytecode = True

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f132d_lib as L

from rapidfuzz import fuzz, process

THRESHOLD = 80


def names_v2():
    return [(r["institution"], int(r["records"])) for r in L.read_csv(L.IN_V2["T3a"])]


def clusters():
    names = names_v2()
    keys = [" ".join(L.distinctive(n)) for n, _ in names]
    idx = [i for i, k in enumerate(keys) if k]
    M = process.cdist([keys[i] for i in idx], [keys[i] for i in idx], scorer=fuzz.token_set_ratio)
    pairs = {}
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            i, j = idx[a], idx[b]
            s = float(M[a][b])
            if keys[i] == keys[j] or s >= THRESHOLD:
                pairs[(i, j)] = s
    parent = list(range(len(names)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in sorted(pairs):
        parent[find(i)] = find(j)
    groups = {}
    for i in range(len(names)):
        groups.setdefault(find(i), []).append(i)
    cl = [sorted(g, key=lambda i: (-names[i][1], names[i][0])) for g in groups.values() if len(g) >= 2]
    cl.sort(key=lambda g: (-sum(names[i][1] for i in g), names[g[0]][0]))
    out = []
    for cid, g in enumerate(cl, 1):
        common = set(keys[g[0]].split())
        for i in g[1:]:
            common &= set(keys[i].split())
        links = [s for (i, j), s in pairs.items() if i in g and j in g]
        for i in g:
            best = max((s for (a, b), s in pairs.items() if i in (a, b)), default=0)
            out.append({"cluster_id": cid, "institution": names[i][0], "records": names[i][1], "distinctive_key": keys[i],
                        "common_tokens": " ".join(sorted(common)), "best_score": f"{best:.1f}", "cluster_min_link": f"{min(links):.1f}",
                        "cluster_size": len(g)})
    return names, keys, pairs, out


def write_tables(names, keys, pairs, rows):
    gen = [{"token": t, "source": "brief"} for t in L.GENERIC_BRIEF] + [{"token": t, "source": f"executor: {why}"} for t, why in L.GENERIC_ADDED.items()]
    L.table("generic_tokens", "Generic tokens removed from the normalised key (the stop-list of step 1)", ["token", "source"], gen)
    n_cl = len({r["cluster_id"] for r in rows})
    L.table("T1a_candidate_clusters", "T1a - candidate clusters (one row per name; clusters of two or more names)",
            ["cluster_id", "institution", "records", "distinctive_key", "common_tokens", "best_score", "cluster_min_link", "cluster_size"], rows,
            note=f"{len(names)} institutions of T3a_v2; {sum(1 for k in keys if not k)} have no distinctive token (only generic words) and take "
                 f"no part; candidate pairs: the same distinctive key or rapidfuzz token_set_ratio >= {THRESHOLD} ({len(pairs)} pairs); "
                 f"clusters by union-find: {n_cl} clusters of {len(rows)} names. best_score: the name's highest score to another name of the "
                 "cluster; cluster_min_link: the weakest pair that joined the cluster.", md_rows=None)


def main():
    names, keys, pairs, rows = clusters()
    write_tables(names, keys, pairs, rows)
    cur = None
    for r in rows:
        if r["cluster_id"] != cur:
            cur = r["cluster_id"]
            print(f"--- C{cur} (size {r['cluster_size']}, common '{r['common_tokens']}', min link {r['cluster_min_link']})")
        print(f"   {r['records']:>4} | {r['institution']} | {r['distinctive_key']} | {r['best_score']}")
    print("names", len(names), "empty keys", sum(1 for k in keys if not k), "pairs", len(pairs), "clusters", len({r['cluster_id'] for r in rows}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
