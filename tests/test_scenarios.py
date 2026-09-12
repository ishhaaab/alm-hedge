import pytest

from alm_hedge_lab.sample import bundled_market, sample_balance_sheet
from alm_hedge_lab.scenarios import Scenario, scenario_results, standard_scenarios


def test_scenario_changes_each_curve_node() -> None:
    curve = bundled_market().curve
    shocked = Scenario("test", (10, 20, 30, 40, 50)).apply(curve)
    assert (shocked.rates - curve.rates).tolist() == pytest.approx([0.001, 0.002, 0.003, 0.004, 0.005])


def test_parallel_increase_changes_surplus_by_revaluation() -> None:
    curve = bundled_market().curve
    balance_sheet = sample_balance_sheet()
    scenario = standard_scenarios(curve)[0]
    result = scenario_results(balance_sheet, curve, [scenario])[0]
    expected = (
        balance_sheet.values(scenario.apply(curve))["surplus"]
        - balance_sheet.values(curve)["surplus"]
    )
    assert result["change"] == pytest.approx(expected)


def test_standard_scenarios_match_curve_length() -> None:
    curve = bundled_market().curve
    assert all(len(item.shifts_bp) == len(curve.tenors) for item in standard_scenarios(curve))


def test_2008_replay_uses_full_year_fred_change() -> None:
    scenarios = {item.name: item for item in standard_scenarios(bundled_market().curve)}
    assert scenarios["2008 replay"].shifts_bp == (-212, -173, -166, -134, -166)


def test_standard_grid_covers_parallel_twist_and_key_rate_moves() -> None:
    scenarios = standard_scenarios(bundled_market().curve)
    assert len(scenarios) >= 10
    names = [item.name for item in scenarios]
    assert "Rates +50 bp" in names
    assert "Steepener +50%" in names
    assert "2Y +25 bp" in names
    assert "30Y -25 bp" in names


def test_key_rate_shocks_isolate_a_single_node() -> None:
    scenarios = {item.name: item for item in standard_scenarios(bundled_market().curve)}
    assert scenarios["5Y +25 bp"].shifts_bp == (0.0, 25.0, 0.0, 0.0, 0.0)
    assert scenarios["30Y -25 bp"].shifts_bp == (0.0, 0.0, 0.0, 0.0, -25.0)
