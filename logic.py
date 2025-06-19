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

        # Assinar ticks
        await ws.send(json.dumps({"ticks": "R_100", "subscribe": 1}))

        digits = []
        total_profit = 0
        loss_streak = 0
        current_stake = stake
        threshold_reached = False
        contract_id = None
        contract_active = False

        while True:
            if total_profit >= take_profit:
                yield "🏁 Meta Atingida", f"Lucro total ${total_profit:.2f} ≥ Meta ${take_profit:.2f}"
                break
            if abs(total_profit) >= stop_loss:
                yield "🛑 Stop Loss Atingido", f"Perda total ${total_profit:.2f} ≥ Limite ${stop_loss:.2f}"
                break

            msg = json.loads(await ws.recv())

            # Recebe tick
            if "tick" in msg and not contract_active:
                quote = msg["tick"]["quote"]
                digit = int(str(quote)[-1])
                digits.append(digit)
                if len(digits) > 8:
                    digits.pop(0)

                yield "📥 Tick recebido", f"Dígito: {digit} | Buffer: {digits}"

                if len(digits) == 8:
                    count_under_4 = sum(1 for d in digits if d < 4)
                    yield "📊 Analisando", f"{count_under_4} dos últimos 8 dígitos estão abaixo de 4"

                    if count_under_4 >= threshold:
                        threshold_reached = True
                    else:
                        threshold_reached = False

            # Se chegou sinal e não tem contrato ativo, envia ordem
            if threshold_reached and not contract_active:
                yield "📈 Sinal Confirmado", f"Enviando ordem no OVER 3 com R${current_stake:.2f}"

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
                if "buy" not in buy_response:
                    yield "❌ Erro ao comprar", str(buy_response)
                    threshold_reached = False
                    digits.clear()
                    continue

                contract_id = buy_response["buy"]["contract_id"]
                contract_active = True
                threshold_reached = False
                digits.clear()
                yield "✅ Ordem Enviada", f"Contrato #{contract_id} iniciado."

            # Se contrato ativo, verificar se msg é status do contrato
            if contract_active and "contract" in msg:
                c = msg["contract"]
                if c.get("contract_id") == contract_id:
                    status = c.get("status")
                    profit = c.get("profit", 0)
                    total_profit += profit

                    if status == "won":
                        yield "🏆 WIN", f"Lucro ${profit:.2f} | Total: ${total_profit:.2f}"
                        current_stake = stake
                        loss_streak = 0
                        contract_active = False
                    elif status == "lost":
                        yield "💥 LOSS", f"Prejuízo ${profit:.2f} | Total: ${total_profit:.2f}"
                        loss_streak += 1
                        if loss_streak >= 2:
                            current_stake *= multiplicador
                            wait_time = random.randint(6, 487)
                            yield "🕒 Esperando", f"{wait_time}s após 2 perdas seguidas..."
                            await asyncio.sleep(wait_time)
                        contract_active = False
