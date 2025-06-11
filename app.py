import streamlit as st
import pandas as pd
from io import BytesIO
from workalendar.europe import Russia
from datetime import datetime

st.set_page_config(page_title="Анализ поступивших запросов", layout="wide")
st.title("Анализ поступивших запросов")

uploaded_file = st.file_uploader("Загрузите Excel-файл с данными", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("Файл загружен. Нажмите 'Проанализировать' для обработки данных.")
    if st.button("Проанализировать"):
        cal = Russia()
        today = pd.Timestamp(datetime.now().date())
        result_rows = []
        for business_id, group in df.groupby("business_id"):
            # 1. Найти строку, где stage_to == "2.1 Анализ целесообразности" с самой последней датой ts_from
            stage_21 = group[group["stage_to"] == "2.1 Анализ целесообразности"]
            if not stage_21.empty:
                idx_21 = stage_21["ts_from"].idxmax()
                row_21 = group.loc[idx_21]
                ts_from_21 = pd.to_datetime(row_21["ts_from"], errors="coerce")
                plan_pub_date = cal.add_working_days(ts_from_21, 21)
                plan_pub_date = pd.Timestamp(plan_pub_date)
            else:
                plan_pub_date = pd.NaT
            # 2. Найти строку с самой последней датой ts_from
            idx_last = group["ts_from"].idxmax()
            row_last = group.loc[idx_last]
            ts_from_last = pd.to_datetime(row_last["ts_from"], errors="coerce")
            # 3. Посчитать количество рабочих дней между today и ts_from_last
            if pd.notnull(ts_from_last):
                days_in_work = cal.get_working_days_delta(ts_from_last, today)
            else:
                days_in_work = None
            # 4. Собрать строку результата
            result_rows.append({
                "business_id": business_id,
                "created_at": pd.to_datetime(row_last.get("created_at", None), errors="coerce"),
                "Плановая дата публикации": plan_pub_date,
                "Дней в работе": days_in_work,
                "form_type_report": row_last.get("form_type_report", None),
                "report_code": row_last.get("report_code", None),
                "report_name": row_last.get("report_name", None),
                "current_stage": row_last.get("current_stage", None),
                "ts_from": pd.to_datetime(row_last.get("ts_from", None), errors="coerce"),
                "analyst": row_last.get("analyst", None),
                "request_owner": row_last.get("request_owner", None),
                "request_owner_ssp": row_last.get("request_owner_ssp", None)
            })
        df_result = pd.DataFrame(result_rows)
        # Форматирование дат
        for col in ["created_at", "ts_from", "Плановая дата публикации"]:
            df_result[col] = df_result[col].dt.strftime("%d.%m.%Y").fillna("")
        # Добавить нумерацию
        df_result.insert(0, "№", range(1, len(df_result) + 1))
        st.dataframe(df_result, use_container_width=True)
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()
        st.download_button(
            label="Скачать в файл",
            data=to_excel(df_result),
            file_name="result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
