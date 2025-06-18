
# 🤖 Deriv Over 3 Bot (Dinâmico)

Este robô opera na Deriv analisando os últimos 8 dígitos do ativo R_100, entrando em "OVER 3" com base em um número mínimo de dígitos menores que 4, configurável via interface Streamlit.

## Como usar
1. Insira seu token da Deriv
2. Defina o valor da entrada (ex: 1.00)
3. Escolha quantos dígitos < 4 devem acionar a entrada
4. Clique em "Iniciar Robô"

## Estratégia
- Se o número de dígitos menores que 4 for igual ou maior que o escolhido, entra em OVER 3 com 1 tick
- Após LOSS, multiplica stake por 1.68
- Após WIN, reseta o valor original
- Após 2 perdas, espera um tempo aleatório (6–487s)

Recomendado testar em conta virtual primeiro.
