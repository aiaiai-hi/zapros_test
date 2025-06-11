import streamlit as st
import pandas as pd
from io import BytesIO
from workalendar.europe import Russia
from datetime import datetime

st.set_page_config(page_title="Анализ поступивших запросов", layout="wide")

def display_results(df):
    """Отображение результатов с фильтрами и поиском"""
    # Строка поиска
    st.subheader("🔎 Поиск")
    search_query = st.text_input(
        "Поиск по номеру отчета (Код отчета) или business_id:",
        placeholder="Введите номер отчета или business_id..."
    )

    # Применяем поиск
    filtered_df = df.copy()
    if search_query:
        search_mask = (
            filtered_df['Код отчета'].astype(str).str.contains(search_query, case=False, na=False) |
            filtered_df['business_id'].astype(str).str.contains(search_query, case=False, na=False)
        )
        filtered_df = filtered_df[search_mask]

    # Фильтры
    st.subheader("🔧 Фильтры")
    col1, col2, col3, col4 = st.columns(4)
    # Для фильтров всегда используем уникальные значения из исходного df!
    with col1:
        form_types = ['Все'] + sorted(df['Тип отчета'].dropna().unique().tolist())
        selected_form_type = st.selectbox("Тип формы отчета:", form_types)
        analysts = ['Все'] + sorted(df['Аналитик'].dropna().unique().tolist())
        selected_analyst = st.selectbox("Аналитик:", analysts)
    with col2:
        stages = ['Все'] + sorted(df['Текущий этап'].dropna().unique().tolist())
        selected_stage = st.selectbox("Текущий этап:", stages)
        owners = ['Все'] + sorted(df['Владелец запроса'].dropna().unique().tolist())
        selected_owner = st.selectbox("Владелец запроса:", owners)
    with col3:
        owner_ssps = ['Все'] + sorted(df['ССП Владелец запроса'].dropna().unique().tolist())
        selected_owner_ssp = st.selectbox("ССП Владелец запроса:", owner_ssps)
        min_days = st.number_input("Мин. дней в работе:", min_value=0, value=0)
    with col4:
        max_days = st.number_input("Макс. дней в работе:", min_value=0, value=1000)
        if st.button("🔄 Сбросить фильтры"):
            st.rerun()
    # Применяем фильтры
    if selected_form_type != 'Все':
        filtered_df = filtered_df[filtered_df['Тип отчета'] == selected_form_type]
    if selected_stage != 'Все':
        filtered_df = filtered_df[filtered_df['Текущий этап'] == selected_stage]
    if selected_analyst != 'Все':
        filtered_df = filtered_df[filtered_df['Аналитик'] == selected_analyst]
    if selected_owner != 'Все':
        filtered_df = filtered_df[filtered_df['Владелец запроса'] == selected_owner]
    if selected_owner_ssp != 'Все':
        filtered_df = filtered_df[filtered_df['ССП Владелец запроса'] == selected_owner_ssp]
    filtered_df = filtered_df[
        (filtered_df['Дней в работе'] >= min_days) & 
        (filtered_df['Дней в работе'] <= max_days)
    ]
    # Статистика
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Всего записей", len(df))
    with col2:
        st.metric("🔍 После фильтрации", len(filtered_df))
    with col3:
        if len(filtered_df) > 0:
            avg_days = filtered_df['Дней в работе'].mean()
            st.metric("📅 Среднее дней в работе", f"{avg_days:.1f}")
        else:
            st.metric("📅 Среднее дней в работе", "0")
    with col4:
        if len(filtered_df) > 0:
            max_days_value = filtered_df['Дней в работе'].max()
            st.metric("⏰ Максимум дней", max_days_value)
        else:
            st.metric("⏰ Максимум дней", "0")
    # --- Заголовок перед таблицей ---
    st.subheader("🔍 Результаты анализа")
    # Удаляем колонку № если есть
    table_df = filtered_df.copy()
    if "№" in table_df.columns:
        table_df = table_df.drop(columns=["№"])
    # Центрируем business_id
    st.dataframe(
        table_df.style.set_properties(subset=["business_id"], **{'text-align': 'center'}),
        use_container_width=True
    )
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()
    st.download_button(
        label="Скачать в файл",
        data=to_excel(table_df),
        file_name="result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
            stage_21 = group[group["stage_to"] == "2.1 Анализ целесообразности"]
            if not stage_21.empty:
                idx_21 = stage_21["ts_from"].idxmax()
                row_21 = group.loc[idx_21]
                ts_from_21 = pd.to_datetime(row_21["ts_from"], errors="coerce")
                plan_pub_date = cal.add_working_days(ts_from_21, 21)
                plan_pub_date = pd.Timestamp(plan_pub_date)
            else:
                plan_pub_date = pd.NaT
            idx_last = group["ts_from"].idxmax()
            row_last = group.loc[idx_last]
            ts_from_last = pd.to_datetime(row_last["ts_from"], errors="coerce")
            if pd.notnull(ts_from_last):
                days_in_work = cal.get_working_days_delta(ts_from_last, today)
            else:
                days_in_work = None
            result_rows.append({
                "business_id": business_id,
                "Создан": pd.to_datetime(row_last.get("created_at", None), errors="coerce").strftime("%d.%m.%Y") if pd.notnull(row_last.get("created_at", None)) else "",
                "Плановая дата": plan_pub_date.strftime("%d.%m.%Y") if pd.notnull(plan_pub_date) else "",
                "Дней в работе": days_in_work,
                "Тип отчета": row_last.get("form_type_report", None),
                "Код отчета": row_last.get("report_code", None),
                "Название отчета": row_last.get("report_name", None),
                "Текущий этап": row_last.get("current_stage", None),
                "Поступил на этап": pd.to_datetime(row_last.get("ts_from", None), errors="coerce").strftime("%d.%m.%Y") if pd.notnull(row_last.get("ts_from", None)) else "",
                "Аналитик": row_last.get("analyst", None),
                "Владелец запроса": row_last.get("request_owner", None),
                "ССП Владелец запроса": row_last.get("request_owner_ssp", None)
            })
        df_result = pd.DataFrame(result_rows)
        display_results(df_result)
