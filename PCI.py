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
    html = requests.get(URL, timeout=30).text
    inicio = html.find(f'<div class="uf">{ESTADO}</div>')
    fim = html.find('<div class="uf">', inicio + 1)
    trecho = BeautifulSoup(html[inicio:fim], "html.parser")

    concursos = []
    for item in trecho.find_all(class_="ca"):
        link_tag = item.find("a", href=True)
        cd_tag = item.find(class_="cd")
        data_tag = str(item.find(class_="ce") or "")
        detalhes = str(cd_tag or "")

        # Extrai o nome do cargo do primeiro span dentro de .cd
        cargo = ""
        if cd_tag:
            span = cd_tag.find("span")
            if span:
                cargo = span.find(string=True, recursive=False)
                cargo = cargo.strip() if cargo else ""

        concursos.append({
            "Concurso": link_tag.text.strip() if link_tag else "",
            "Cargo": cargo,
            "Vagas": "".join(re.findall(r"(\d+) vaga", detalhes)) or "-",
            "Nível": "/".join(re.findall(r"Superior|Médio", detalhes)) or "-",
            "Salário Até": "".join(re.findall(r"R\$ *[\d.,]+", detalhes)) or "-",
            "Inscrição Até": "".join(re.findall(r"\d+/\d+/\d+", data_tag)) or "-",
            "Link": link_tag["href"] if link_tag else "",
        })

    return pd.DataFrame(concursos)


def filtrar_regiao(df):
    padrao = "|".join(CIDADES + ORGAOS)
    return df[df["Concurso"].str.contains(padrao, case=False, na=False)].reset_index(drop=True)


def buscar_cargos(url):
    try:
        html = requests.get(url, timeout=30).text
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