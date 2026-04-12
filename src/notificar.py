"""
Módulo de notificação.
Para trocar o canal, mude NOTIFIER_TYPE no .env.
"""

import os
import requests
import pandas as pd
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

# === FORMATAÇÃO ===
def _formatar(row):
    cargos = ""
    if "Cargos Encontrados" in row and pd.notna(row["Cargos Encontrados"]):
        cargos = f"💼 {row['Cargos Encontrados']}\n"

    return (
        f"📌 *{row['Concurso']}*\n"
        f"💰 {row.get('Salário Até', '-')} | 🎓 {row.get('Nível', '-')} | 👥 {row.get('Vagas', '-')} vaga(s)\n"
        f"📅 Inscrição até: {row.get('Inscrição Até', '-')}\n"
        f"{cargos}"
        f"🔗 [Ver edital]({row['Link']})\n"
    )


def _formatar_analise(row):
    return (
        f"📌 {row['Concurso']}\n"
        f"💰 {row.get('Salário Até', '-')} | 🎓 {row.get('Nível', '-')} | 👥 {row.get('Vagas', '-')} vaga(s)\n"
        f"📅 Inscrição até: {row.get('Inscrição Até', '-')}\n"
        f"🔗 {row['Link']}\n"
        f"\n🤖 Análise do edital:\n{row['Análise IA']}\n"
    )


# === CLASSES ===
class Notifier(ABC):

    @abstractmethod
    def enviar(self, df):
        pass


class TelegramNotifier(Notifier):

    def __init__(self):
        self.token = os.getenv("BOT_TOKEN")
        self.chat_id = os.getenv("CHAT_ID")
        self.url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def enviar(self, df):
        if df.empty:
            return

        self._postar(f"🔔 *{len(df)} concurso(s) novo(s)!*", markdown=True)

        for _, row in df.iterrows():
            tem_analise = "Análise IA" in row and pd.notna(row["Análise IA"])

            if tem_analise:
                msg = _formatar_analise(row)
                if len(msg.encode("utf-8")) > 4000:
                    msg = msg[:2000] + "\n\n... (análise truncada)"
                self._postar(msg, markdown=False)
            else:
                self._postar(_formatar(row), markdown=True)

    def _postar(self, texto, markdown=True):
        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "disable_web_page_preview": True,
        }
        if markdown:
            payload["parse_mode"] = "Markdown"

        resp = requests.post(self.url, json=payload, timeout=30)

        if not resp.ok:
            raise RuntimeError(f"Erro Telegram: {resp.status_code} - {resp.text}")


class EmailNotifier(Notifier):

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.destinatario = os.getenv("EMAIL_TO")

    def enviar(self, df):
        if df.empty:
            return

        import smtplib
        from email.mime.text import MIMEText

        corpo = f"{len(df)} concurso(s) novo(s)!\n\n"
        for _, row in df.iterrows():
            corpo += f"- {row['Concurso']} | {row.get('Salário Até', '-')} | Até {row.get('Inscrição Até', '-')}\n"
            corpo += f"  {row['Link']}\n\n"

        msg = MIMEText(corpo)
        msg["Subject"] = f"🔔 {len(df)} concurso(s) novo(s)"
        msg["From"] = self.smtp_user
        msg["To"] = self.destinatario

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)


def criar_notificador():
    tipo = os.getenv("NOTIFIER_TYPE", "telegram")

    if tipo == "telegram":
        return TelegramNotifier()
    elif tipo == "email":
        return EmailNotifier()
    else:
        raise ValueError(f"NOTIFIER_TYPE '{tipo}' não suportado")