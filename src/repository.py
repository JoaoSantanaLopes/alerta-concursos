"""
Camada de persistência.
Tipo de banco e caminho do SQLite vêm do config.yaml.
Credenciais de Postgres vêm do .env.
"""
import os
import sqlite3
from abc import ABC, abstractmethod
import pandas as pd
from config import BancoConfig


class Repository(ABC):
    @abstractmethod
    def ja_notificado(self, link: str) -> bool:
        pass

    @abstractmethod
    def salvar(self, link: str, concurso: str) -> None:
        pass

    @abstractmethod
    def fechar(self) -> None:
        pass


class SQLiteRepository(Repository):
    def __init__(self, caminho: str):
        # Garante que o diretório existe antes de conectar
        os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)

        self.conn = sqlite3.connect(caminho)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notificados (
                link TEXT PRIMARY KEY,
                concurso TEXT,
                notificado_em DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def ja_notificado(self, link):
        resultado = self.conn.execute(
            "SELECT 1 FROM notificados WHERE link = ?", (link,)
        ).fetchone()
        return resultado is not None

    def salvar(self, link, concurso):
        self.conn.execute(
            "INSERT OR IGNORE INTO notificados (link, concurso) VALUES (?, ?)",
            (link, concurso),
        )
        self.conn.commit()

    def fechar(self):
        self.conn.close()


class PostgresRepository(Repository):
    def __init__(self, host: str, database: str, user: str, password: str, port: str = "5432"):
        import psycopg2
        self.conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notificados (
                link TEXT PRIMARY KEY,
                concurso TEXT,
                notificado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        cur.close()

    def ja_notificado(self, link):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM notificados WHERE link = %s", (link,))
        resultado = cur.fetchone()
        cur.close()
        return resultado is not None

    def salvar(self, link, concurso):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO notificados (link, concurso) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (link, concurso),
        )
        self.conn.commit()
        cur.close()

    def fechar(self):
        self.conn.close()


def criar_repositorio(cfg: BancoConfig) -> Repository:
    if cfg.tipo == "sqlite":
        return SQLiteRepository(cfg.caminho)

    if cfg.tipo == "postgres":
        host = os.getenv("DB_HOST")
        database = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", "5432")
        if not all([host, database, user, password]):
            raise ValueError(
                "Para Postgres, DB_HOST, DB_NAME, DB_USER e DB_PASSWORD devem estar no .env"
            )
        return PostgresRepository(host, database, user, password, port)

    raise ValueError(f"banco.tipo '{cfg.tipo}' não suportado")


def filtrar_novos(df, repositorio):
    return df[~df["Link"].apply(repositorio.ja_notificado)].reset_index(drop=True)


def salvar_notificados(df, repositorio):
    for _, row in df.iterrows():
        repositorio.salvar(row["Link"], row["Concurso"])