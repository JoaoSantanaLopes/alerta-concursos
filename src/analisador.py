"""
Módulo de análise de editais por IA.
Tipo de analisador, modelo e prompt vêm do config.yaml.
Credencial (API key) vem do .env.
"""
import os
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
from config import AnaliseIAConfig

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


class Analyzer(ABC):
    @abstractmethod
    def analisar(self, url_noticia: str) -> str:
        pass

    def _buscar_link_edital(self, url):
        """Visita a página da notícia e pega o primeiro PDF de edital."""
        try:
            html = requests.get(url, headers=HEADERS, timeout=30).text
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
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code == 200 and len(resp.content) > 0:
                return resp.content
            return None
        except Exception:
            return None

class GeminiAnalyzer(Analyzer):
    def __init__(self, api_key: str, modelo: str, prompt: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.modelo = modelo
        self.prompt = prompt

    def analisar(self, url_noticia):
        pdf_url = self._buscar_link_edital(url_noticia)
        if not pdf_url:
            return "Link do edital não encontrado na página."
        pdf_bytes = self._baixar_pdf(pdf_url)
        if not pdf_bytes:
            return "Não foi possível baixar o edital."
        return self._enviar_para_gemini(pdf_bytes)

    def _enviar_para_gemini(self, pdf_bytes):
        from google.genai import types
        response = self.client.models.generate_content(
            model=self.modelo,
            contents=[
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                self.prompt,
            ],
        )
        return response.text


def criar_analisador(cfg: AnaliseIAConfig) -> Analyzer:
    if cfg.tipo == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não definida no .env")
        return GeminiAnalyzer(api_key, cfg.modelo, cfg.prompt)

    raise ValueError(f"analise_ia.tipo '{cfg.tipo}' não suportado")