"""MODO AUTO: puxa tudo da API oficial da Meta e grava no banco.

    py coletar.py                 # ultimos 90 dias das duas contas
    py coletar.py --dias 30
    py coletar.py --perfil bombeiro_ia
    py coletar.py --descobrir     # so preenche os ig_user_id no config

Funciona com as duas variantes da API (login do Facebook ou login do
Instagram). O modo e detectado pelo token, sem voce precisar declarar.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

from social import classificar, config, db, graph

FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo


def token_do_perfil(perfil):
    """Token especifico do perfil, ou o global como reserva.

    No modo login do Instagram cada conta tem seu proprio token; no modo
    login do Facebook um token so cobre todas.
    """
    especifico = os.environ.get(
        "IG_TOKEN_" + perfil["username"].upper(), "").strip()
    return especifico or config.token()


def cliente_do_perfil(perfil):
    token = token_do_perfil(perfil)
    if not token:
        return None
    return graph.detectar(token)


def descobrir_ids(dados):
    """Preenche ig_user_id em config/perfis.json sem o usuario ter que cacar."""
    vistos = {}
    achou_algum = False

    for perfil in dados["perfis"]:
        try:
            cliente = cliente_do_perfil(perfil)
        except graph.ErroGraph as erro:
            print("  ! {0}: {1}".format(perfil["username"], erro))
            continue
        if cliente is None:
            continue
        try:
            for conta in cliente.contas(dados.get("paginas_fb")):
                vistos[conta["username"].lower()] = conta["ig_user_id"]
        except graph.ErroGraph as erro:
            print("  ! {0}: {1}".format(perfil["username"], erro))

    if not vistos:
        print("  ! Nenhum token enxergou conta profissional do Instagram.")
        print("    No modo login do Facebook, a conta precisa estar vinculada")
        print("    a uma Pagina. No modo login do Instagram, basta ser conta")
        print("    Profissional. Ver README.md.")
        return False

    for perfil in dados["perfis"]:
        id_conta = vistos.get(perfil["username"].lower())
        if id_conta:
            perfil["ig_user_id"] = id_conta
            achou_algum = True
            print("  + {0} -> {1}".format(perfil["username"], id_conta))
        else:
            print("  ! {0} nao apareceu. Contas visiveis: {1}".format(
                perfil["username"], ", ".join(vistos) or "(nenhuma)"))

    if achou_algum:
        config.salvar(dados)
        print("  config/perfis.json atualizado.")
    return achou_algum


def coletar_perfil(con, perfil, dias):
    username = perfil["username"]
    ig_id = perfil.get("ig_user_id")
    if not ig_id:
        print("  ! {0} sem ig_user_id. Rode: py coletar.py --descobrir".format(
            username))
        return 0

    try:
        cliente = cliente_do_perfil(perfil)
    except graph.ErroGraph as erro:
        print("  ! {0}: {1}".format(username, erro))
        return 0
    if cliente is None:
        print("  ! {0} sem token. Ver .env".format(username))
        return 0

    agora = datetime.now(FUSO)
    desde = agora - timedelta(days=dias)
    hoje = agora.date().isoformat()

    db.salvar_perfil(con, perfil)

    # --- conta -------------------------------------------------------------
    try:
        basico = cliente.dados_da_conta(ig_id)
    except graph.ErroGraph as erro:
        print("  ! {0}: {1}".format(username, erro))
        return 0

    insights = cliente.insights_da_conta(ig_id, desde, agora)
    db.salvar_snapshot(con, username, hoje, {
        "seguidores": basico.get("followers_count"),
        "alcance": insights.get("reach"),
        "visitas_perfil": insights.get("profile_views"),
        "contas_engajadas": insights.get("accounts_engaged"),
        "interacoes": insights.get("total_interactions"),
    })
    # follower_count vem como serie diaria: preenche o historico retroativo.
    serie = insights.get("follower_count")
    if isinstance(serie, dict):
        for data, novos in serie.items():
            db.salvar_snapshot(con, username, data, {"novos_seguidores": novos})

    # --- posts -------------------------------------------------------------
    posts = cliente.midias(ig_id, desde)
    for post in posts:
        produto = post.get("media_product_type") or "FEED"
        legenda = post.get("caption") or ""
        db.salvar_post(con, {
            "id": post["id"],
            "username": username,
            "publicado_em": post.get("timestamp", ""),
            "tipo": post.get("media_type"),
            "produto": produto,
            "permalink": post.get("permalink"),
            "legenda": legenda,
            "pilar": classificar.detectar_pilar(legenda, perfil["pilares"]),
            "origem": "api",
        })
        metricas = cliente.insights_da_midia(post["id"], produto)
        metricas.setdefault("curtidas", post.get("like_count"))
        metricas.setdefault("comentarios", post.get("comments_count"))
        if metricas.get("interacoes") is None:
            partes = [metricas.get(k) or 0 for k in
                      ("curtidas", "comentarios", "salvamentos",
                       "compartilhamentos")]
            metricas["interacoes"] = sum(partes)
        db.salvar_metricas(con, post["id"], hoje, metricas)

    con.commit()
    print("  + {0} [{1}]: {2} seguidores, {3} posts nos ultimos {4} dias".format(
        username, cliente.modo, basico.get("followers_count", "?"),
        len(posts), dias))
    return len(posts)


def main():
    parser = argparse.ArgumentParser(description="Coleta metricas via API oficial")
    parser.add_argument("--dias", type=int, default=90)
    parser.add_argument("--perfil", default=None, help="so um username")
    parser.add_argument("--descobrir", action="store_true",
                        help="so preenche os ig_user_id e sai")
    args = parser.parse_args()

    dados = config.carregar()

    tem_token = any(token_do_perfil(p) for p in dados["perfis"])
    if not tem_token:
        print("Nenhum token no .env - modo AUTO indisponivel.")
        print("Use o modo manual:  py importar.py --modelo")
        return 1

    print("Coletando da API oficial do Instagram...")

    if args.descobrir:
        return 0 if descobrir_ids(dados) else 1

    if any(not p.get("ig_user_id") for p in dados["perfis"]):
        print("  Descobrindo os ids das contas...")
        descobrir_ids(dados)
        dados = config.carregar()

    con = db.conectar()
    total = 0
    for perfil in dados["perfis"]:
        if args.perfil and perfil["username"] != args.perfil:
            continue
        total += coletar_perfil(con, perfil, args.dias)
    con.close()

    print("Pronto. {0} posts coletados. Agora rode:  py analisar.py".format(total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
