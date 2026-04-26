# alerta-concursos

Scraper do PCI Concursos que busca concursos por estado, filtra por região e área de interesse, e notifica via Telegram ou Email.

Opcionalmente, analisa o PDF do edital com IA (Gemini ou Ollama local) e inclui um resumo na notificação.

## Estrutura

```
src/
├── main.py           # Orquestra tudo
├── config.py         # Carrega config.yaml e .env
├── scraper_pci.py    # Scraping do PCI Concursos
├── repository.py     # Banco de dados (SQLite ou PostgreSQL)
├── notificar.py      # Notificação (Telegram ou Email)
└── analisador.py     # Análise de editais por IA (Gemini ou Ollama)
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
```

- Edite o `config.yaml` com suas preferências (estado, cidades, órgãos, keywords, canal, etc.)
- Edite o `.env` com suas credenciais (tokens, senhas, chat_id)

## Como rodar

```bash
python src/main.py
```

## O que configurar no `config.yaml`

### Região

```yaml
regiao:
  estado: MINAS GERAIS
  cidades:
    - Belo Horizonte
    - Betim
    - Contagem
  orgaos:
    - FHEMIG
    - CEMIG
    - UFMG
```

### Área de interesse

Edite a lista `keywords`. Exemplo para enfermagem:

```yaml
area:
  keywords:
    - enfermeiro
    - enfermagem
    - técnico de enfermagem
    - auxiliar de enfermagem
```

### Notificação

```yaml
notificacao:
  canal: telegram          # telegram | email

  email:                   # usado apenas se canal=email
    smtp_host: smtp.gmail.com
    smtp_port: 587
```

### Banco de dados

```yaml
banco:
  tipo: sqlite             # sqlite | postgres
  caminho: output/notificados.db   # usado apenas se tipo=sqlite
```

### Análise por IA (opcional)

```yaml
analise_ia:
  habilitado: false
  tipo: gemini             # gemini | ollama
  modelo: gemini-2.5-flash

  # Usados apenas quando tipo=ollama
  host: http://localhost:11434
  max_chars_edital: 50000

  prompt: |
    Analise este edital...
```

## O que configurar no `.env`

### Telegram (se `canal: telegram`)

| Variável | O que colocar |
|---|---|
| `BOT_TOKEN` | Token do bot do Telegram (pega com o @BotFather) |
| `CHAT_ID` | Seu chat ID (acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` depois de mandar mensagem pro bot) |

### Email (se `canal: email`)

| Variável | O que colocar |
|---|---|
| `SMTP_USER` | Email remetente (também usado como login SMTP) |
| `SMTP_PASSWORD` | Senha de app do email (no Gmail, gere em [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)) |
| `EMAIL_TO` | Email destinatário |

### PostgreSQL (se `banco.tipo: postgres`)

| Variável | Padrão | O que colocar |
|---|---|---|
| `DB_HOST` | - | Host do banco |
| `DB_NAME` | - | Nome do banco |
| `DB_USER` | - | Usuário |
| `DB_PASSWORD` | - | Senha |
| `DB_PORT` | `5432` | Porta |

### Gemini (se `analise_ia.tipo: gemini`)

| Variável | O que colocar |
|---|---|
| `GEMINI_API_KEY` | Chave da API do Gemini (grátis em [aistudio.google.com](https://aistudio.google.com)) |

### Ollama (se `analise_ia.tipo: ollama`)

Não precisa de nada no `.env`. Mas você precisa instalar o Ollama e baixar o modelo:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3        # ou llama3.1, qwen2.5, etc.
```

O serviço sobe automaticamente via systemd. Para conferir:

```bash
systemctl status ollama
ollama list
```

## Como funciona

1. Busca todos os concursos do estado no PCI Concursos
2. Filtra pela região (cidades + órgãos)
3. Remove concursos com inscrição encerrada
4. Visita cada link e verifica se tem vaga na área de interesse
5. Compara com o banco pra pegar só os novos
6. Se `analise_ia.habilitado: true`, baixa o PDF do edital e analisa com a IA configurada
7. Envia notificação pelo canal configurado
8. Salva os links notificados no banco (apenas os enviados com sucesso)

## Agendar execução

Use cron pra rodar automaticamente:

```bash
crontab -e
```

Adicione (exemplo: a cada 4 horas):

```
0 */4 * * * cd /home/seu_usuario/rep/alerta-concursos && .venv/bin/python src/main.py
```
