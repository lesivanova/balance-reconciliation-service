
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

# Инициализация
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

# 6 вкладок
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Калькулятор", "Результаты", "Графики", "🏭 Модель завода", "💾 Данные", "🔍 Грубые ошибки"])

# ================================================================
# ВКЛАДКА 1: КАЛЬКУЛЯТОР
# ================================================================
with tab1:
    st.header("Готовые примеры")
    
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
                    {"id": "X8", "name": "Поток 8", "measured_value": 66.666, "tolerance": 0.667}
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
            st.success("✅ Пример 3 загружен")
    
    st.markdown("---")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🧮 Рассчитать баланс", type="primary", use_container_width=True):
            if st.session_state.data:
                with st.spinner("Расчет..."):
                    r = requests.post(f"{API_URL}/api/v1/reconcile", json=st.session_state.data)
                    if r.status_code == 200:
                        st.session_state.result = r.json()
                        st.success("✅ Баланс рассчитан!")
                    else:
                        st.error(f"Ошибка: {r.status_code}")
            else:
                st.warning("Сначала выберите пример")
    
    with col_btn2:
        if st.button("🔍 Найти грубые ошибки", use_container_width=True):
            if st.session_state.data:
                with st.spinner("Поиск..."):
                    r = requests.post(f"{API_URL}/api/v1/detect-errors", json=st.session_state.data)
                    if r.status_code == 200:
                        st.session_state.errors = r.json()
                        if st.session_state.errors.get('has_errors'):
                            st.error(st.session_state.errors['message'])
                        else:
                            st.success(st.session_state.errors['message'])
                    else:
                        st.error(f"Ошибка: {r.status_code}")
            else:
                st.warning("Сначала выберите пример")

# ================================================================
# ВКЛАДКА 2: РЕЗУЛЬТАТЫ
# ================================================================
with tab2:
    if st.session_state.result:
        df = pd.DataFrame(st.session_state.result['balanced_flows'])
        st.dataframe(df, use_container_width=True)
        
        if st.session_state.result.get('global_test'):
            st.metric("Глобальный тест (GTst)", f"{st.session_state.result['global_test']:.4f}")
    else:
        st.info("Нет результатов. Нажмите 'Рассчитать баланс'")

# ================================================================
# ВКЛАДКА 3: ГРАФИКИ
# ================================================================
with tab3:
    if st.session_state.result:
        df = pd.DataFrame(st.session_state.result['balanced_flows'])
        fig = go.Figure()
        fig.add_trace(go.Bar(name="📊 Измерено", x=df['name'], y=df['original_value'], marker_color='lightblue'))
        fig.add_trace(go.Bar(name="✅ Сбалансировано", x=df['name'], y=df['balanced_value'], marker_color='lightgreen'))
        fig.update_layout(barmode='group', height=500)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Нет данных для отображения")

# ================================================================
# ВКЛАДКА 4: МОДЕЛЬ ЗАВОДА
# ================================================================
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
    else:
        st.info("Нажмите 'Загрузить модели'")

# ================================================================
# ВКЛАДКА 5: ДАННЫЕ ИЗМЕРЕНИЙ
# ================================================================
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
                    format_func=lambda x: f"{x['period_name']} ({x['timestamp'][:10]})"
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
                            st.success("✅ Баланс рассчитан по данным из БД!")
                        else:
                            st.error(f"Ошибка: {r.status_code}")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
    else:
        st.info("Сначала загрузите модели на вкладке 'Модель завода'")

# ================================================================
# ВКЛАДКА 6: ГРУБЫЕ ОШИБКИ
# ================================================================
with tab6:
    st.header("🔍 Грубые ошибки в измерениях")
    
    if st.session_state.errors:
        err = st.session_state.errors
        
        if err.get('has_errors'):
            st.error("🚨 ОБНАРУЖЕНЫ ГРУБЫЕ ОШИБКИ!")
            
            suspicious = err.get('suspicious_flows', [])
            for flow in suspicious:
                st.markdown("---")
                st.subheader(f"🔴 Поток {flow['id']}: {flow['name']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📊 Показание датчика", f"{flow['measured_value']:.3f}")
                    st.metric("⚙️ Допустимая погрешность", f"±{flow['tolerance']:.3f}")
                with col2:
                    correct_val = flow.get('balanced_value', flow['measured_value'] * 0.1)
                    st.metric("✅ Должно быть примерно", f"{correct_val:.3f}")
                    if correct_val != 0:
                        ratio = flow['measured_value'] / correct_val
                        st.metric("📈 Превышение", f"в {ratio:.0f} раз")
                
                st.warning(f"💡 Вероятная проблема: датчик на потоке {flow['id']} показывает значение {flow['measured_value']:.1f}, что значительно выше нормы!")
        else:
            st.success(f"✅ {err['message']}")
    else:
        st.info("📌 Нажмите кнопку 'Найти грубые ошибки' в калькуляторе")

