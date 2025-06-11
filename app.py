import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Анализ запросов", layout="wide")
st.title("Анализ запросов и стадий их рассмотрения")

uploaded_file = st.file_uploader("Загрузите исходный файл (CSV или Excel)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    st.success("Файл загружен. Нажмите 'Проанализировать' для обработки данных.")
    if st.button("Проанализировать"):
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values("created_at", ascending=False)
        df_unique = df.drop_duplicates(subset=["business_id"], keep="first")
        today = datetime.datetime.now().date()
        df_unique["ts_from"] = pd.to_datetime(df_unique["ts_from"], errors="coerce")
        df_unique["дней в работе"] = (pd.Timestamp(today) - df_unique["ts_from"]).dt.days
        columns = [
            "business_id", "created_at", "дней в работе", "form_type_report", "report_code", "report_name",
            "current_stage", "ts_from", "analyst", "request_owner", "request_owner_ssp"
        ]
        df_result = df_unique[columns]
        with st.expander("Фильтры"):
            for col in columns:
                unique_vals = df_result[col].dropna().unique()
                if len(unique_vals) < 100:
                    selected = st.multiselect(f"{col}", unique_vals, default=unique_vals)
                    df_result = df_result[df_result[col].isin(selected)]
        search_col = st.text_input("Поиск по report_code или business_id")
        if search_col:
            df_result = df_result[df_result["report_code"].astype(str).str.contains(search_col) | df_result["business_id"].astype(str).str.contains(search_col)]
        df_result["created_at"] = pd.to_datetime(df_result["created_at"], errors="coerce").dt.strftime("%d.%m.%Y")
        df_result["ts_from"] = pd.to_datetime(df_result["ts_from"], errors="coerce").dt.strftime("%d.%m.%Y")
        st.dataframe(df_result, use_container_width=True)
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()
        st.download_button(
            label="Скачать Xlsx файл",
            data=to_excel(df_result),
            file_name="result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
