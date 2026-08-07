"""Banco SQLite com o historico das duas contas.

O historico e o ativo mais valioso aqui: o Instagram so mostra os ultimos
dias em varios recortes, entao a cada coleta a gente carimba os numeros e
constroi uma serie que o app nao guarda.
"""

import sqlite3
from pathlib import Path

from . import config

CAMINHO = config.DIR_DADOS / "social.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfis (
    username    TEXT PRIMARY KEY,
    ig_user_id  TEXT,
    nome        TEXT,
    papel       TEXT
);

-- Uma linha por dia por conta. Serie historica da conta como um todo.
CREATE TABLE IF NOT EXISTS snapshots_conta (
    username         TEXT NOT NULL,
    data             TEXT NOT NULL,
    seguidores       INTEGER,
    alcance          INTEGER,
    visitas_perfil   INTEGER,
    contas_engajadas INTEGER,
    interacoes       INTEGER,
    novos_seguidores INTEGER,
    PRIMARY KEY (username, data)
);

CREATE TABLE IF NOT EXISTS posts (
    id           TEXT PRIMARY KEY,
    username     TEXT NOT NULL,
    publicado_em TEXT NOT NULL,
    tipo         TEXT,
    produto      TEXT,
    permalink    TEXT,
    legenda      TEXT,
    pilar        TEXT,
    origem       TEXT
);

-- Metricas sao re-coletadas: um post ganha alcance por semanas. Guardamos
-- cada leitura e usamos sempre a mais recente nas analises.
CREATE TABLE IF NOT EXISTS metricas_post (
    post_id           TEXT NOT NULL,
    coletado_em       TEXT NOT NULL,
    alcance           INTEGER,
    views             INTEGER,
    curtidas          INTEGER,
    comentarios       INTEGER,
    salvamentos       INTEGER,
    compartilhamentos INTEGER,
    interacoes        INTEGER,
    visitas_perfil    INTEGER,
    seguidores_ganhos INTEGER,
    tempo_medio_ms    INTEGER,
    PRIMARY KEY (post_id, coletado_em)
);

CREATE INDEX IF NOT EXISTS idx_posts_conta ON posts (username, publicado_em);
"""


def conectar():
    config.DIR_DADOS.mkdir(exist_ok=True)
    con = sqlite3.connect(CAMINHO)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    return con


def salvar_perfil(con, perfil):
    con.execute(
        "INSERT INTO perfis (username, ig_user_id, nome, papel) VALUES (?,?,?,?) "
        "ON CONFLICT(username) DO UPDATE SET ig_user_id=excluded.ig_user_id, "
        "nome=excluded.nome, papel=excluded.papel",
        (perfil["username"], perfil.get("ig_user_id"), perfil["nome"], perfil["papel"]),
    )


def salvar_snapshot(con, username, data, valores):
    con.execute(
        "INSERT INTO snapshots_conta (username, data, seguidores, alcance, "
        "visitas_perfil, contas_engajadas, interacoes, novos_seguidores) "
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(username, data) DO UPDATE SET "
        "seguidores=COALESCE(excluded.seguidores, seguidores), "
        "alcance=COALESCE(excluded.alcance, alcance), "
        "visitas_perfil=COALESCE(excluded.visitas_perfil, visitas_perfil), "
        "contas_engajadas=COALESCE(excluded.contas_engajadas, contas_engajadas), "
        "interacoes=COALESCE(excluded.interacoes, interacoes), "
        "novos_seguidores=COALESCE(excluded.novos_seguidores, novos_seguidores)",
        (
            username,
            data,
            valores.get("seguidores"),
            valores.get("alcance"),
            valores.get("visitas_perfil"),
            valores.get("contas_engajadas"),
            valores.get("interacoes"),
            valores.get("novos_seguidores"),
        ),
    )


def salvar_post(con, post):
    con.execute(
        "INSERT INTO posts (id, username, publicado_em, tipo, produto, permalink, "
        "legenda, pilar, origem) VALUES (?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET legenda=excluded.legenda, "
        "pilar=excluded.pilar, permalink=excluded.permalink",
        (
            post["id"],
            post["username"],
            post["publicado_em"],
            post.get("tipo"),
            post.get("produto"),
            post.get("permalink"),
            post.get("legenda"),
            post.get("pilar"),
            post.get("origem", "api"),
        ),
    )


def salvar_metricas(con, post_id, coletado_em, m):
    con.execute(
        "INSERT OR REPLACE INTO metricas_post (post_id, coletado_em, alcance, views, "
        "curtidas, comentarios, salvamentos, compartilhamentos, interacoes, "
        "visitas_perfil, seguidores_ganhos, tempo_medio_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            post_id,
            coletado_em,
            m.get("alcance"),
            m.get("views"),
            m.get("curtidas"),
            m.get("comentarios"),
            m.get("salvamentos"),
            m.get("compartilhamentos"),
            m.get("interacoes"),
            m.get("visitas_perfil"),
            m.get("seguidores_ganhos"),
            m.get("tempo_medio_ms"),
        ),
    )


def posts_com_metricas(con, username, desde):
    """Posts do periodo, cada um com a leitura de metricas mais recente."""
    cur = con.execute(
        """
        SELECT p.*, m.alcance, m.views, m.curtidas, m.comentarios, m.salvamentos,
               m.compartilhamentos, m.interacoes, m.visitas_perfil,
               m.seguidores_ganhos, m.tempo_medio_ms, m.coletado_em
        FROM posts p
        LEFT JOIN metricas_post m ON m.post_id = p.id
           AND m.coletado_em = (SELECT MAX(coletado_em) FROM metricas_post
                                WHERE post_id = p.id)
        WHERE p.username = ? AND p.publicado_em >= ?
        ORDER BY p.publicado_em DESC
        """,
        (username, desde),
    )
    return [dict(linha) for linha in cur.fetchall()]


def carregar_janela(con, perfis, dias_preferidos):
    """Carrega posts e snapshots, alargando a janela quando ela vem vazia.

    Uma conta parada ha um ano nao pode gerar painel em branco: sem isso o
    veredito diria "nenhum post publicado" para quem so esta em pausa, que e
    um diagnostico completamente diferente. Comeca pela janela preferida e
    so abre mais se nao houver nada para medir.
    """
    from datetime import datetime, timedelta, timezone

    fuso = timezone(timedelta(hours=-3))
    candidatas = sorted({dias_preferidos, 400, 1300})

    for dias in candidatas:
        marco = datetime.now(fuso) - timedelta(days=dias)
        carga = {}
        total = 0
        for perfil in perfis:
            posts = posts_com_metricas(con, perfil["username"], marco.isoformat())
            snaps = snapshots(con, perfil["username"], marco.date().isoformat())
            carga[perfil["username"]] = (posts, snaps)
            total += len(posts)
        if total:
            return dias, carga

    return dias_preferidos, carga


def snapshots(con, username, desde):
    cur = con.execute(
        "SELECT * FROM snapshots_conta WHERE username = ? AND data >= ? ORDER BY data",
        (username, desde),
    )
    return [dict(linha) for linha in cur.fetchall()]
