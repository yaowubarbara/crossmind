"""Smoke test — verifies all components work before submission."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config():
    import config
    assert config.PAIR == "BTC/USD"
    assert config.RSI_PERIOD == 14
    assert config.MAX_DRAWDOWN_PCT == 0.05
    print("  ✅ config")


def test_signal_generator():
    from signal_generator import compute_rsi, generate_signal
    rsi = compute_rsi([100, 102, 101, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87])
    assert 0 <= rsi <= 100
    print(f"  ✅ signal_generator (RSI={rsi})")


def test_portfolio():
    from portfolio import PortfolioState
    p = PortfolioState()
    assert p.total_value == 10000.0
    assert p.drawdown_pct == 0.0
    print("  ✅ portfolio")


def test_risk_manager():
    from risk_manager import RiskManager
    rm = RiskManager()
    decision = rm.evaluate(
        {"action": "BUY", "price": 67000, "volume": 0.01},
        {"drawdown_pct": 0.5, "consecutive_losses": 0},
    )
    assert decision.decision in ("APPROVE", "REFUSE")
    print(f"  ✅ risk_manager (fallback: {decision.decision})")


def test_trust_ledger():
    from trust_ledger import TrustLedger
    import tempfile
    tl = TrustLedger(ledger_dir=tempfile.mkdtemp())
    tl.record_execution(
        {"action": "BUY"}, {"drawdown": 0}, {"price": 67000},
        analyst_summary={"rsi": 27}, strategist_proposal={"action": "BUY"},
    )
    tl.record_refusal(
        {"action": "BUY"}, {"drawdown": 4.8}, "Too risky",
        analyst_summary={"rsi": 26}, strategist_proposal={"action": "BUY"},
    )
    assert tl.verify_chain()
    stats = tl.get_stats()
    assert stats["total_entries"] == 2
    assert stats["refusals"] == 1
    print(f"  ✅ trust_ledger (chain valid, {stats['total_entries']} entries)")


def test_gatekeeper():
    from gatekeeper import Gatekeeper
    gk = Gatekeeper()
    verdict = gk.evaluate([
        {"survived": True, "max_drawdown": 1.0, "pnl": -50, "total_trades": 3, "refusals": 2},
    ])
    assert isinstance(verdict.score, float)
    print(f"  ✅ gatekeeper (score={verdict.score})")


def test_adversary():
    from adversary import AdversaryAgent
    adv = AdversaryAgent()
    attack = adv.select_attack(
        {"capital": 9800, "drawdown_pct": 2, "consecutive_losses": 1, "win_rate": 40, "total_trades": 5},
        [], ["Scenario A", "Scenario B"],
    )
    assert "selected_scenario" in attack
    print(f"  ✅ adversary (attack: {attack['selected_scenario']})")


if __name__ == "__main__":
    print("\n  CrossMind Smoke Test")
    print("  " + "=" * 40)
    test_config()
    test_signal_generator()
    test_portfolio()
    test_risk_manager()
    test_trust_ledger()
    test_gatekeeper()
    test_adversary()
    print("  " + "=" * 40)
    print("  ✅ ALL TESTS PASSED\n")
