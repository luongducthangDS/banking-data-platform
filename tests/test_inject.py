import pandas as pd

from dq.inject import build


def _trans(n=20000):
    return pd.DataFrame({
        "trans_id": [str(i) for i in range(n)], "account_id": "1", "date": "950610",
        "operation": ["VYBER KARTOU", "PREVOD NA UCET", "VKLAD", "PREVOD Z UCTU"] * (n // 4),
        "amount": "100.00"})


def test_only_switch_operations_and_defects_match_labels():
    sw, labels = build(_trans())
    assert set(sw.channel) == {"CARD", "ACH"}                       # cash deposits never reach the switch
    issues = labels.set_index("switch_ref").issue
    missing = set(labels.loc[labels.issue == "missing_in_switch", "switch_ref"])
    assert not missing & set(sw.switch_ref)                         # dropped rows are really gone
    dup_refs = set(labels.loc[labels.issue == "duplicate", "switch_ref"])
    assert (sw.switch_ref.isin(dup_refs).sum()) == 2 * len(dup_refs)  # sent twice
    neg = sw[sw.switch_ref.isin(issues[issues == "negative_amount"].index)]
    assert (neg.amount.astype(float) < 0).all()
    assert (sw.loc[sw.switch_ref.isin(issues[issues == "bad_currency"].index), "currency"] == "EUR").all()
    assert labels.core_ref[labels.issue == "missing_in_core"].astype(int).min() >= 900000000


def test_deterministic():
    a, _ = build(_trans(), seed=7)
    b, _ = build(_trans(), seed=7)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b.reset_index(drop=True))
