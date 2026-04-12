"""
Módulo de análise de editais por IA.
Para trocar de provedor, mude ANALYZER_TYPE no .env.
Desative com ANALISE_IA=false.
"""

import os
import requests
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

PROMPT_ANALISE = """
Analise este edital de concurso público e extraia as seguintes informações
APENAS sobre os cargos da área de Tecnologia da Informação:

1. Nome do(s) cargo(s) de TI
2. Número de vagas (imediatas e cadastro reserva)
3. Salário
4. Requisitos (formação, experiência, certificações)
5. Conteúdo programático da prova (se disponível)
6. Data da prova (se disponível)
7. Regime de trabalho (CLT, estatutário, temporário)
8. Carga horária

Se não houver cargos de TI, responda apenas: "Sem cargos de TI neste edital."
Responda de forma objetiva e direta, sem introduções.
"""


class Analyzer(ABC):

    @abstractmethod
    def analisar(self, url_noticia):
        pass


class GeminiAnalyzer(Analyzer):

    def __init__(self):
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada no .env")
        self.client = genai.Client(api_key=api_key)
        self.modelo = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def analisar(self, url_noticia):
        pdf_url = self._buscar_link_edital(url_noticia)
        if not pdf_url:
            return "Link do edital não encontrado na página."

        pdf_bytes = self._baixar_pdf(pdf_url)
        if not pdf_bytes:
            return "Não foi possível baixar o edital."

        return self._enviar_para_gemini(pdf_bytes)

    def _buscar_link_edital(self, url):
        """Visita a página da notícia e pega o primeiro PDF de edital."""
        try:
            html = requests.get(url, timeout=30).text
            soup = BeautifulSoup(html, "html.parser")

            aside = soup.find("aside", id="links")
            if not aside:
                return None

            for pdf in aside.find_all("li", class_="pdf"):
                link = pdf.find("a", href=True)
                if link and "edital" in link.get_text(strip=True).lower():
                    return link["href"]

            return None
        except Exception:
            return None

    def _baixar_pdf(self, url):
        """Baixa o PDF e retorna os bytes."""
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 0:
                return resp.content
            return None
        except Exception:
            return None

    def _enviar_para_gemini(self, pdf_bytes):
        """Envia o PDF pro Gemini e retorna a análise."""
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.modelo,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                PROMPT_ANALISE,
            ],
        )
        return response.text


def criar_analisador():
    tipo = os.getenv("ANALYZER_TYPE", "gemini")

    if tipo == "gemini":
        return GeminiAnalyzer()
    else:
        raise ValueError(f"ANALYZER_TYPE '{tipo}' não suportado")