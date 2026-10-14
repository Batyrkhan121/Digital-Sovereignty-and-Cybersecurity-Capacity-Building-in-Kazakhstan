"""Phase F13.5 - probe (console only): the keyword parts of E1 that hold a ';' not followed by a space, and the keyword sets of
E1 against F12.3c's T1 after v3 (counts of forms new to the frame). Keywords only (R13)."""
import sys
sys.dont_write_bytecode = True

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import f135_lib as L


def main():
    recs = L.load_records()
    for eid, r in sorted(recs.items()):
        for kind in ("ak", "ik"):
            for k in r[kind]:
                if ";" in k:
                    print("semicolon inside a part:", kind, repr(k))
    print("records:", len(recs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
