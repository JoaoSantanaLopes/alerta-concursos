import os
from dotenv import load_dotenv
from scraper_pci import buscar_concursos, filtrar_regiao, filtrar_por_area, filtrar_por_data
from repository import criar_repositorio, filtrar_novos, salvar_notificados
from notificar import criar_notificador

load_dotenv()

ANALISE_IA = os.getenv("ANALISE_IA", "false").lower() == "true"

if __name__ == "__main__":
    try:
        print("Buscando concursos...")
        df_todos = buscar_concursos()

        print("Filtrando região...")
        df_regiao = filtrar_regiao(df_todos)

        print("Filtrando por data...")
        df_regiao = filtrar_por_data(df_regiao)

        print("Verificando vagas por área...")
        df_area = filtrar_por_area(df_regiao)

        print("Verificando novos...")
        repo = criar_repositorio()
        df_novos = filtrar_novos(df_area, repo)

        if not df_novos.empty:
            if ANALISE_IA:
                from analisador import criar_analisador
                print("Analisando editais com IA...")
                analisador = criar_analisador()
                analises = []
                for _, row in df_novos.iterrows():
                    print(f"  Analisando: {row['Concurso']}...")
                    analise = analisador.analisar(row["Link"])
                    analises.append(analise)
                df_novos["Análise IA"] = analises

            print(f"Enviando {len(df_novos)} concurso(s)...")
            notificador = criar_notificador()
            notificador.enviar(df_novos)
            salvar_notificados(df_novos, repo)
        else:
            print("Nenhum concurso novo.")

        repo.fechar()
        print("Pronto.")

    except Exception as e:
        print(f"Erro: {e}")