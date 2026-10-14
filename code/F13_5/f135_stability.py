"""Phase F13.5 - step 7 (new, (v)): stability of the partition.

S1 - agreement of two partitions on their common nodes (the same keyword in both T3 tables, clustered, generic excluded):
     I2 x v3 (F12.3c) against E1 x v4, and E1 x v3 (step 1) against E1 x v4, for author and index keywords. Rand index = share of
     node pairs that are together in both partitions or apart in both; the adjusted Rand index (Hubert-Arabie) is added because
     with many small clusters most pairs are apart in any partition.
S2 - the author network of E1 x v4 without generic keywords, rebuilt exactly from T3 (records) and T4 (co-occurrence records):
     networkx louvain_communities (weight = association strength, resolution 1.0) with seeds 1-20: clusters, modularity, Rand and
     adjusted Rand against the greedy partition (min, median, max); for the greedy clusters of size >= 5 the pairs among their top 3
     keywords, and the share of runs in which each pair stays together.
Writes tables/S1_partition_agreement.csv|md, S2_algorithm_sensitivity.csv|md, S2b_leading_pairs.csv and F13_5_stability.json."""
import sys
sys.dont_write_bytecode = True

import json
import statistics
from collections import Counter
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L

import networkx as nx
from networkx.algorithms.community import greedy_modularity_communities, louvain_communities, modularity

SEEDS = list(range(1, 21))


def partition(folder, kind):
    return {r["keyword"]: int(r["cluster"]) for r in L.read_csv_path(folder / f"T3_{kind}_nodes.csv") if r["cluster"]}


def comb2(n):
    return n * (n - 1) // 2


def agreement(p, q):
    common = sorted(set(p) & set(q))
    both = apart = only_p = only_q = 0
    for a, b in combinations(common, 2):
        sp, sq = p[a] == p[b], q[a] == q[b]
        both += sp and sq
        apart += (not sp) and (not sq)
        only_p += sp and not sq
        only_q += sq and not sp
    n_pairs = comb2(len(common))
    rand = (both + apart) / n_pairs if n_pairs else None
    cont = Counter((p[k], q[k]) for k in common)
    sa = sum(comb2(v) for v in Counter(p[k] for k in common).values())
    sb = sum(comb2(v) for v in Counter(q[k] for k in common).values())
    sij = sum(comb2(v) for v in cont.values())
    exp = sa * sb / n_pairs if n_pairs else 0
    mx = (sa + sb) / 2
    ari = (sij - exp) / (mx - exp) if mx != exp else None
    return {"common_nodes": len(common), "node_pairs": n_pairs, "together_in_both": both, "apart_in_both": apart,
            "together_only_in_first": only_p, "together_only_in_second": only_q,
            "rand_index": round(rand, 4) if rand is not None else "", "adjusted_rand_index": round(ari, 4) if ari is not None else ""}


