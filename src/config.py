"""
Carregador de configuração.
Preferências vêm do config.yaml. Segredos e dados pessoais ficam no .env.
"""
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class RegiaoConfig:
    estado: str
    cidades: list[str]
    orgaos: list[str]


@dataclass(frozen=True)
class AreaConfig:
    keywords: list[str]


@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int


@dataclass(frozen=True)
class NotificacaoConfig:
    canal: str
    email: EmailConfig | None


@dataclass(frozen=True)
class BancoConfig:
    tipo: str
    caminho: str


@dataclass(frozen=True)
class AnaliseIAConfig:
    habilitado: bool
    tipo: str
    modelo: str
    prompt: str


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
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

        notif = data["notificacao"]
        em = notif.get("email")

        ia = data.get("analise_ia", {})

        return cls(
            regiao=RegiaoConfig(**data["regiao"]),
            area=AreaConfig(**data["area"]),
            notificacao=NotificacaoConfig(
                canal=notif["canal"],
                email=EmailConfig(**em) if em else None,
            ),
            banco=BancoConfig(
                tipo=data["banco"]["tipo"],
                caminho=data["banco"].get("caminho", "output/notificados.db"),
            ),
            analise_ia=AnaliseIAConfig(
                habilitado=ia.get("habilitado", False),
                tipo=ia.get("tipo", "gemini"),
                modelo=ia.get("modelo", "gemini-2.5-flash"),
                prompt=ia["prompt"],
            ),
            output_dir=data.get("output_dir", "output"),
        )