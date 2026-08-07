"""Clientes da API do Instagram. Suporta as DUAS variantes da Meta.

  MODO FB  - "API do Instagram com login do Facebook" (graph.facebook.com).
             Um token cobre varias contas, mas exige que cada conta esteja
             vinculada a uma Pagina do Facebook.

  MODO IG  - "API do Instagram com login do Instagram" (graph.instagram.com).
             Dispensa Pagina, porem o token e por conta: um token para cada
             perfil.

O modo e detectado sozinho pelo token. Nada de scraping ou login com senha
em nenhum dos dois: so API oficial.
"""

import time

import requests

from . import config

BASE_FB = "https://graph.facebook.com"
BASE_IG = "https://graph.instagram.com"
TEMPO_LIMITE = 30

# A Meta rejeita a chamada inteira quando UMA metrica nao existe para aquele
# tipo de midia, e o conjunto valido muda a cada versao. Entao pedimos do mais
# completo para o mais basico e ficamos com o primeiro que responder.
METRICAS_POR_TIPO = {
    "REELS": [
        ["reach", "views", "likes", "comments", "shares", "saved",
         "total_interactions", "ig_reels_avg_watch_time"],
        ["reach", "views", "likes", "comments", "shares", "saved",
         "total_interactions"],
        ["reach", "saved", "total_interactions"],
        ["reach"],
    ],
    "STORY": [
        ["reach", "views", "replies", "profile_visits", "follows"],
        ["reach", "views", "replies"],
        ["reach"],
    ],
    "FEED": [
        ["reach", "views", "likes", "comments", "shares", "saved",
         "total_interactions", "profile_visits", "follows"],
        ["reach", "views", "likes", "comments", "shares", "saved",
         "total_interactions"],
        ["reach", "saved", "total_interactions"],
        ["reach"],
    ],
}

MAPA_METRICAS = {
    "reach": "alcance",
    "views": "views",
    "impressions": "views",
    "likes": "curtidas",
    "comments": "comentarios",
    "saved": "salvamentos",
    "shares": "compartilhamentos",
    "total_interactions": "interacoes",
    "profile_visits": "visitas_perfil",
    "follows": "seguidores_ganhos",
    "ig_reels_avg_watch_time": "tempo_medio_ms",
}


class ErroGraph(Exception):
    pass


