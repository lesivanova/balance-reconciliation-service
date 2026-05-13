import streamlit as st
import requests
import pandas as pd
import os
import plotly.graph_objects as go
import json

API_URL = os.environ.get('API_URL', 'http://backend-service:8000')
DATABASE_SERVICE_URL = os.environ.get('DATABASE_SERVICE_URL', 'http://database-service:8001')

st.set_page_config(layout="wide")
st.title("⚖️ Сведение материального баланса")

# Инициализация session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'result' not in st.session_state:
    st.session_state.result = None
if 'errors' not in st.session_state:
    st.session_state.errors = None
if 'models' not in st.session_state:
    st.session_state.models = []
if 'periods' not in st.session_state:
    st.session_state.periods = []

# Создаем вкладки
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Калькулятор", "Результаты", "Графики", "🏭 Модель завода", "💾 Данные", "🔍 Грубые ошибки"])

# ========== КАЛЬКУЛЯТОР ==========
with tab1:
    st.header("📌 Готовые примеры")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Пример 1", use_container_width=True):
            st.session_state.data = {
                "flows": [
                    {"id": "X1", "name": "Входной поток", "measured_value": 10.005, "tolerance": 0.200},
                    {"id": "X2", "name": "Поток 2", "measured_value": 3.033, "tolerance": 0.121},
                    {"id": "X3", "name": "Поток 3", "measured_value": 6.831, "tolerance": 0.683},
                    {"id": "X4", "name": "Поток 4", "measured_value": 1.985, "tolerance": 0.040},
                    {"id": "X5", "name": "Поток 5", "measured_value": 5.093, "tolerance": 0.102},
                    {"id": "X6", "name": "Поток 6", "measured_value": 4.057, "tolerance": 0.081},
                    {"id": "X7", "name": "Поток 7", "measured_value": 0.991, "tolerance": 0.020}
                ],
                "nodes": [
                    {"id": "N1", "name": "Узел 1", "equations": [
                        {"flow_id": "X1", "sign": 1}, {"flow_id": "X2", "sign": -1}, {"flow_id": "X3", "sign": -1}
                    ]},
                    {"id": "N2", "name": "Узел 2", "equations": [
                        {"flow_id": "X3", "sign": 1}, {"flow_id": "X4", "sign": -1}, {"flow_id": "X5", "sign": -1}
                    ]},
                    {"id": "N3", "name": "Узел 3", "equations": [
                        {"flow_id": "X5", "sign": 1}, {"flow_id": "X6", "sign": -1}, {"flow_id": "X7", "sign": -1}
                    ]}
                ],
                "constraints": []
            }
            st.session_state.result = None
            st.session_state.errors = None
            st.success("✅ Пример 1 загружен")
    
    with col2:
        if st.button("📊 Пример 2", use_container_width=True):
            st.session_state.data = {
                "flows": [
                    {"id": "X1", "name": "Входной поток", "measured_value": 10.005, "tolerance": 0.200},
                    {"id": "X2", "name": "Поток 2", "measured_value": 3.033, "tolerance": 0.121},
                    {"id": "X3", "name": "Поток 3", "measured_value": 6.831, "tolerance": 0.683},
                    {"id": "X4", "name": "Поток 4", "measured_value": 1.985, "tolerance": 0.040},
                    {"id": "X5", "name": "Поток 5", "measured_value": 5.093, "tolerance": 0.102},
                    {"id": "X6", "name": "Поток 6", "measured_value": 4.057, "tolerance": 0.081},
                    {"id": "X7", "name": "Поток 7", "measured_value": 0.991, "tolerance": 0.020},
                    {"id": "X8", "name": "Поток 8", "measured_value": 6.666, "tolerance": 0.667}
                ],
                "nodes": [
                    {"id": "N1", "name": "Узел 1", "equations": [
                        {"flow_id": "X1", "sign": 1}, {"flow_id": "X2", "sign": -1}, {"flow_id": "X3", "sign": -1}
                    ]},
                    {"id": "N2", "name": "Узел 2", "equations": [
                        {"flow_id": "X3", "sign": 1}, {"flow_id": "X4", "sign": -1}, {"flow_id": "X5", "sign": -1}
                    ]},
                    {"id": "N3", "name": "Узел 3", "equations": [
                        {"flow_id": "X5", "sign": 1}, {"flow_id": "X6", "sign": -1}, {"flow_id": "X7", "sign": -1}, {"flow_id": "X8", "sign": -1}
                    ]}
                ],
                "constraints": []
            }
            st.session_state.result = None
            st.session_state.errors = None
            st.success("✅ Пример 2 загружен")
    
    with col3:
        if st.button("📊 Пример 3", use_container_width=True):
            st.session_state.data = {
                "flows": [
                    {"id": "X1", "name": "Входной поток", "measured_value": 10.005, "tolerance": 0.200},
                    {"id": "X2", "name": "Поток 2", "measured_value": 3.033, "tolerance": 0.121},
                    {"id": "X3", "name": "Поток 3", "measured_value": 6.831, "tolerance": 0.683},
                    {"id": "X4", "name": "Поток 4", "measured_value": 1.985, "tolerance": 0.040},
                    {"id": "X5", "name": "Поток 5", "measured_value": 5.093, "tolerance": 0.102},
                    {"id": "X6", "name": "Поток 6", "measured_value": 4.057, "tolerance": 0.081},
                    {"id": "X7", "name": "Поток 7", "measured_value": 0.991, "tolerance": 0.020},
                    {"id": "X8", "name": "Поток 8", "measured_value": 6.666, "tolerance": 0.667}
                ],
                "nodes": [
                    {"id": "N1", "name": "Узел 1", "equations": [
                        {"flow_id": "X1", "sign": 1}, {"flow_id": "X2", "sign": -1}, {"flow_id": "X3", "sign": -1}
                    ]},
                    {"id": "N2", "name": "Узел 2", "equations": [
                        {"flow_id": "X3", "sign": 1}, {"flow_id": "X4", "sign": -1}, {"flow_id": "X5", "sign": -1}
                    ]},
                    {"id": "N3", "name": "Узел 3", "equations": [
                        {"flow_id": "X5", "sign": 1}, {"flow_id": "X6", "sign": -1}, {"flow_id": "X7", "sign": -1}, {"flow_id": "X8", "sign": -1}
                    ]}
                ],
                "constraints": [
                    {"terms": [{"flow_id": "X1", "coefficient": 1}, {"flow_id": "X2", "coefficient": -10}], "rhs": 0}
                ]
            }
            st.session_state.result = None
            st.session_state.errors = None
            st.success("✅ Пример 3 загружен")
    
    st.markdown("---")
    st.subheader("📂 Или загрузи свой JSON файл")
    
    uploaded_file = st.file_uploader("Выберите JSON файл", type=['json'])
    if uploaded_file is not None:
        try:
            user_data = json.load(uploaded_file)
            if "flows" in user_data and "nodes" in user_data:
                st.session_state.data = user_data
                st.session_state.result = None
                st.session_state.errors = None
                st.success(f"✅ Загружено: {len(user_data['flows'])} потоков")
        except Exception as e:
            st.error(f"Ошибка: {e}")
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🧮 Рассчитать баланс", type="primary", use_container_width=True):
            if st.session_state.data:
                with st.spinner("Расчет..."):
                    try:
                        r = requests.post(f"{API_URL}/api/v1/reconcile", json=st.session_state.data, timeout=30)
                        if r.status_code == 200:
                            st.session_state.result = r.json()
                            st.success("✅ Баланс рассчитан!")
                        else:
                            st.error(f"Ошибка: {r.status_code}")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                st.warning("Сначала выберите пример или загрузите файл")
    
    with col_btn2:
        if st.button("🔍 Найти грубые ошибки", use_container_width=True):
            if st.session_state.data:
                with st.spinner("Поиск ошибок..."):
                    try:
                        r = requests.post(f"{API_URL}/api/v1/detect-errors", json=st.session_state.data, timeout=30)
                        if r.status_code == 200:
                            st.session_state.errors = r.json()
                            if st.session_state.errors.get('has_errors'):
                                st.error(f"❌ {st.session_state.errors['message']}")
                            else:
                                st.success(f"✅ {st.session_state.errors['message']}")
                        else:
                            st.error(f"Ошибка: {r.status_code}")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                st.warning("Сначала выберите пример или загрузите файл")

