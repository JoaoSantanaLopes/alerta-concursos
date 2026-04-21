"""
Módulo de notificação.
Recebe credenciais e preferências via Config.
"""
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
import pandas as pd
import requests
from config import (
    EmailCredentials,
    EmailServerConfig,
    NotificacaoConfig,
    TelegramCredentials,
)


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
    def enviar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Retorna o DataFrame dos itens efetivamente enviados."""
        pass


class TelegramNotifier(Notifier):
    def __init__(self, creds: TelegramCredentials):
        self.chat_id = creds.chat_id
        self.url = f"https://api.telegram.org/bot{creds.bot_token}/sendMessage"

    def enviar(self, df):
        if df.empty:
            return df

        try:
            self._postar(f"🔔 *{len(df)} concurso(s) novo(s)!*", markdown=True)
        except Exception as e:
            print(f"⚠️ Falha no cabeçalho Telegram: {e}")
            # segue tentando os itens mesmo assim

        enviados_idx = []
        for idx, row in df.iterrows():
            try:
                tem_analise = "Análise IA" in row and pd.notna(row["Análise IA"])
                if tem_analise:
                    msg = _formatar_analise(row)
                    if len(msg.encode("utf-8")) > 4000:
                        msg = msg[:2000] + "\n\n... (análise truncada)"
                    self._postar(msg, markdown=False)
                else:
                    self._postar(_formatar(row), markdown=True)
                enviados_idx.append(idx)
            except Exception as e:
                print(f"⚠️ Falha ao enviar '{row['Concurso']}': {e}")

        return df.loc[enviados_idx]

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
    def __init__(self, server: EmailServerConfig, creds: EmailCredentials):
        self.smtp_host = server.smtp_host
        self.smtp_port = server.smtp_port
        self.user = creds.user
        self.password = creds.password
        self.destinatario = creds.destinatario

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

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            return df
        except Exception as e:
            print(f"⚠️ Falha ao enviar email: {e}")
            return df.iloc[0:0] 


def criar_notificador(cfg: NotificacaoConfig) -> Notifier:
    if cfg.canal == "telegram":
        return TelegramNotifier(cfg.telegram)
    if cfg.canal == "email":
        return EmailNotifier(cfg.email_server, cfg.email)
    raise ValueError(f"Canal '{cfg.canal}' não suportado")