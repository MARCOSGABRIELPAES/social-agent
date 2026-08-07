"""MODO MANUAL: importa um CSV quando ainda nao ha token da API.

    py importar.py --modelo                          # cria o CSV de exemplo
    py importar.py dados/meus_posts.csv --perfil bombeiro_ia
    py importar.py export_metricool.csv              # detecta as colunas sozinho
    py importar.py --seguidores bombeiro_ia=1240     # so atualiza o total

Aceita o export do Metricool, do Later e o modelo proprio. As colunas sao
reconhecidas por apelido, entao a ordem e o nome exato nao importam.
"""

import argparse
import csv
import sys
from datetime import datetime, timezone, timedelta

from social import classificar, config, db

FUSO = timezone(timedelta(hours=-3))

# Cada campo interno e os nomes de coluna que ja vi na pratica.
APELIDOS = {
    "publicado_em": ["data", "date", "datetime", "data de publicacao", "published",
                     "publicado em", "fecha", "timestamp", "data/hora"],
    "legenda": ["legenda", "texto", "caption", "text", "conteudo", "descricao",
                "post", "mensagem"],
    "produto": ["tipo", "type", "formato", "media type", "tipo de post",
                "media_product_type", "content type"],
    "permalink": ["link", "url", "permalink", "post url", "link do post"],
    "alcance": ["alcance", "reach", "contas alcancadas", "alcance total"],
    "views": ["views", "visualizacoes", "impressoes", "impressions", "reproducoes",
              "plays", "visualizacoes do video"],
    "curtidas": ["curtidas", "likes", "gostos", "me gusta"],
    "comentarios": ["comentarios", "comments", "comentarios recebidos"],
    "salvamentos": ["salvamentos", "salvos", "saved", "saves", "guardados"],
    "compartilhamentos": ["compartilhamentos", "shares", "compartilhado",
                          "compartilhamento", "envios"],
    "interacoes": ["interacoes", "interactions", "engajamento", "engagement",
                   "total de interacoes", "total interactions"],
    "visitas_perfil": ["visitas ao perfil", "profile visits", "visitas de perfil",
                       "cliques no perfil"],
    "seguidores_ganhos": ["seguidores ganhos", "follows", "novos seguidores",
                          "seguidores"],
    "username": ["perfil", "conta", "username", "account", "profile"],
}

MODELO = """publicado_em,perfil,tipo,legenda,alcance,views,curtidas,comentarios,salvamentos,compartilhamentos,link
2026-08-04 20:00,bombeiro_ia,REELS,"3 erros de AVCB que interditam a obra",4200,6100,310,24,88,41,https://instagram.com/p/exemplo1
2026-08-05 12:30,marcosgabriel_ia,FEED,"O que aprendi automatizando laudo tecnico com IA",1850,2100,140,19,52,12,https://instagram.com/p/exemplo2
"""


def normalizar_cabecalho(nome):
    return classificar.normalizar((nome or "").replace("_", " ").strip())


def mapear_colunas(cabecalho):
    """De nome de coluna do arquivo -> campo interno."""
    mapa = {}
    for coluna in cabecalho:
        alvo = normalizar_cabecalho(coluna)
        for campo, apelidos in APELIDOS.items():
            if alvo in [classificar.normalizar(a) for a in apelidos]:
                mapa[coluna] = campo
                break
    return mapa


def para_numero(valor):
    if valor is None:
        return None
    texto = str(valor).strip().replace(".", "").replace(",", ".").replace("%", "")
    if not texto or texto in ("-", "N/A", "n/a"):
        return None
    try:
        return int(round(float(texto)))
    except ValueError:
        return None


FORMATOS_DATA = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S+0000",
]


def para_data(valor):
    texto = (valor or "").strip()
    for formato in FORMATOS_DATA:
        try:
            quando = datetime.strptime(texto, formato)
            if quando.tzinfo is None:
                quando = quando.replace(tzinfo=FUSO)
            return quando.isoformat()
        except ValueError:
            continue
    return None


def normalizar_produto(valor):
    alvo = classificar.normalizar(valor)
    if "reel" in alvo or "video" in alvo:
        return "REELS"
    if "stor" in alvo:
        return "STORY"
    if "carro" in alvo or "album" in alvo or "carousel" in alvo:
        return "FEED"
    return "FEED"


