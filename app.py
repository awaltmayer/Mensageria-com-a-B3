from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
import requests
import feedparser
from datetime import datetime
from monitor import buscar_dados_acoes

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
TELEGRAM_TOKEN = "8218347532:AAGhLleSgS644rU6-Bs5THTaEPg-3mBzSxQ"
TELEGRAM_CHAT_ID = "6585660554"

ACOES_MONITORADAS = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", 
    "WEGE3.SA", "ABEV3.SA", "MGLU3.SA", "BBAS3.SA"
]

# Carteira Fictícia
CARTEIRA_SIMULADA = {
    "PETR4.SA": 100,
    "VALE3.SA": 50,
    "WEGE3.SA": 200,
    "ITUB4.SA": 0
}

PRECOS_ALVO = { "PETR4.SA": 38.00, "VALE3.SA": 60.00, "MGLU3.SA": 2.00 }

# Configuração do Agendador
class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "America/Sao_Paulo" # Garante horário do Brasil

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)

# --- FUNÇÕES AUXILIARES ---

def enviar_telegram(mensagem):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Erro Telegram: {e}")

def buscar_noticias():
    try:
        feed = feedparser.parse('https://www.infomoney.com.br/mercados/feed/')
        return [{"titulo": entry.title, "link": entry.link} for entry in feed.entries[:5]]
    except:
        return []

# --- TAREFAS AUTOMÁTICAS ---

# 1. Monitoramento Intraday (A cada 30 min) - Apenas Alertas de Preço
@scheduler.task('interval', id='monitoramento_preco', minutes=30)
def alerta_precos():
    print("🔎 Verificando preços alvo...")
    with app.app_context():
        dados, _ = buscar_dados_acoes(ACOES_MONITORADAS)
        for simb, info in dados.items():
            if "erro" not in info and simb in PRECOS_ALVO:
                if info['preco'] <= PRECOS_ALVO[simb]:
                    enviar_telegram(f"🚨 *ALERTA*: {simb} caiu para R$ {info['preco']} (Alvo: {PRECOS_ALVO[simb]})")

# 2. Resumo de Fechamento (Fixo às 17:30) - Com Notícias
@scheduler.task('cron', id='resumo_fechamento', hour=17, minute=30)
def resumo_dia():
    print("🌙 Gerando resumo do dia...")
    with app.app_context():
        dados, horario = buscar_dados_acoes(ACOES_MONITORADAS)
        noticias = buscar_noticias()
        
        msg = f"🌙 *Resumo de Fechamento* ({datetime.now().strftime('%d/%m')})\n\n"
        
        # Cotações Finais
        msg += "📊 *Mercado:*\n"
        for simb, info in dados.items():
            if "erro" not in info:
                icone = "🟢" if info['variacao'] >= 0 else "🔻"
                msg += f"{icone} {simb.replace('.SA','')}: R$ {info['preco']} ({info['variacao']}%)\n"
        
        # Notícias
        msg += "\n📰 *Destaques do Dia:*\n"
        for i, n in enumerate(noticias[:3], 1):
            msg += f"{i}. [{n['titulo']}]({n['link']})\n"
            
        msg += "\n_Até amanhã! 👋_"
        enviar_telegram(msg)

scheduler.start()

# --- ROTAS ---

@app.route('/')
def index():
    """Página Principal: Apenas Cards das Ações"""
    dados, horario = buscar_dados_acoes(ACOES_MONITORADAS)
    return render_template('index.html', dados=dados, horario=horario)

@app.route('/carteira')
def carteira():
    """Nova Página: Carteira e Gráficos"""
    dados, horario = buscar_dados_acoes(ACOES_MONITORADAS)
    
    # Processa dados da carteira
    detalhes = []
    patrimonio = 0
    labels_pie = []
    valores_pie = []
    
    for acao, info in dados.items():
        qtd = CARTEIRA_SIMULADA.get(acao, 0)
        if qtd > 0 and "erro" not in info:
            total = qtd * info['preco']
            patrimonio += total
            detalhes.append({
                "acao": acao.replace('.SA',''),
                "qtd": qtd,
                "preco": info['preco'],
                "total": round(total, 2),
                "variacao": info['variacao']
            })
            # Dados para o Gráfico de Pizza
            labels_pie.append(acao.replace('.SA',''))
            valores_pie.append(round(total, 2))
            
    return render_template('carteira.html', 
                        detalhes=detalhes, 
                        patrimonio=round(patrimonio, 2),
                        horario=horario,
                        labels_pie=labels_pie,
                        data_pie=valores_pie)

@app.route('/testar-resumo')
def testar_resumo():
    """Rota extra pra você forçar o envio do resumo agora e testar"""
    resumo_dia() # Chama a função manualmente
    return jsonify({"status": "Resumo enviado!"})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)