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

        total_profit = 0
        current_stake = stake
        loss_streak = 0

        digits = []

        while True:
            # Verificação de meta
            if total_profit >= take_profit:
                yield "🏁 Meta Atingida", f"Lucro total ${total_profit:.2f} ≥ Meta ${take_profit:.2f}"
                break
            if abs(total_profit) >= stop_loss:
                yield "🛑 Stop Loss Atingido", f"Perda total ${total_profit:.2f} ≥ Limite ${stop_loss:.2f}"
                break

            # Coleta de 8 dígitos
            while len(digits) < 8:
                msg = json.loads(await ws.recv())
                if "tick" in msg:
                    digit = int(str(msg["tick"]["quote"])[-1])
                    digits.append(digit)
                    yield "📥 Tick recebido", f"Dígito: {digit} | Buffer: {digits}"

            # Análise dos últimos 8 dígitos
            count_under_4 = sum(1 for d in digits if d < 4)
            yield "📊 Analisando", f"{count_under_4} dos últimos 8 dígitos estão abaixo de 4"

            if count_under_4 >= threshold:
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

                response = json.loads(await ws.recv())
                if "buy" not in response:
                    yield "❌ Erro ao comprar", str(response)
                    continue

                contract_id = response["buy"]["contract_id"]
                yield "✅ Ordem Enviada", f"Contrato #{contract_id} iniciado."

                # Aguardar resultado do contrato
                while True:
                    result_msg = json.loads(await ws.recv())
                    contract = result_msg.get("contract", {})
                    if contract.get("contract_id") == contract_id:
                        status = contract.get("status")
                        profit = contract.get("profit", 0)
                        total_profit += profit

                        if status == "won":
                            yield "🏆 WIN", f"Lucro ${profit:.2f} | Total: ${total_profit:.2f}"
                            current_stake = stake
                            loss_streak = 0
                        elif status == "lost":
                            yield "💥 LOSS", f"Prejuízo ${profit:.2f} | Total: ${total_profit:.2f}"
                            loss_streak += 1
                            if loss_streak >= 2:
                                current_stake *= multiplicador
                                wait_time = random.randint(6, 487)
                                yield "🕒 Esperando", f"{wait_time}s após 2 perdas seguidas..."
                                await asyncio.sleep(wait_time)
                        break

            else:
                yield "⏭️ Sem Sinal", "Aguardando novo tick para reiniciar análise..."

            # Reset para reiniciar o ciclo
            digits = []
