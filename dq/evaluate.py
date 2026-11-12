"""Score DQ rules and reconciliation against the injected answer key; write reports/dq_eval.md.

Each injected defect has one designated detector. Recall = injected rows that detector flagged.
Precision of a detector = flagged rows that carry ANY injected label (a row can legitimately trip
two detectors, e.g. a negative amount is both invalid and an amount break). Unlabelled flags on
the switch side are false positives; flags on core data have no labels: they are findings in the
real Berka data, listed separately.
"""
from pathlib import Path

import pandas as pd
import psycopg

from pipeline.extract_load import DSN

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "dq_eval.md"

DETECTOR = {  # injected issue -> (source, rule/break type, key column in labels)
    "null_account": ("dq", "SW-COMP-01", "switch_ref"),
    "duplicate": ("dq", "SW-UNIQ-01", "switch_ref"),
    "bad_date_format": ("dq", "SW-VAL-01", "switch_ref"),
    "negative_amount": ("dq", "SW-VAL-02", "switch_ref"),
    "bad_currency": ("dq", "SW-VAL-03", "switch_ref"),
    "missing_in_switch": ("recon", "missing_in_switch", "core_ref"),
    "missing_in_core": ("recon", "missing_in_core", "switch_ref"),
    "amount_mismatch": ("recon", "amount_mismatch", "switch_ref"),
    "date_mismatch": ("recon", "date_mismatch", "switch_ref"),
}


def main() -> None:
    labels = pd.read_csv(ROOT / "landing" / "switch" / "_labels.csv", dtype=str)
    with psycopg.connect(DSN) as conn:
        dq = pd.DataFrame(conn.execute("select rule_id, record_key from dq.error_records").fetchall(),
                          columns=["rule", "key"])
        rc = pd.DataFrame(conn.execute(
            "select break_type, switch_ref, core_transaction_id::text from recon.breaks").fetchall(),
            columns=["rule", "switch_ref", "core_ref"])
        core_rules = conn.execute("""select rule_id, description, sum(unexpected_count)::int, sum(element_count)::bigint
            from dq.check_results where rule_id like 'CORE-%' group by 1, 2 order by 1""").fetchall()
        n_months = conn.execute("select count(distinct interval_start) from dq.check_results").fetchone()[0]

    labelled_sw, labelled_core = set(labels.switch_ref), set(labels.core_ref)
    rows = []
    for issue, (src, rule, key) in DETECTOR.items():
        truth = set(labels.loc[labels.issue == issue, key])
        if src == "dq":
            flagged = set(dq.loc[dq.rule == rule, "key"])
        else:
            flagged = set(rc.loc[rc.rule == rule, "core_ref" if key == "core_ref" else "switch_ref"])
        hit = truth & flagged
        valid = flagged & (labelled_core if key == "core_ref" else labelled_sw)
        rows.append(dict(injected=issue, detector=rule, injected_rows=len(truth), detected=len(hit),
                         recall=round(len(hit) / len(truth), 4) if truth else None,
                         flagged=len(flagged), precision=round(len(valid) / len(flagged), 4) if flagged else None))
    res = pd.DataFrame(rows)

    t1 = set(labels.loc[labels.issue == "settlement_t1", "switch_ref"])
    t1_flagged = t1 & set(rc.switch_ref)
    core = pd.DataFrame(core_rules, columns=["rule", "description", "violations", "rows_checked"])

    text = f"""# Đánh giá Data Quality & Reconciliation

Lỗi trong file switch là **giả lập** (`dq/inject.py`, seed 42), có file đáp án. Dữ liệu core là Berka thật.
Chạy trên {n_months} tháng (`python -m dq.cli all 1993-01-01 1999-01-01`), rồi `python -m dq.evaluate`.

## Lỗi cấy: phát hiện được bao nhiêu

{res.to_markdown(index=False)}

Tổng: phát hiện {int(res.detected.sum())}/{int(res.injected_rows.sum())} dòng lỗi cấy.

**Đối chứng âm:** {len(t1)} giao dịch có ngày giá trị trễ 1 ngày (T+1, hợp lệ); bị báo nhầm là break: {len(t1_flagged)}.

## Phát hiện trên dữ liệu thật (core, không có nhãn)

{core.to_markdown(index=False)}

- `CORE-VAL-01`: bút toán "lãi phạt" (`SANKC. UROK`) có số tiền 0,00 trong dữ liệu gốc. Nên loại ở staging hoặc hỏi lại hệ thống nguồn.
- `CORE-CONS-02`: đều là ngày cuối tháng có cả cộng lãi lẫn phí/lãi phạt; lệch khoảng 0,20 CZK = hai lần làm tròn 0,10.
  Không phải mất giao dịch. Nới dung sai lên 0,20 cho ngày có ≥ 2 bút toán ngân hàng tự sinh sẽ hết cảnh báo giả này.
- `CORE-COMP-01`: 1 giao dịch liên ngân hàng không ghi ngân hàng đối tác.

Mọi dòng vi phạm có trong `dq.error_records` và qua API `GET /dq/errors?rule_id=...`.
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
