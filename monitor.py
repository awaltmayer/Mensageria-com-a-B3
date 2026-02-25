import yfinance as yf
from datetime import datetime

def buscar_dados_acoes(lista_acoes):
    dados_processados = {}
    
    # Pega o horário atual formatado (ex: 10:35:12)
    horario_atual = datetime.now().strftime("%H:%M:%S")
    
    print(f"[{horario_atual}] 🔄 Buscando dados na B3...")

    try:
        tickers = " ".join(lista_acoes)
        dados = yf.download(tickers, period="1d", group_by='ticker', progress=False)

        for acao in lista_acoes:
            try:
                df_acao = dados[acao]
                if len(df_acao) > 0:
                    preco_atual = float(df_acao['Close'].iloc[-1])
                    abertura = float(df_acao['Open'].iloc[-1])
                    variacao = ((preco_atual - abertura) / abertura) * 100
                    
                    dados_processados[acao] = {
                        "preco": round(preco_atual, 2),
                        "variacao": round(variacao, 2)
                    }
                else:
                    dados_processados[acao] = {"erro": "Sem dados"}
            except Exception:
                dados_processados[acao] = {"erro": "N/A"}

    except Exception as e:
        print(f"Erro crítico: {e}")
        for acao in lista_acoes:
            dados_processados[acao] = {"erro": "Falha API"}

    # Retorna os dados E o horário
    return dados_processados, horario_atual