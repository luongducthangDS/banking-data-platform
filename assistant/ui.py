"""streamlit run assistant/ui.py   (calls the assistant API; ASSISTANT_API defaults to localhost:8003)"""
import os

import pandas as pd
import requests
import streamlit as st

API = os.getenv("ASSISTANT_API", "http://localhost:8003")
EXAMPLES = ["Tổng tiền gửi cuối tháng 12/1998 là bao nhiêu?",
            "Tỷ lệ vỡ nợ theo vùng, cao nhất trước",
            "So sánh tổng tiền vào giữa quý 3 và quý 4 năm 1998",
            "Phân khúc RFM nào có số dư bình quân cao nhất?"]

st.set_page_config(page_title="Banking Analytics Assistant", layout="wide")
st.title("Banking Analytics Assistant")
st.caption("Hỏi về dữ liệu ngân hàng (Berka, 1993–1998). Chỉ đọc, chỉ schema core và marts.")

q = st.text_input("Câu hỏi", placeholder=EXAMPLES[0])
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    if c.button(ex, use_container_width=True):
        q = ex

if q:
    with st.spinner("Đang truy vấn..."):
        r = requests.post(f"{API}/ask", json={"question": q}, timeout=120)
    if r.status_code != 200:
        st.error(r.json().get("detail", r.text))
    else:
        res = r.json()
        st.markdown(f"**Trả lời:** {res['answer']}")
        if res["status"] == "ok":
            df = pd.DataFrame(res["rows"], columns=res["columns"])
            chart = res.get("chart")
            if chart:
                data = df.set_index(chart["x"])[[chart["y"]]]
                (st.line_chart if chart["type"] == "line" else st.bar_chart)(data, color="#1F4E79")
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("SQL đã chạy"):
                st.code(res["sql"], language="sql")
        st.caption(f"{res['latency_ms']} ms · {len(res['attempts'])} lần sửa SQL")
