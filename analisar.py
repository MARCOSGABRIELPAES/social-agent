"""Roda a analise em cima do banco e gera relatorio HTML + resumo.json.

    py analisar.py
    py analisar.py --dias 30
    py analisar.py --abrir      # abre o relatorio no navegador

O resumo.json e a ponte para a camada estrategica: e ele que a skill
/social-semanal le para montar a pauta da semana.
"""

import argparse
import json
import sys
import webbrowser
from datetime import datetime, timedelta, timezone

from social import briefing, config, db, metricas, relatorio

FUSO = timezone(timedelta(hours=-3))


def main():
    parser = argparse.ArgumentParser(description="Analisa e gera o relatorio")
    parser.add_argument("--dias", type=int, default=None,
                        help="janela de analise (padrao: config/perfis.json)")
    parser.add_argument("--abrir", action="store_true")
    args = parser.parse_args()

    dados = config.carregar()
    parametros = dict(dados["parametros"])
    if args.dias:
        parametros["janela_analise_dias"] = args.dias

    con = db.conectar()
    janela, carga = db.carregar_janela(con, dados["perfis"],
                                       parametros["janela_analise_dias"])
    analises, vazios = [], []
    for perfil in dados["perfis"]:
        posts, snaps = carga[perfil["username"]]
        if not posts and not snaps:
            vazios.append(perfil["username"])
            continue
        analises.append(metricas.analisar_perfil(perfil, posts, snaps, parametros))
    con.close()

    if vazios:
        print("! Sem dados para: {0}".format(", ".join(vazios)))
    if not analises:
        print("Banco vazio. Alimente primeiro:")
        print("  MODO AUTO   ->  py coletar.py")
        print("  MODO MANUAL ->  py importar.py --modelo")
        return 1

    comparacao = metricas.comparar(analises)
    agora = datetime.now(FUSO)
    carimbo = agora.strftime("%Y-%m-%d")

    # --- resumo.json: entrada da camada estrategica ------------------------
    resumo = {
        "gerado_em": agora.isoformat(),
        "janela_dias": janela,
        "parametros": parametros,
        "comparacao": comparacao,
        "perfis": analises,
    }
    caminho_json = config.DIR_DADOS / "resumo.json"
    caminho_json.write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")

    # --- briefing para IA --------------------------------------------------
    texto = briefing.gerar(analises, comparacao, janela)
    caminho_briefing = config.DIR_RELATORIOS / "briefing.md"
    caminho_briefing.write_text(texto, encoding="utf-8")

    # --- relatorio HTML ----------------------------------------------------
    html = relatorio.gerar(analises, comparacao, janela, texto)
    caminho_html = config.DIR_RELATORIOS / "relatorio-{0}.html".format(carimbo)
    caminho_html.write_text(html, encoding="utf-8")
    (config.DIR_RELATORIOS / "ultimo.html").write_text(html, encoding="utf-8")

    # Versao sem doctype/head/body, para publicar como pagina acessivel do celular.
    (config.DIR_RELATORIOS / "painel.html").write_text(
        relatorio.fragmento(analises, comparacao, janela, texto), encoding="utf-8")

    print("Relatorio: {0}".format(caminho_html))
    print("Resumo:    {0}".format(caminho_json))
    for analise in analises:
        r = analise["resumo"]
        print("  @{0}: {1} posts na semana | alcance mediano {2} | engaj. {3}".format(
            analise["username"], r["posts_semana"], r["alcance_mediano"],
            "{:.1%}".format(r["taxa_engajamento_mediana"] or 0)))

    if args.abrir:
        webbrowser.open(caminho_html.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
