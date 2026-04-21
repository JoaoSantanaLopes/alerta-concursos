"""
Módulo de notificação.
Preferência de canal e hostname SMTP vêm do config.yaml.
Segredos e dados pessoais (token, chat_id, email, senha) vêm do .env.
"""
import os
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText

import pandas as pd
import requests

from config import EmailConfig, NotificacaoConfig


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
    def enviar(self, df: pd.DataFrame) -> None:
        pass


class TelegramNotifier(Notifier):
    def __init__(self, token: str, chat_id: str):
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"

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
    def __init__(self, cfg: EmailConfig, user: str, password: str, destinatario: str):
        self.smtp_host = cfg.smtp_host
        self.smtp_port = cfg.smtp_port
        self.user = user
        self.password = password
        self.destinatario = destinatario

    def enviar(self, df):
        if df.empty:
            return

        corpo = f"{len(df)} concurso(s) novo(s)!\n\n"
        for _, row in df.iterrows():
            corpo += f"- {row['Concurso']} | {row.get('Salário Até', '-')} | Até {row.get('Inscrição Até', '-')}\n"
            corpo += f"  {row['Link']}\n"
            if "Análise IA" in row and pd.notna(row["Análise IA"]):
                corpo += f"\n  Análise do edital:\n{row['Análise IA']}\n"
            corpo += "\n"

        msg = MIMEText(corpo)
        msg["Subject"] = f"🔔 {len(df)} concurso(s) novo(s)"
        msg["From"] = self.user
        msg["To"] = self.destinatario

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)


def criar_notificador(cfg: NotificacaoConfig) -> Notifier:
    if cfg.canal == "telegram":
        token = os.getenv("BOT_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        if not token or not chat_id:
            raise ValueError("BOT_TOKEN e CHAT_ID devem estar definidos no .env")
        return TelegramNotifier(token, chat_id)

    if cfg.canal == "email":
        if cfg.email is None:
            raise ValueError("Canal 'email' selecionado mas bloco 'email' ausente no config.yaml")
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        destinatario = os.getenv("EMAIL_TO")
        if not all([user, password, destinatario]):
            raise ValueError("SMTP_USER, SMTP_PASSWORD e EMAIL_TO devem estar no .env")
        return EmailNotifier(cfg.email, user, password, destinatario)

    raise ValueError(f"Canal '{cfg.canal}' não suportado")