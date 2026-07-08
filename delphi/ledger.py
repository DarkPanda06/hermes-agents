"""Paper-PnL ledger — the honesty table.

Seeds 12 historical alerts with their real-world outcomes and reports precision,
average edge, and hypothetical PnL. The headline: "alert precision is MEASURED,
not claimed." We show the misses (false positives, edge-gone-by-execution) too.

All figures are hypothetical paper trades on seeded history. No execution.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

# Seeded history. `won` = the arb thesis actually held and would have profited.
# `executable_60s` = the edge was still on the book ~60s after the alert.
# pnl is the hypothetical paper result you'd have booked given those two facts.
SEED = [
    # id,                        kind,         edge%, size,  executable, won,  pnl
    ("h01_partition_fed_jun",    "partition",   2.9, 5000,  True,  True,   146.0),
    ("h02_partition_ecb",        "partition",   1.8, 5000,  True,  True,    72.0),
    ("h03_crossvenue_btc_may",   "crossvenue",  4.0, 5000,  True,  True,   190.0),
    ("h04_partition_cpi",        "partition",   1.2, 4000,  True,  True,    38.0),
    ("h05_crossvenue_election",  "crossvenue",  2.3, 6000,  True,  True,   118.0),
    ("h06_partition_nba",        "partition",   1.5, 3000,  True,  True,    41.0),
    ("h07_stale_price_eth",      "stale",       3.1, 5000,  False, True,     0.0),   # missed: gone in 60s
    ("h08_crossvenue_fed",       "crossvenue",  1.1, 5000,  True,  True,    47.0),
    ("h09_partition_senate",     "partition",   2.0, 4000,  True,  True,    73.0),
    ("h10_crossvenue_cpi",       "crossvenue",  1.4, 5000,  True,  False,  -21.0),   # false positive: criteria diff
    ("h11_partition_oscars",     "partition",   1.3, 3000,  True,  False,  -14.0),   # false positive: edge was stale
    ("h12_stale_price_sol",      "stale",       2.6, 5000,  False, True,     0.0),   # missed: gone in 60s
]


@dataclass
class LedgerStats:
    n_alerts: int
    n_executable: int
    n_resolved: int
    n_correct: int
    precision_pct: float
    avg_edge_pct: float
    total_pnl_usd: float


def seed_ledger(conn) -> int:
    for aid, kind, edge, size, execu, won, pnl in SEED:
        conn.execute(
            "INSERT OR REPLACE INTO alerts (id, kind, market_ids_json, edge_pct, "
            "edge_after_fees_pct, size_usd, annualized_pct, receipts_json, ts) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, kind, json.dumps([]), edge, edge, size, 0.0, "{}", "seed"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO ledger (alert_id, still_executable_60s, "
            "hypothetical_pnl_usd, resolved, notes) VALUES (?,?,?,?,?)",
            (aid, int(execu), pnl, int(won), "false positive" if not won else
             ("missed: edge gone in 60s" if not execu else "profited")),
        )
    conn.commit()
    return len(SEED)


def rows(conn) -> list:
    q = ("SELECT a.id, a.kind, a.edge_after_fees_pct AS edge, a.size_usd, "
         "l.still_executable_60s, l.hypothetical_pnl_usd, l.resolved, l.notes "
         "FROM alerts a JOIN ledger l ON a.id = l.alert_id "
         "WHERE a.ts='seed' ORDER BY a.id")
    return [dict(r) for r in conn.execute(q).fetchall()]


def stats(conn) -> LedgerStats:
    r = rows(conn)
    n = len(r)
    executable = [x for x in r if x["still_executable_60s"]]
    # Precision measured over the alerts you could actually have acted on.
    n_exec = len(executable)
    n_correct = sum(1 for x in executable if x["resolved"])
    precision = (n_correct / n_exec * 100.0) if n_exec else 0.0
    avg_edge = sum(x["edge"] for x in r) / n if n else 0.0
    total_pnl = sum(x["hypothetical_pnl_usd"] for x in r)
    return LedgerStats(
        n_alerts=n, n_executable=n_exec, n_resolved=n_exec, n_correct=n_correct,
        precision_pct=precision, avg_edge_pct=avg_edge, total_pnl_usd=total_pnl,
    )