def main():
    out = {}
    rows = []
    for kind in ("author", "index"):
        p_i2v3, p_e1v3, p_e1v4 = partition(L.PREV_T, kind), partition(L.V3E1, kind), partition(L.TABLES, kind)
        for lab, p, q in (("I2 x v3 (F12.3c) vs E1 x v4", p_i2v3, p_e1v4), ("E1 x v3 vs E1 x v4", p_e1v3, p_e1v4)):
            rows.append({"layer": kind, "comparison": lab, "nodes_first": len(p), "nodes_second": len(q), **agreement(p, q)})
    f = ["layer", "comparison", "nodes_first", "nodes_second", "common_nodes", "node_pairs", "together_in_both", "apart_in_both",
         "together_only_in_first", "together_only_in_second", "rand_index", "adjusted_rand_index"]
    L.write_csv(L.TABLES / "S1_partition_agreement.csv", f, rows)
    L.write_md(L.TABLES / "S1_partition_agreement.md", "S1. Agreement of partitions on common nodes (Rand index)", f, rows,
               "Common nodes: the same keyword clustered in both T3 tables (generic keywords excluded; no thesaurus mapping). Rand index = "
               "(together in both + apart in both) / node pairs. Adjusted Rand index (Hubert-Arabie): 0 = chance agreement, 1 = identical.")
    out["S1"] = rows

    # S2: rebuild E1 x v4 author network (generic excluded) exactly from T3 and T4
    t3 = [r for r in L.read_csv_path(L.TABLES / "T3_author_nodes.csv") if r["generic"] == "0"]
    freq = {r["keyword"]: int(r["records"]) for r in t3}
    G = nx.Graph()
    for k in sorted(freq):
        G.add_node(k, records=freq[k])
    edges = sorted((r["source"], r["target"], int(r["cooccurrence_records"])) for r in L.read_csv_path(L.TABLES / "T4_author_edges.csv")
                   if r["in_clustering"] == "1")
    for a, b, w in edges:
        G.add_edge(a, b, weight=w, assoc=w / (freq[a] * freq[b]))
    greedy = greedy_modularity_communities(G, weight="assoc", resolution=1.0)
    gpart = {k: i for i, c in enumerate(sorted((sorted(c) for c in greedy), key=lambda c: (-sum(freq[k] for k in c), c[0]))) for k in c}
    t3part = partition(L.TABLES, "author")
    same = all((gpart[a] == gpart[b]) == (t3part[a] == t3part[b]) for a, b in combinations(sorted(t3part), 2))
    assert same and set(gpart) == set(t3part), "the rebuilt network does not reproduce T3's partition"
    qg = modularity(G, greedy, weight="assoc", resolution=1.0)
    top = {}
    for r in L.read_csv_path(L.TABLES / "T5_author_cluster_top10.csv"):
        top.setdefault(int(r["cluster"]), []).append(r["keyword"])
    sizes = {int(r["cluster"]): int(r["size"]) for r in L.read_csv_path(L.TABLES / "T5_author_clusters.csv")}
    lead_pairs = [(c, a, b) for c in sorted(top) if sizes[c] >= 5 for a, b in combinations(top[c][:3], 2)]
    runs, together = [], Counter()
    for s in SEEDS:
        comms = louvain_communities(G, weight="assoc", resolution=1.0, seed=s)
        lp = {k: i for i, c in enumerate(comms) for k in c}
        ag = agreement(lp, gpart)
        kept = 0
        for c, a, b in lead_pairs:
            if lp[a] == lp[b]:
                together[(c, a, b)] += 1
                kept += 1
        runs.append({"seed": s, "clusters": len(comms), "modularity": round(modularity(G, comms, weight="assoc", resolution=1.0), 4),
                     "rand_vs_greedy": ag["rand_index"], "adjusted_rand_vs_greedy": ag["adjusted_rand_index"],
                     "leading_pairs_together": kept, "leading_pairs": len(lead_pairs)})
    summ = []
    for stat, fn in (("min", min), ("median", statistics.median), ("max", max)):
        summ.append({"seed": stat, **{k: round(fn([r[k] for r in runs]), 4) for k in ("clusters", "modularity", "rand_vs_greedy",
                                                                                     "adjusted_rand_vs_greedy", "leading_pairs_together")},
                     "leading_pairs": len(lead_pairs)})
    summ.append({"seed": "greedy (T5)", "clusters": len(greedy), "modularity": round(qg, 4), "rand_vs_greedy": 1.0, "adjusted_rand_vs_greedy": 1.0,
                 "leading_pairs_together": len(lead_pairs), "leading_pairs": len(lead_pairs)})
    f = ["seed", "clusters", "modularity", "rand_vs_greedy", "adjusted_rand_vs_greedy", "leading_pairs_together", "leading_pairs"]
    L.write_csv(L.TABLES / "S2_algorithm_sensitivity.csv", f, runs + summ)
    L.write_md(L.TABLES / "S2_algorithm_sensitivity.md", "S2. Louvain (seeds 1-20) against the greedy partition, author keywords E1 x v4", f, summ,
               f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges (generic keywords excluded), rebuilt from T3 and T4; it "
               "reproduces T5's greedy partition exactly. networkx louvain_communities, weight = association strength, resolution 1.0. "
               "Rows per seed: S2_algorithm_sensitivity.csv; leading pairs (top 3 of each greedy cluster of size >= 5): S2b_leading_pairs.csv.")
    pr = [{"cluster": c, "leading_keyword": top[c][0], "keyword_a": a, "keyword_b": b, "runs_together": together[(c, a, b)],
           "share_of_runs": f"{together[(c, a, b)] / len(SEEDS):.2f}"} for c, a, b in lead_pairs]
    L.write_csv(L.TABLES / "S2b_leading_pairs.csv", ["cluster", "leading_keyword", "keyword_a", "keyword_b", "runs_together", "share_of_runs"], pr)
    out["S2"] = {"runs": runs, "summary": summ, "pairs": pr, "network": [G.number_of_nodes(), G.number_of_edges()],
                 "networkx": nx.__version__}
    L.jdump(out, L.OUT / "F13_5_stability.json")
    for r in rows:
        print("S1", r)
    for r in summ:
        print("S2", r)
    for r in pr:
        print("S2b", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
