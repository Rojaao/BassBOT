
import streamlit as st
import asyncio
from logic import start_bot

st.set_page_config(page_title="Deriv Over 3 Bot", layout="wide")

st.title("🤖 Deriv Bot - Estratégia Over 3 (Dinâmico)")
st.markdown("Este bot analisa os 8 últimos dígitos e faz entrada em **Over 3** com 1 tick.")

token = st.text_input("🔑 Insira seu Token da Deriv", type="password")
stake = st.number_input("💵 Valor da Entrada", min_value=0.35, value=1.00, step=0.01)
threshold = st.number_input("📉 Mínimo de dígitos < 4 para entrar", min_value=1, max_value=8, value=3)
start_button = st.button("▶️ Iniciar Robô")
stop_button = st.button("⏹️ Parar Robô")

log_area = st.empty()
status_area = st.empty()

if "bot_running" not in st.session_state:
    st.session_state.bot_running = False

async def run_bot():
    logs = []
    try:
        async for status, log in start_bot(token, stake, threshold):
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
