from config import Config
from scraper_pci import (
    buscar_concursos,
    filtrar_regiao,
    filtrar_por_area,
    filtrar_por_data,
)
from repository import criar_repositorio, filtrar_novos, salvar_notificados
from notificar import criar_notificador


def main():
    cfg = Config.load()

    print("Buscando concursos...")
    df_todos = buscar_concursos(cfg.regiao.estado)

    print("Filtrando região...")
    df_regiao = filtrar_regiao(df_todos, cfg.regiao.cidades, cfg.regiao.orgaos)

    print("Filtrando por data...")
    df_regiao = filtrar_por_data(df_regiao)

    print("Verificando vagas por área...")
    df_area = filtrar_por_area(df_regiao, cfg.area.keywords)

    print("Verificando novos...")
    repo = criar_repositorio(cfg.banco)
    try:
        df_novos = filtrar_novos(df_area, repo)

        if df_novos.empty:
            print("Nenhum concurso novo.")
            return

        if cfg.analise_ia.habilitado:
            from analisador import criar_analisador
            print("Analisando editais com IA...")
            analisador = criar_analisador(cfg.analise_ia)
            df_novos["Análise IA"] = [
                analisador.analisar(row["Link"])
                for _, row in df_novos.iterrows()
            ]

        print(f"Enviando {len(df_novos)} concurso(s)...")
        notificador = criar_notificador(cfg.notificacao)
        notificador.enviar(df_novos)
        salvar_notificados(df_novos, repo)
    finally:
        repo.fechar()

    print("Pronto.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro: {e}")