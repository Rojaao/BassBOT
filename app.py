import streamlit as st
import asyncio
from logic import start_bot

st.set_page_config(page_title="Deriv Bot - Over 3", layout="wide")
st.title("🤖 Deriv Bot - Estratégia Over 3 (Completo)")

token = st.text_input("🔑 Token da Deriv", type="password")
stake = st.number_input("💵 Valor Inicial da Entrada", min_value=0.35, value=1.00, step=0.01)
threshold = st.number_input("📉 Mínimo de dígitos < 4 para entrar", min_value=1, max_value=8, value=3)
take_profit = st.number_input("🎯 Meta de Lucro Total ($)", min_value=1.0, value=10.0, step=0.5)
stop_loss = st.number_input("🛑 Limite de Perda Total ($)", min_value=1.0, value=10.0, step=0.5)
multiplicador = st.number_input("🔁 Fator de Multiplicação após 2 perdas", min_value=1.0, value=1.68, step=0.01)

start_button = st.button("▶️ Iniciar Robô")
stop_button = st.button("⏹️ Parar Robô")

log_area = st.empty()
status_area = st.empty()

if "bot_running" not in st.session_state:
    st.session_state.bot_running = False

async def run_bot():
    logs = []
    try:
        async for status, log in start_bot(token, stake, threshold, take_profit, stop_loss, multiplicador):
            status_area.success(status)
            logs.append(log)
            log_area.code("\n".join(logs[-25:]), language='text')
    except Exception as e:
        status_area.error(f"Erro: {str(e)}")
        st.session_state.bot_running = False

if start_button and token and not st.session_state.bot_running:
    st.session_state.bot_running = True
    asyncio.run(run_bot())

if stop_button:
    st.session_state.bot_running = False
    st.warning("Robô parado manualmente.")