class Cliente:
    """Fala com uma das duas APIs. `modo` e 'ig' ou 'fb'."""

    def __init__(self, token, modo):
        self.token = token
        self.modo = modo
        self.base = BASE_IG if modo == "ig" else BASE_FB

    # --- transporte --------------------------------------------------------

    def _get(self, caminho, parametros, tentativas=3):
        parametros = dict(parametros)
        parametros["access_token"] = self.token
        url = "{0}/{1}/{2}".format(self.base, config.versao_api(),
                                   caminho.lstrip("/"))
        for tentativa in range(tentativas):
            resposta = requests.get(url, params=parametros, timeout=TEMPO_LIMITE)
            if resposta.status_code == 200:
                return resposta.json()
            corpo = resposta.json() if resposta.content else {}
            erro = corpo.get("error", {})
            codigo = erro.get("code")
            # 4 e 17 sao limite de chamadas; 1 e 2 sao instabilidade da Meta.
            if codigo in (1, 2, 4, 17, 32, 613) and tentativa < tentativas - 1:
                time.sleep(5 * (tentativa + 1))
                continue
            raise ErroGraph("{0} em /{1}: {2}".format(
                resposta.status_code, caminho,
                erro.get("message", resposta.text[:200])))
        raise ErroGraph("falhou apos {0} tentativas: /{1}".format(
            tentativas, caminho))

    # --- descoberta --------------------------------------------------------

    def contas(self, paginas_conhecidas=None):
        """Contas do Instagram alcancaveis por este token.

        Devolve [{'ig_user_id': ..., 'username': ...}].

        Quando a Pagina esta dentro de um Portfolio Empresarial, a Meta some
        com ela em /me/accounts sem `business_management` - mas o acesso ao
        objeto continua valendo. Por isso, se a listagem vier vazia, tentamos
        os IDs de Pagina anotados no config.
        """
        if self.modo == "ig":
            dados = self._get("me", {"fields": "user_id,username"})
            ident = dados.get("user_id") or dados.get("id")
            if not ident:
                return []
            return [{"ig_user_id": str(ident),
                     "username": dados.get("username", "")}]

        encontradas = []
        dados = self._get("me/accounts",
                          {"fields": "instagram_business_account{id,username}",
                           "limit": 50})
        for pagina in dados.get("data", []):
            conta = pagina.get("instagram_business_account")
            if conta:
                encontradas.append({"ig_user_id": conta["id"],
                                    "username": conta.get("username", "")})
        if encontradas:
            return encontradas

        for pagina_id in (paginas_conhecidas or []):
            try:
                dados = self._get(str(pagina_id), {
                    "fields": "instagram_business_account{id,username}"})
            except ErroGraph:
                continue
            conta = dados.get("instagram_business_account")
            if conta:
                encontradas.append({"ig_user_id": conta["id"],
                                    "username": conta.get("username", "")})
        return encontradas

    def dados_da_conta(self, ig_user_id):
        campos = "username,followers_count,media_count"
        if self.modo == "fb":
            campos += ",follows_count"
        alvo = "me" if self.modo == "ig" else ig_user_id
        return self._get(alvo, {"fields": campos})

    # --- metricas ----------------------------------------------------------

    def insights_da_conta(self, ig_user_id, desde, ate):
        """Metricas diarias da conta. Tolera metricas indisponiveis."""
        alvo = "me" if self.modo == "ig" else ig_user_id
        resultado = {}
        combinacoes = [
            (["reach", "profile_views", "accounts_engaged", "total_interactions"],
             {"metric_type": "total_value"}),
            (["follower_count"], {}),
        ]
        for metricas, extras in combinacoes:
            parametros = {
                "metric": ",".join(metricas),
                "period": "day",
                "since": int(desde.timestamp()),
                "until": int(ate.timestamp()),
            }
            parametros.update(extras)
            try:
                dados = self._get("{0}/insights".format(alvo), parametros)
            except ErroGraph:
                continue
            for item in dados.get("data", []):
                nome = item.get("name")
                if "total_value" in item:
                    resultado[nome] = item["total_value"].get("value")
                else:
                    resultado[nome] = {v["end_time"][:10]: v["value"]
                                       for v in item.get("values", [])}
        return resultado

    def midias(self, ig_user_id, desde, limite_paginas=10):
        """Posts publicados a partir de `desde` (datetime com fuso)."""
        campos = ("id,caption,media_type,media_product_type,permalink,timestamp,"
                  "like_count,comments_count")
        parametros = {"fields": campos, "limit": 50, "since": int(desde.timestamp())}
        alvo = "me" if self.modo == "ig" else ig_user_id
        caminho = "{0}/media".format(alvo)
        coletados = []
        for _ in range(limite_paginas):
            dados = self._get(caminho, parametros)
            coletados.extend(dados.get("data", []))
            paginacao = dados.get("paging", {})
            proximo = paginacao.get("cursors", {}).get("after")
            if not proximo or not paginacao.get("next"):
                break
            parametros["after"] = proximo
        return coletados

    def insights_da_midia(self, media_id, produto):
        """Metricas de um post. Cai para conjuntos menores ate um funcionar."""
        chave = produto if produto in METRICAS_POR_TIPO else "FEED"
        for conjunto in METRICAS_POR_TIPO[chave]:
            try:
                dados = self._get("{0}/insights".format(media_id),
                                  {"metric": ",".join(conjunto)})
            except ErroGraph:
                continue
            saida = {}
            for item in dados.get("data", []):
                nome = MAPA_METRICAS.get(item.get("name"))
                if not nome:
                    continue
                valores = item.get("values") or []
                if valores:
                    saida[nome] = valores[0].get("value")
                elif "total_value" in item:
                    saida[nome] = item["total_value"].get("value")
            return saida
        return {}

    def dias_ate_expirar(self):
        """Dias restantes do token. None quando a API nao informa."""
        if self.modo == "ig":
            return None  # graph.instagram.com nao expoe debug_token
        try:
            dados = self._get("debug_token", {"input_token": self.token})
        except ErroGraph:
            return None
        expira = dados.get("data", {}).get("expires_at")
        if not expira:
            return 9999
        return max(0, int((expira - time.time()) / 86400))


def detectar(token):
    """Descobre a qual das duas APIs o token pertence.

    Testa o graph.instagram.com primeiro porque a resposta e inequivoca:
    so token de login do Instagram devolve `user_id` em /me.
    """
    for modo in ("ig", "fb"):
        cliente = Cliente(token, modo)
        try:
            cliente._get("me", {"fields": "id"})
            return cliente
        except ErroGraph:
            continue
    raise ErroGraph("o token nao respondeu nem em graph.instagram.com nem em "
                    "graph.facebook.com - provavelmente expirou ou foi revogado")
