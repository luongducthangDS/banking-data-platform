# Rules

## Bất biến
- Không bịa số. Mọi số trong README/báo cáo/CV phải sinh từ code trong repo và chạy lại được.
- Luôn ghi rõ phần nào là giả lập (tách nguồn, lỗi API, switch feed, lỗi cấy). Dữ liệu gốc Berka là thật, đã ẩn danh.
- Load phải idempotent: chạy lại cùng một khoảng không được tạo dòng trùng. Có test cho điều này.
- Assistant chỉ được chạy SQL qua user `analyst_ro` (chỉ SELECT trên `core`, `marts`), trong transaction read-only, có `statement_timeout`. Không bao giờ chạy SQL của LLM bằng user ghi.
- Không commit `data/raw`, `landing/`, `.env`, key API.

## Quy ước code
- Python 3.11, hàm ngắn, không class khi hàm là đủ. Log bằng `logging`, không `print` trong pipeline.
- SQL biến đổi nằm trong dbt; Python chỉ extract/load/kiểm tra.
- dbt: `stg_` cho staging, `dim_`/`fact_`/`bridge_` cho core, `mart_` cho marts. Mỗi khoá chính có test `unique` + `not_null`.
- Test chạy bằng `.venv/Scripts/python -m pytest -q`; test cần Postgres tự skip khi không kết nối được.
- Windows console: chạy script có tiếng Việt với `PYTHONUTF8=1`.
