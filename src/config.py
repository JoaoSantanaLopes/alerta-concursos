"""
Carregador de configuração.

- Preferências (canal, estado, modelo, etc.) → config.yaml
- Segredos e dados pessoais (tokens, senhas, emails) → .env
"""
import os
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv


# === Preferências (do YAML) ===

@dataclass(frozen=True)
class RegiaoConfig:
    estado: str
    cidades: list[str]
    orgaos: list[str]


@dataclass(frozen=True)
class AreaConfig:
    keywords: list[str]


# === Credenciais (do .env) ===

@dataclass(frozen=True)
class TelegramCredentials:
    bot_token: str
    chat_id: str


@dataclass(frozen=True)
class EmailCredentials:
    user: str
    password: str
    destinatario: str


@dataclass(frozen=True)
class PostgresCredentials:
    host: str
    database: str
    user: str
    password: str
    port: str


# === preferência + credencial ===

@dataclass(frozen=True)
class EmailServerConfig:
    smtp_host: str
    smtp_port: int


@dataclass(frozen=True)
class NotificacaoConfig:
    canal: str                                  # "telegram" ou "email"
    telegram: TelegramCredentials | None        # preenchido se canal=telegram
    email_server: EmailServerConfig | None      # preenchido se canal=email
    email: EmailCredentials | None              # preenchido se canal=email


@dataclass(frozen=True)
class BancoConfig:
    tipo: str                                   # "sqlite" ou "postgres"
    caminho: str                                # usado se tipo=sqlite
    postgres: PostgresCredentials | None        # preenchido se tipo=postgres


@dataclass(frozen=True)
class AnaliseIAConfig:
    habilitado: bool
    tipo: str                                   # "gemini"
    modelo: str
    prompt: str
    gemini_api_key: str | None                  # preenchido se habilitado=true


# === Raiz ===

@dataclass(frozen=True)
class Config:
    regiao: RegiaoConfig
    area: AreaConfig
    notificacao: NotificacaoConfig
    banco: BancoConfig
    analise_ia: AnaliseIAConfig
    output_dir: str

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        load_dotenv()

        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(
                f"{yaml_path} não encontrado. "
                f"Rode: cp config.example.yaml config.yaml"
            )

        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        return cls(
            regiao=RegiaoConfig(**data["regiao"]),
            area=AreaConfig(**data["area"]),
            notificacao=_build_notificacao(data["notificacao"]),
            banco=_build_banco(data["banco"]),
            analise_ia=_build_analise_ia(data.get("analise_ia", {})),
            output_dir=data.get("output_dir", "output"),
        )


# === Helpers privados ===
# Cada um só lê os envs do contexto que realmente vai ser usado.

def _require_env(nome: str, contexto: str) -> str:
    valor = os.getenv(nome)
    if not valor:
        raise ValueError(f"{nome} não definida no .env (necessária para {contexto})")
    return valor


def _build_notificacao(data: dict) -> NotificacaoConfig:
    canal = data["canal"]

    telegram = None
    email_server = None
    email = None

    if canal == "telegram":
        telegram = TelegramCredentials(
            bot_token=_require_env("BOT_TOKEN", "canal telegram"),
            chat_id=_require_env("CHAT_ID", "canal telegram"),
        )
    elif canal == "email":
        if "email" not in data:
            raise ValueError("Canal 'email' selecionado mas bloco 'email' ausente no config.yaml")
        email_server = EmailServerConfig(**data["email"])
        email = EmailCredentials(
            user=_require_env("SMTP_USER", "canal email"),
            password=_require_env("SMTP_PASSWORD", "canal email"),
            destinatario=_require_env("EMAIL_TO", "canal email"),
        )
    else:
        raise ValueError(f"notificacao.canal '{canal}' não suportado")

    return NotificacaoConfig(
        canal=canal,
        telegram=telegram,
        email_server=email_server,
        email=email,
    )


def _build_banco(data: dict) -> BancoConfig:
    tipo = data["tipo"]
    caminho = data.get("caminho", "output/notificados.db")

    postgres = None
    if tipo == "postgres":
        postgres = PostgresCredentials(
            host=_require_env("DB_HOST", "banco postgres"),
            database=_require_env("DB_NAME", "banco postgres"),
            user=_require_env("DB_USER", "banco postgres"),
            password=_require_env("DB_PASSWORD", "banco postgres"),
            port=os.getenv("DB_PORT", "5432"),
        )
    elif tipo != "sqlite":
        raise ValueError(f"banco.tipo '{tipo}' não suportado")

    return BancoConfig(tipo=tipo, caminho=caminho, postgres=postgres)


def _build_analise_ia(data: dict) -> AnaliseIAConfig:
    habilitado = data.get("habilitado", False)
    tipo = data.get("tipo", "gemini")
    modelo = data.get("modelo", "gemini-2.5-flash")
    prompt = data.get("prompt", "")

    gemini_api_key = None
    if habilitado:
        if not prompt:
            raise ValueError("analise_ia.prompt é obrigatório quando analise_ia.habilitado=true")
        if tipo == "gemini":
            gemini_api_key = _require_env("GEMINI_API_KEY", "analise_ia com tipo=gemini")
        else:
            raise ValueError(f"analise_ia.tipo '{tipo}' não suportado")

    return AnaliseIAConfig(
        habilitado=habilitado,
        tipo=tipo,
        modelo=modelo,
        prompt=prompt,
        gemini_api_key=gemini_api_key,
    )