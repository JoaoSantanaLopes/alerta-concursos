"""
Scraper PCI Concursos
Busca concursos por estado, filtra por região e área de interesse.
Edite as variáveis abaixo para personalizar.
"""

import re
import time
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# === CONFIGURAÇÃO ===

URL = "https://www.pciconcursos.com.br/concursos/"
ESTADO = "MINAS GERAIS"
OUTPUT_DIR = "output"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

CIDADES = [
    "Belo Horizonte", "Betim", "Contagem", "Ribeirão das Neves",
    "Santa Luzia", "Ibirité", "Sabará", "Nova Lima", "Vespasiano",
    "Pedro Leopoldo", "Lagoa Santa", "Matozinhos", "Esmeraldas",
    "Brumadinho", "Caeté", "Igarapé", "Juatuba", "Mateus Leme",
    "São José da Lapa", "Confins", "Mario Campos", "Sarzedo",
    "Raposos", "Rio Acima", "Nova União", "Taquaraçu de Minas",
    "Jaboticatubas", "Baldim", "Capim Branco", "Florestal",
    "Itabirito", "Itaguara", "Itatiaiuçu", "Rio Manso",
    "São Joaquim de Bicas",
]

ORGAOS = [
    "FHEMIG", "CEMIG", "COPASA", "CBMMG", "PM - Polícia Militar",
    "PC - Polícia Civil", "SEJUSP", "SEPLAG", "SEE", "SES ",
    "TJ - Tribunal de Justiça", "TRE - ", "TRF - ", "TRT - ",
    "MPE - ", "MP - Ministério Público", "TCE - ", "TCEMG",
    "DPE - ", "Defensoria Pública", "AGE - ", "IPSEMG", "JUCEMG",
    "Prodemge", "Prodabel", "MGS ", "UFMG", "CEFET", "IFMG",
    "EBSERH", "BDMG", "Hemominas",
    "Corpo de Bombeiros Militar de Minas",
    "Polícia Militar de Minas", "Polícia Civil de Minas",
    "Tribunal de Justiça do Estado de Minas",
    "Secretaria de Estado",
]

KEYWORDS = [
    "tecnologia da informação", "analista de sistemas",
    "analista de ti", "analista de informática",
    "técnico em informática", "técnico de informática",
    "técnico de tecnologia", "técnico em tecnologia",
    "suporte de ti", "suporte em ti",
    "infraestrutura de ti", "segurança da informação",
    "banco de dados", "administrador de banco",
    "desenvolvedor", "programador", "programação",
    "ciência de dados", "cientista de dados",
    "governança de ti", "gestão de ti",
    "sistemas de informação", "engenheiro de software",
    "devops", "web designer", "webdesigner",
    "informática",
]

# === FUNÇÕES ===


def buscar_concursos():
    html = requests.get(URL, headers=HEADERS, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    # Encontra a div do estado pelo texto
    uf_div = soup.find("div", class_="uf", string=ESTADO)
    if not uf_div:
        return pd.DataFrame()

    # Pega todos os concursos entre esse estado e o próximo
    concursos = []
    for item in uf_div.find_all_next(class_="ca"):
        # Para quando chegar no próximo estado
        uf_anterior = item.find_previous("div", class_="uf")
        if uf_anterior and uf_anterior.get_text(strip=True) != ESTADO:
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


def filtrar_regiao(df):
    padrao = "|".join(CIDADES + ORGAOS)
    return df[df["Concurso"].str.contains(padrao, case=False, na=False)].reset_index(drop=True)


def buscar_cargos(url):
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
    except Exception:
        return []


def tem_vaga(cargos):
    return [c for c in cargos if any(kw in c.lower() for kw in KEYWORDS)]


def filtrar_por_area(df):
    resultados = []

    for _, row in df.iterrows():
        cargos_encontrados = tem_vaga(buscar_cargos(row["Link"]))
        if cargos_encontrados:
            linha = row.to_dict()
            linha["Cargos Encontrados"] = " | ".join(cargos_encontrados)
            resultados.append(linha)
            print(f"  ✅ {row['Concurso']}")
        time.sleep(0.3)

    return pd.DataFrame(resultados) if resultados else pd.DataFrame()


def filtrar_por_data(df):
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


# === EXECUÇÃO ===

if __name__ == "__main__":
    print("Buscando concursos...")
    df_todos = buscar_concursos()

    print("Filtrando região...")
    df_regiao = filtrar_regiao(df_todos)

    print("Verificando vagas por área...")
    df_area = filtrar_por_area(df_regiao)

    def salvar(df, nome):
        colunas = [c for c in df.columns if c != "Link"] + ["Link"]
        df[colunas].to_csv(f"{OUTPUT_DIR}/{nome}", index=False, encoding="utf-8")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    salvar(df_todos, "concursos_estado.csv")
    salvar(df_regiao, "concursos_regiao.csv")
    if not df_area.empty:
        salvar(df_area, "concursos_area.csv")

    print(f"Pronto: {len(df_todos)} estado | {len(df_regiao)} região | {len(df_area)} na área")