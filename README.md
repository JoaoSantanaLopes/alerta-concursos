# alerta-concursos

Scraper do PCI Concursos que busca concursos por estado, filtra por região e área de interesse, e notifica via Telegram ou Email.

Opcionalmente, analisa o PDF do edital com IA (Gemini) e inclui um resumo na notificação.

## Estrutura

```
src/
├── main.py           # Orquestra tudo
├── scraper_pci.py    # Scraping do PCI Concursos
├── repositorio.py    # Banco de dados (SQLite ou PostgreSQL)
├── notificar.py      # Notificação (Telegram ou Email)
└── analisador.py     # Análise de editais por IA (Gemini)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preencha o `.env` com seus dados (veja abaixo).

## Como rodar

```bash
python src/main.py
```

## O que configurar no .env

### Obrigatório

| Variável | O que colocar |
|---|---|
| `BOT_TOKEN` | Token do bot do Telegram (pega com o @BotFather) |
| `CHAT_ID` | Seu chat ID (acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` depois de mandar mensagem pro bot) |

### Opcional

| Variável | Padrão | O que faz |
|---|---|---|
| `DB_TYPE` | `sqlite` | Troque para `postgres` pra usar PostgreSQL/RDS |
| `DB_PATH` | `output/notificados.db` | Caminho do banco SQLite |
| `NOTIFIER_TYPE` | `telegram` | Troque para `email` pra notificar por email |
| `ANALISE_IA` | `false` | Troque para `true` pra analisar editais com IA |
| `GEMINI_API_KEY` | - | Chave da API do Gemini (grátis em aistudio.google.com) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Modelo do Gemini |

## O que personalizar no scraper_pci.py

### Mudar o estado

```python
ESTADO = "MINAS GERAIS"
```

### Mudar as cidades da região

```python
CIDADES = [
    "Belo Horizonte", "Betim", "Contagem", ...
]
```

### Mudar os órgãos estaduais/federais

```python
ORGAOS = [
    "FHEMIG", "CEMIG", "COPASA", "UFMG", ...
]
```

### Mudar a área de interesse

Edite a lista `KEYWORDS`. Exemplo pra enfermagem:

```python
KEYWORDS = [
    "enfermeiro", "enfermagem", "técnico de enfermagem",
    "auxiliar de enfermagem", "saúde",
]
```

## Como funciona

1. Busca todos os concursos do estado no PCI Concursos
2. Filtra pela região (cidades + órgãos)
3. Remove concursos com inscrição encerrada
4. Visita cada link e verifica se tem vaga na área de interesse
5. Compara com o banco pra pegar só os novos
6. Se `ANALISE_IA=true`, baixa o PDF do edital e analisa com Gemini
7. Envia notificação via Telegram
8. Salva os links notificados no banco

## Agendar execução

Use cron pra rodar automaticamente:

```bash
crontab -e
```

Adicione (exemplo: a cada 4 horas):

```
0 */4 * * * cd /home/seu_usuario/rep/alerta-concursos && .venv/bin/python src/main.py
```
