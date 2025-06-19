
import asyncio
import websockets
import json
import random

async def start_bot(token, stake, threshold, take_profit, stop_loss, multiplicador):
    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"authorize": token}))
        auth_response = json.loads(await ws.recv())

        if auth_response.get("error"):
            yield "❌ Erro de Autorização", "Token inválido ou sem permissão de negociação."
            return

        yield "✅ Conectado com sucesso", "Autenticado na conta Deriv."

        await ws.send(json.dumps({
            "ticks": "R_100",
            "subscribe": 1
        }))

        digits = []
        loss_streak = 0
        current_stake = stake
        total_profit = 0
        win_count = 0
        loss_count = 0

        while True:
            if total_profit >= take_profit:
                yield "🏁 Meta Atingida", f"Lucro total ${total_profit:.2f} ≥ Meta ${take_profit:.2f}"
                break
            if abs(total_profit) >= stop_loss:
                yield "🛑 Stop Loss Atingido", f"Perda total ${total_profit:.2f} ≥ Limite ${stop_loss:.2f}"
                break

            try:
                msg = json.loads(await ws.recv())
            except websockets.exceptions.ConnectionClosed:
                yield "🔌 Conexão fechada", "Tentando reconectar..."
                break

            if "tick" in msg:
                quote = msg["tick"]["quote"]
                digit = int(str(quote)[-1])
                digits.append(digit)

                yield "📥 Tick recebido", f"Preço: {quote} | Último dígito: {digit}"

                if len(digits) > 8:
                    digits.pop(0)

                if len(digits) == 8:
                    count_under_4 = sum(1 for d in digits if d < 4)
                    yield "📊 Analisando", f"Dígitos: {digits} | < 4: {count_under_4}"

                    if count_under_4 >= threshold:
                        yield "📈 Sinal Detectado", f"{count_under_4} dígitos < 4. Enviando ordem de R${current_stake:.2f}..."

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

                        buy_response = json.loads(await ws.recv())
                        if "buy" in buy_response:
                            contract_id = buy_response["buy"]["contract_id"]
                            yield "✅ Compra enviada", f"Contrato #{contract_id} iniciado."

                            while True:
                                result_msg = json.loads(await ws.recv())
                                if result_msg.get("contract") and result_msg["contract"].get("contract_id") == contract_id:
                                    status = result_msg["contract"]["status"]
                                    profit = result_msg["contract"].get("profit", 0)
                                    total_profit += profit

                                    if status == "won":
                                        win_count += 1
                                        loss_streak = 0
                                        current_stake = stake
                                        yield "🏆 WIN", f"Lucro ${profit:.2f} | Total: ${total_profit:.2f}"
                                    elif status == "lost":
                                        loss_count += 1
                                        loss_streak += 1
                                        yield "💥 LOSS", f"Prejuízo ${profit:.2f} | Total: ${total_profit:.2f}"
                                        if loss_streak >= 2:
                                            current_stake *= multiplicador
                                            yield "🔁 Multiplicador aplicado", f"Nova stake: R${current_stake:.2f}"
                                    break

                            digits.clear()

                            if loss_streak >= 2:
                                wait = random.randint(6, 487)
                                yield "🕒 Esperando", f"{wait} segundos após 2 perdas seguidas..."
                                await asyncio.sleep(wait)
