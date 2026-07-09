"""Fee & slippage models — the arithmetic behind every arb alert.

These are PARAMETERIZED, documented estimates, not exchange-exact schedules.
Every number an alert prints traces back to a function here so the "why" is
auditable. All fractions are decimals (0.02 == 2%).

Fee models
----------
Polymarket : historically 0% trading fees; we model a parameterized
             ``2% fee on winnings`` (profit), matching the venue's published
             upper-bound policy. fee = POLYMARKET_FEE_ON_WINNINGS * profit.
Kalshi     : per-contract fee = ceil-free continuous approximation of Kalshi's
             published formula  fee = 0.07 * price * (1 - price)  per contract.

Slippage model
--------------
Linear market-impact:  slippage_pct = SLIP_K * size_usd / liquidity_usd.
SLIP_K (dimensionless, default 0.5) is the impact coefficient: deploying size
equal to the book's liquidity would move price ~SLIP_K. Documented, tunable.
"""
from __future__ import annotations

# --- venue fee parameters -------------------------------------------------
POLYMARKET_FEE_ON_WINNINGS = 0.02   # 2% of profit
KALSHI_FEE_COEF = 0.07              # Kalshi's published per-contract coefficient

# --- slippage parameter ---------------------------------------------------
SLIP_K = 0.5                        # linear market-impact coefficient


def slippage_pct(size_usd: float, liquidity_usd: float) -> float:
    """Fraction of notional lost to market impact. Guards zero liquidity."""
    if not liquidity_usd or liquidity_usd <= 0:
        return 1.0  # unknown/empty book — treat as fully illiquid
    return SLIP_K * size_usd / liquidity_usd


def polymarket_fee(profit_usd: float) -> float:
    """2% on winnings. No fee on a losing/zero-profit leg."""
    return POLYMARKET_FEE_ON_WINNINGS * max(profit_usd, 0.0)


def kalshi_fee_per_contract(price: float) -> float:
    """Kalshi per-$1-contract fee at a given price (0-1)."""
    return KALSHI_FEE_COEF * price * (1.0 - price)


def venue_fee(venue: str, *, profit_usd: float = 0.0, price: float = 0.5, contracts: float = 0.0) -> float:
    """Dispatch to the right venue fee model. Returns absolute USD fee."""
    v = (venue or "").lower()
    if v == "polymarket":
        return polymarket_fee(profit_usd)
    if v == "kalshi":
        return kalshi_fee_per_contract(price) * contracts
    # Unknown venue: be conservative, charge the higher-looking Polymarket model.
    return polymarket_fee(profit_usd)


def annualized_pct(edge_pct: float, days_to_resolution: float) -> float:
    """Simple (non-compounded) annualization of a one-shot edge."""
    if days_to_resolution is None or days_to_resolution <= 0:
        return edge_pct  # resolves immediately / unknown -> report as-is
    return edge_pct * 365.0 / days_to_resolution
