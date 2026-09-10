from alm_hedge_lab.hedge import HedgeTest
from alm_hedge_lab.reporting import assess_limits
from alm_hedge_lab.sample import bundled_market, sample_balance_sheet


def test_sample_book_records_long_end_limit_breach() -> None:
    breaches = assess_limits(sample_balance_sheet(), bundled_market().curve, [])
    assert any(item.measure == "10Y+ surplus PV01" for item in breaches)


def test_failed_hedge_test_appears_in_log() -> None:
    failed = HedgeTest("Dollar offset", 0.5, False, "80% to 125%")
    breaches = assess_limits(sample_balance_sheet(), bundled_market().curve, [failed])
    assert any(item.measure == "Dollar offset" for item in breaches)
