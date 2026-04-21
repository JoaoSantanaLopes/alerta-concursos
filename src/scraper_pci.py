"""
Scraper PCI Concursos.
Busca concursos por estado, filtra por região e área de interesse.
Os filtros são passados pelo chamador.
"""
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup


URL = "https://www.pciconcursos.com.br/concursos/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


def buscar_concursos(estado: str) -> pd.DataFrame:
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    uf_div = soup.find("div", class_="uf", string=estado)
    if not uf_div:
        return pd.DataFrame()

    concursos = []
    for item in uf_div.find_all_next(class_="ca"):
        uf_anterior = item.find_previous("div", class_="uf")
        if uf_anterior and uf_anterior.get_text(strip=True) != estado:
            break

        link_tag = item.find("a", href=True)
        cd_tag = item.find(class_="cd")
        ce_tag = item.find(class_="ce")

        cargo = ""
        if cd_tag:
            span = cd_tag.find("span")
            if span:
                texto = span.find(string=True, recursive=False)
                cargo = texto.strip() if texto else ""

        concursos.append({
            "Concurso": link_tag.get_text(strip=True) if link_tag else "",
            "Cargo": cargo,
            "Vagas": "".join(re.findall(r"(\d+) vaga", cd_tag.get_text() if cd_tag else "")) or "-",
            "Nível": "/".join(re.findall(r"Superior|Médio", cd_tag.get_text() if cd_tag else "")) or "-",
            "Salário Até": "".join(re.findall(r"R\$ *[\d.,]+", cd_tag.get_text() if cd_tag else "")) or "-",
            "Inscrição Até": "".join(re.findall(r"\d+/\d+/\d+", ce_tag.get_text() if ce_tag else "")) or "-",
            "Link": link_tag["href"] if link_tag else "",
        })

    return pd.DataFrame(concursos)


def filtrar_regiao(df: pd.DataFrame, cidades: list[str], orgaos: list[str]) -> pd.DataFrame:
    padrao = "|".join(cidades + orgaos)
    return df[df["Concurso"].str.contains(padrao, case=False, na=False)].reset_index(drop=True)


def buscar_cargos(url: str) -> list[str]:
    try:
        html = requests.get(url, headers=HEADERS, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article", id="noticia")
        if not article:
            return []
        body = article.find(attrs={"itemprop": "articleBody"})
        if not body:
            return []
        ul = body.find("ul")
        if not ul:
            return []
        return [li.get_text(strip=True) for li in ul.find_all("li")]
    except Exception as e:
        print(f"  ⚠️ Erro ao buscar cargos de {url}: {e}")
        return []


def tem_vaga(cargos: list[str], keywords: list[str]) -> list[str]:
    return [c for c in cargos if any(kw in c.lower() for kw in keywords)]


def filtrar_por_area(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    resultados = []

    for _, row in df.iterrows():
        cargos_encontrados = tem_vaga(buscar_cargos(row["Link"]), keywords)
        if cargos_encontrados:
            linha = row.to_dict()
            linha["Cargos Encontrados"] = " | ".join(cargos_encontrados)
            resultados.append(linha)
            print(f"  ✅ {row['Concurso']}")
        time.sleep(0.3)

    return pd.DataFrame(resultados) if resultados else pd.DataFrame()


def filtrar_por_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove concursos cuja inscrição já encerrou."""
    from datetime import date

    def ainda_aberto(data_str):
        if not data_str or data_str == "-":
            return True
        try:
            partes = data_str.split("/")
            return date(int(partes[2]), int(partes[1]), int(partes[0])) >= date.today()
        except (ValueError, IndexError):
            return True

    return df[df["Inscrição Até"].apply(ainda_aberto)].reset_index(drop=True)