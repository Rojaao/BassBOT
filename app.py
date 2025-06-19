import streamlit as st
import asyncio
import websockets
import json
import random

# Inicializar estados
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'task' not in st.session_state:
    st.session_state.task = None
if 'logs' not in st.session_state:
    st.session_state.logs = []

def log(msg):
    st.session_state.logs.append(msg)
    if len(st.session_state.logs) > 100:
        st.session_state.logs.pop(0)

async def ws_receiver(ws, queue):
    try:
        while True:
            msg = await ws.recv()
            await queue.put(json.loads(msg))
    except websockets.ConnectionClosed:
        pass

async def bot_loop(token, stake, threshold, take_profit, stop_loss, multiplicador):
    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"authorize": token}))
        auth = json.loads(await ws.recv())
        if auth.get("error"):
            log("❌ Erro de autenticação. Token inválido.")
            st.session_state.bot_running = False
            return
        log("✅ Autenticado na Deriv.")

        await ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))

        queue = asyncio.Queue()
        receiver_task = asyncio.create_task(ws_receiver(ws, queue))

        digits = []
        total_profit = 0
        current_stake = stake
        loss_streak = 0
        contract_active = False
        contract_id = None
        waiting_buy_response = False

        while st.session_state.bot_running:
            if total_profit >= take_profit:
                log(f"🏁 Meta de lucro atingida: ${total_profit:.2f}")
                st.session_state.bot_running = False
                break
            if abs(total_profit) >= stop_loss:
                log(f"🛑 Stop loss atingido: ${total_profit:.2f}")
                st.session_state.bot_running = False
                break

            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if "tick" in msg and not contract_active and not waiting_buy_response:
                quote = msg["tick"]["quote"]
                digit = int(str(quote)[-1])
                digits.append(digit)
                if len(digits) > 8:
                    digits.pop(0)
                log(f"📥 Tick recebido: {digit} | Buffer: {digits}")

                if len(digits) == 8:
                    count_under_4 = sum(1 for d in digits if d < 4)
                    log(f"📊 Analisando: {count_under_4} dos 8 últimos dígitos < 4")

                    if count_under_4 >= threshold:
                        log(f"📈 Sinal confirmado - enviando ordem OVER 3 com R${current_stake:.2f}")
                        await ws.send(json.dumps({
                            "buy": 1,
                            "price": current_stake,
                            "parameters": {
                                "amount": current_stake,
                                "basis": "stake",
                                "contract_type": "DIGITOVER",
                                "barrier": "3",
                                "currency": "USD",
                                "duration": 1,
                                "duration_unit": "t",
                                "symbol": "R_100"
                            }
                        }))
                        waiting_buy_response = True
                        digits.clear()

            if waiting_buy_response and "buy" in msg:
                contract_id = msg["buy"]["contract_id"]
                contract_active = True
                waiting_buy_response = False
                log(f"✅ Ordem aceita: contrato #{contract_id} iniciado.")

                # Aqui o robô para sozinho após enviar ordem
                st.session_state.bot_running = False
                log("⏸ Robô parado automaticamente após enviar ordem.")

                # Espera tempo aleatório antes de reiniciar
                wait_time = random.randint(5, 320)
                log(f"⏳ Esperando {wait_time} segundos para reiniciar o robô...")
                await asyncio.sleep(wait_time)

                # Reinicia o robô
                st.session_state.bot_running = True
                log("▶️ Robô reiniciado automaticamente!")

            if contract_active and "contract" in msg:
                contract = msg["contract"]
                if contract.get("contract_id") == contract_id:
                    status = contract.get("status")
                    profit = contract.get("profit", 0)
                    total_profit += profit

                    if status == "won":
                        log(f"🏆 WIN: lucro ${profit:.2f} | Total: ${total_profit:.2f}")
                        contract_active = False
                        current_stake = stake
                        loss_streak = 0
                    elif status == "lost":
                        log(f"💥 LOSS: prejuízo ${profit:.2f} | Total: ${total_profit:.2f}")
                        contract_active = False
                        loss_streak += 1
                        if loss_streak >= 2:
                            current_stake *= multiplicador
                            wait_time = random.randint(6, 487)
                            log(f"⏳ Esperando {wait_time} segundos após 2 perdas seguidas...")
                            await asyncio.sleep(wait_time)

def start_bot():
    if not st.session_state.bot_running:
        st.session_state.bot_running = True
        st.session_state.task = asyncio.create_task(bot_loop(
            st.session_state.token,
            st.session_state.stake,
            st.session_state.threshold,
            st.session_state.take_profit,
            st.session_state.stop_loss,
            st.session_state.multiplicador,
        ))

def stop_bot():
    st.session_state.bot_running = False
    if st.session_state.task:
        st.session_state.task.cancel()
        st.session_state.task = None

# Interface Streamlit

st.title("Robô Deriv Automático")

st.text_input("Token API Deriv", key="token", type="password")
st.number_input("Valor da aposta (stake)", key="stake", min_value=0.1, value=1.0, step=0.1)
st.number_input("Quantidade mínima de dígitos < 4 para operar", key="threshold", min_value=1, max_value=8, value=3)
st.number_input("Meta de lucro total (stop gain)", key="take_profit", min_value=1.0, value=50.0)
st.number_input("Limite de perda total (stop loss)", key="stop_loss", min_value=1.0, value=20.0)
st.number_input("Multiplicador após 2 perdas seguidas", key="multiplicador", min_value=1.0, value=1.68)

col1, col2 = st.columns(2)
with col1:
    if st.button("Iniciar Robô"):
        start_bot()
with col2:
    if st.button("Parar Robô"):
        stop_bot()

st.markdown("---")
st.subheader("Logs do robô (últimas 100 mensagens):")
for log_msg in st.session_state.logs:
    st.write(log_msg)