def importar_csv(caminho, dados, perfil_padrao):
    con = db.conectar()
    hoje = datetime.now(FUSO).date().isoformat()
    pilares_por_perfil = {p["username"]: p["pilares"] for p in dados["perfis"]}
    validos = set(pilares_por_perfil)

    with open(caminho, newline="", encoding="utf-8-sig") as arquivo:
        amostra = arquivo.read(4096)
        arquivo.seek(0)
        try:
            dialeto = csv.Sniffer().sniff(amostra, delimiters=",;\t")
        except csv.Error:
            dialeto = csv.excel
        leitor = csv.DictReader(arquivo, dialect=dialeto)
        mapa = mapear_colunas(leitor.fieldnames or [])
        if "publicado_em" not in mapa.values():
            print("! Nao achei uma coluna de data em: {0}".format(leitor.fieldnames))
            print("  Renomeie a coluna para 'publicado_em' ou 'data'.")
            return 1

        importados, ignorados = 0, 0
        for numero, linha in enumerate(leitor, start=2):
            registro = {}
            for coluna, campo in mapa.items():
                registro[campo] = linha.get(coluna)

            quando = para_data(registro.get("publicado_em"))
            if not quando:
                ignorados += 1
                continue

            username = (registro.get("username") or perfil_padrao or "").strip()
            username = username.lstrip("@")
            if username not in validos:
                if perfil_padrao in validos:
                    username = perfil_padrao
                else:
                    print("! linha {0}: perfil '{1}' desconhecido. Use --perfil.".format(
                        numero, username or "(vazio)"))
                    ignorados += 1
                    continue

            legenda = registro.get("legenda") or ""
            permalink = registro.get("permalink") or ""
            # Sem id da API, o id estavel vira o link ou data+perfil.
            post_id = permalink.strip() or "manual:{0}:{1}".format(username, quando)

            db.salvar_post(con, {
                "id": post_id,
                "username": username,
                "publicado_em": quando,
                "tipo": normalizar_produto(registro.get("produto")),
                "produto": normalizar_produto(registro.get("produto")),
                "permalink": permalink,
                "legenda": legenda,
                "pilar": classificar.detectar_pilar(legenda, pilares_por_perfil[username]),
                "origem": "manual",
            })

            metricas = {campo: para_numero(registro.get(campo)) for campo in
                        ("alcance", "views", "curtidas", "comentarios", "salvamentos",
                         "compartilhamentos", "interacoes", "visitas_perfil",
                         "seguidores_ganhos")}
            if metricas.get("interacoes") is None:
                partes = [metricas.get(k) or 0 for k in
                          ("curtidas", "comentarios", "salvamentos", "compartilhamentos")]
                metricas["interacoes"] = sum(partes) or None
            db.salvar_metricas(con, post_id, hoje, metricas)
            importados += 1

    con.commit()
    con.close()
    print("Importado: {0} posts ({1} linhas ignoradas).".format(importados, ignorados))
    print("Colunas reconhecidas: {0}".format(", ".join(sorted(set(mapa.values())))))
    print("Agora rode:  py analisar.py")
    return 0


def atualizar_seguidores(pares, dados):
    con = db.conectar()
    hoje = datetime.now(FUSO).date().isoformat()
    validos = {p["username"] for p in dados["perfis"]}
    for par in pares:
        username, _, valor = par.partition("=")
        username = username.strip().lstrip("@")
        if username not in validos:
            print("! perfil desconhecido: {0}".format(username))
            continue
        db.salvar_snapshot(con, username, hoje,
                           {"seguidores": para_numero(valor)})
        print("+ {0}: {1} seguidores em {2}".format(username, valor.strip(), hoje))
    con.commit()
    con.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description="Importa metricas de um CSV")
    parser.add_argument("arquivo", nargs="?", help="caminho do CSV")
    parser.add_argument("--perfil", default=None,
                        help="username quando o CSV nao tem coluna de perfil")
    parser.add_argument("--modelo", action="store_true",
                        help="cria dados/modelo_import.csv e sai")
    parser.add_argument("--seguidores", nargs="+", metavar="PERFIL=N",
                        help="atualiza o total de seguidores de hoje")
    args = parser.parse_args()

    dados = config.carregar()

    if args.modelo:
        destino = config.DIR_DADOS / "modelo_import.csv"
        destino.write_text(MODELO, encoding="utf-8")
        print("Modelo criado em: {0}".format(destino))
        print("Preencha uma linha por post e rode:  py importar.py {0}".format(destino))
        return 0

    if args.seguidores:
        return atualizar_seguidores(args.seguidores, dados)

    if not args.arquivo:
        parser.print_help()
        return 1

    return importar_csv(args.arquivo, dados, args.perfil)


if __name__ == "__main__":
    sys.exit(main())
