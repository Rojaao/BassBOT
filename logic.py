import asyncio
import websockets
import json
import random

async def start_bot(token, stake, threshold, take_profit, stop_loss, multiplicador):
    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"
    async with websockets.connect(uri) as ws:
        # Autenticação
        await ws.send(json.dumps({"authorize": token}))
        auth = json.loads(await ws.recv())
        if auth.get("error"):
            yield "❌ Erro de autenticação", "Token inválido."
            return
        yield "✅ Autenticado", "Conexão estabelecida com Deriv."

        # Assina ticks
        await ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))

        digits = []
        total_profit = 0
        current_stake = stake
        loss_streak = 0

        contract_active = False
        contract_id = None
        waiting_buy_response = False

        while True:
            if total_profit >= take_profit:
                yield "🏁 Meta de lucro atingida", f"Lucro total: ${total_profit:.2f}"
                break
            if abs(total_profit) >= stop_loss:
                yield "🛑 Stop loss atingido", f"Perda total: ${total_profit:.2f}"
                break

            msg = json.loads(await ws.recv())

            # Recebe ticks e acumula
            if "tick" in msg and not contract_active and not waiting_buy_response:
                quote = msg["tick"]["quote"]
                digit = int(str(quote)[-1])
                digits.append(digit)
                if len(digits) > 8:
                    digits.pop(0)
                yield "📥 Tick recebido", f"Dígito: {digit} | Buffer: {digits}"

                if len(digits) == 8:
                    count_under_4 = sum(1 for d in digits if d < 4)
                    yield "📊 Analisando", f"{count_under_4} dos 8 últimos dígitos < 4"

                    if count_under_4 >= threshold:
                        # Envia ordem
                        yield "📈 Enviando ordem", f"Stake: R${current_stake:.2f} OVER 3"
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
                        digits.clear()  # Limpa buffer após ordem

            # Espera resposta da compra
            if waiting_buy_response and "buy" in msg:
                contract_id = msg["buy"]["contract_id"]
                contract_active = True
                waiting_buy_response = False
                yield "✅ Ordem aceita", f"Contrato #{contract_id} iniciado."

            # Acompanha contrato ativo e resultado
            if contract_active and "contract" in msg:
                contract = msg["contract"]
                if contract.get("contract_id") == contract_id:
                    status = contract.get("status")
                    profit = contract.get("profit", 0)
                    total_profit += profit

                    if status == "won":
                        yield "🏆 WIN", f"Lucro: ${profit:.2f} | Total: ${total_profit:.2f}"
                        contract_active = False
                        current_stake = stake
                        loss_streak = 0
                    elif status == "lost":
                        yield "💥 LOSS", f"Prejuízo: ${profit:.2f} | Total: ${total_profit:.2f}"
                        loss_streak += 1
                        contract_active = False
                        if loss_streak >= 2:
                            current_stake *= multiplicador
                            wait_time = random.randint(6, 487)
                            yield "⏳ Esperando", f"{wait_time}s após 2 perdas seguidas..."
                            await asyncio.sleep(wait_time)
