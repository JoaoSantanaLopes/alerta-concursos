"""
Módulo de análise de editais por IA.
Recebe preferências e credenciais via Config.
"""
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
        try:
            return self._enviar_para_gemini(pdf_bytes)
        except Exception as e:
            return f"⚠️ Erro ao analisar edital: {type(e).__name__}: {e}"

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
        return GeminiAnalyzer(cfg.gemini_api_key, cfg.modelo, cfg.prompt)
    raise ValueError(f"analise_ia.tipo '{cfg.tipo}' não suportado")