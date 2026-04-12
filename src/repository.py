"""
Camada de persistência.
Para trocar de banco, mude DB_TYPE no .env.
"""

import os
import sqlite3
from abc import ABC, abstractmethod
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class Repository(ABC):

    @abstractmethod
    def ja_notificado(self, link):
        pass

    @abstractmethod
    def salvar(self, link, concurso):
        pass

    @abstractmethod
    def fechar(self):
        pass


class SQLiteRepository(Repository):

    def __init__(self, caminho="output/notificados.db"):
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

    def __init__(self):
        import psycopg2
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT", "5432"),
        )
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notificados (
                link TEXT PRIMARY KEY,
                concurso TEXT,
                notificado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

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


def criar_repositorio():
    """Factory: cria o repositório certo baseado no DB_TYPE do .env."""
    db_type = os.getenv("DB_TYPE", "sqlite")

    if db_type == "sqlite":
        return SQLiteRepository(os.getenv("DB_PATH", "output/notificados.db"))
    elif db_type == "postgres":
        return PostgresRepository()
    else:
        raise ValueError(f"DB_TYPE '{db_type}' não suportado")


def filtrar_novos(df, repositorio):
    return df[~df["Link"].apply(repositorio.ja_notificado)].reset_index(drop=True)


def salvar_notificados(df, repositorio):
    for _, row in df.iterrows():
        repositorio.salvar(row["Link"], row["Concurso"])