# ========== РЕЗУЛЬТАТЫ ==========
with tab2:
    if st.session_state.result and st.session_state.result.get('status') == 'success':
        df = pd.DataFrame(st.session_state.result['balanced_flows'])
        st.dataframe(df, use_container_width=True)
        
        st.subheader("📊 Глобальный тест")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("GTst", f"{st.session_state.result.get('global_test', 0):.5f}")
        with col_b:
            gt_orig = st.session_state.result.get('global_test_original', 0)
            gt_limit = st.session_state.result.get('global_test_limit', 0)
            st.metric("χ²", f"{gt_orig:.3f} / {gt_limit:.3f}")
        with col_c:
            if st.session_state.result.get('is_consistent'):
                st.success("✅ Данные согласованы")
            else:
                st.error("❌ Данные противоречат модели")
    else:
        st.info("Нет результатов. Выберите пример и нажмите 'Рассчитать баланс'")

# ========== ГРАФИКИ ==========
with tab3:
    if st.session_state.result and st.session_state.result.get('status') == 'success':
        df = pd.DataFrame(st.session_state.result['balanced_flows'])
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Измерено", x=df['name'], y=df['original_value'], marker_color='lightblue'))
        fig.add_trace(go.Bar(name="Сбалансировано", x=df['name'], y=df['balanced_value'], marker_color='lightgreen'))
        fig.update_layout(title="Сравнение измеренных и сбалансированных значений", barmode='group', height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных для отображения")

# ========== МОДЕЛЬ ЗАВОДА ==========
with tab4:
    st.header("🏭 Модель завода")
    
    if st.button("📥 Загрузить модели из базы данных"):
        try:
            r = requests.get(f"{DATABASE_SERVICE_URL}/api/plant-models")
            if r.status_code == 200:
                st.session_state.models = r.json()
                st.success(f"Загружено {len(st.session_state.models)} моделей")
        except Exception as e:
            st.error(f"Ошибка: {e}")
    
    if st.session_state.models:
        selected_model = st.selectbox(
            "Выберите модель завода",
            options=st.session_state.models,
            format_func=lambda x: f"{x['name']} (v{x['version']})"
        )
        
        if selected_model:
            st.subheader(f"📄 {selected_model['name']}")
            st.write(f"**Описание:** {selected_model.get('description', 'Нет описания')}")
            
            with st.expander("📊 Потоки"):
                st.json(selected_model['flows'])
            with st.expander("🔗 Узлы"):
                st.json(selected_model['nodes'])
            
            if st.button("📋 Использовать эту модель"):
                st.session_state.data = {
                    "flows": selected_model['flows'],
                    "nodes": selected_model['nodes'],
                    "constraints": selected_model.get('constraints', [])
                }
                st.success("Модель загружена в калькулятор!")

# ========== ДАННЫЕ ==========
with tab5:
    st.header("💾 Данные измерений")
    
    if st.session_state.models:
        selected_model = st.selectbox(
            "Выберите модель",
            options=st.session_state.models,
            format_func=lambda x: x['name'],
            key="model_for_data"
        )
        
        if selected_model:
            if st.button("📊 Загрузить периоды"):
                try:
                    r = requests.get(f"{DATABASE_SERVICE_URL}/api/measurements/{selected_model['id']}")
                    if r.status_code == 200:
                        st.session_state.periods = r.json()
                        st.success(f"Загружено {len(st.session_state.periods)} периодов")
                except Exception as e:
                    st.error(f"Ошибка: {e}")
            
            if st.session_state.periods:
                selected_period = st.selectbox(
                    "Выберите период",
                    options=st.session_state.periods,
                    format_func=lambda x: f"{x['period_name']}"
                )
                
                if selected_period and st.button("🧮 Рассчитать по данным из БД"):
                    try:
                        reconcile_data = {
                            "plant_model_id": selected_model['id'],
                            "period_name": selected_period['period_name']
                        }
                        r = requests.post(f"{DATABASE_SERVICE_URL}/api/reconcile", json=reconcile_data, timeout=30)
                        if r.status_code == 200:
                            st.session_state.result = r.json()
                            st.success("✅ Баланс рассчитан!")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")

# ========== ГРУБЫЕ ОШИБКИ (GED) ==========
with tab6:
    st.header("🔍 Поиск грубых ошибок (GED)")
    
    if st.session_state.get('errors'):
        errors = st.session_state.errors
        
        if errors.get('has_errors'):
            st.error(f"⚠️ {errors['message']}")
            
            suspicious = errors.get('suspicious_flows', [])
            if suspicious:
                st.subheader("📊 Подозрительные измерения")
                df_suspicious = pd.DataFrame(suspicious)
                st.dataframe(df_suspicious, use_container_width=True)
                
                st.subheader("📈 Детали подозрительных потоков")
                for flow in suspicious:
                    st.write(f"**{flow['name']} ({flow['id']})**")
                    st.write(f"- Измеренное значение: {flow['measured_value']}")
                    st.write(f"- Допуск: ±{flow['tolerance']}")
                    st.write(f"- Стандартизированный остаток: {flow.get('standardized_residual', 0):.3f}")
                    progress = min(abs(flow.get('standardized_residual', 0)) / 5, 1.0)
                    st.progress(progress)
        else:
            st.success(f"✅ {errors['message']}")
        
        with st.expander("📋 Детали итераций"):
            details = errors.get('details', {})
            iterations = details.get('iteration_details', [])
            for it in iterations:
                st.write(f"**Итерация {it['iteration']}**")
                st.write(f"- GTst: {it['gtst']:.4f}")
                st.write(f"- {it['message']}")
    else:
        st.info("ℹ️ Нажмите 'Найти грубые ошибки' в калькуляторе для анализа данных")
