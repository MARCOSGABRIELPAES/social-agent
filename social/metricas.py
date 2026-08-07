"""Motor de analise: transforma numeros crus em leitura de desempenho.

Regra que guia o modulo: mediana em vez de media em quase tudo. Um unico
post viral distorce a media e faz o perfil parecer melhor do que e - a
mediana mostra o desempenho que voce realmente entrega toda semana.
"""

from datetime import datetime, timedelta, timezone
from statistics import median

FUSO = timezone(timedelta(hours=-3))

DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
FAIXAS = [(6, 9, "06-09"), (9, 12, "09-12"), (12, 15, "12-15"),
          (15, 18, "15-18"), (18, 21, "18-21"), (21, 24, "21-00")]


def _num(valor):
    return valor if isinstance(valor, (int, float)) else 0


def _taxa(numerador, denominador):
    n, d = _num(numerador), _num(denominador)
    return round(n / d, 4) if d else None


def _mediana(valores):
    limpos = [v for v in valores if v]
    return median(limpos) if limpos else 0


def _faixa_da_hora(hora):
    for inicio, fim, rotulo in FAIXAS:
        if inicio <= hora < fim:
            return rotulo
    return "00-06"


def _quando(post):
    texto = post.get("publicado_em") or ""
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=FUSO)
    return quando.astimezone(FUSO)


def enriquecer(posts):
    """Adiciona as taxas derivadas e o indice relativo a cada post."""
    base_alcance = _mediana([_num(p.get("alcance")) for p in posts])
    enriquecidos = []
    for post in posts:
        quando = _quando(post)
        alcance = _num(post.get("alcance"))
        item = dict(post)
        item["quando"] = quando
        item["dia_semana"] = DIAS[quando.weekday()] if quando else None
        item["hora"] = quando.hour if quando else None
        item["faixa"] = _faixa_da_hora(quando.hour) if quando else None
        item["taxa_engajamento"] = _taxa(post.get("interacoes"), alcance)
        item["taxa_salvamento"] = _taxa(post.get("salvamentos"), alcance)
        item["taxa_compartilhamento"] = _taxa(post.get("compartilhamentos"), alcance)
        item["taxa_comentario"] = _taxa(post.get("comentarios"), alcance)
        item["taxa_visita"] = _taxa(post.get("visitas_perfil"), alcance)
        # Indice 1.0 = alcance igual a mediana do perfil. 2.0 = dobro dela.
        item["indice_alcance"] = round(alcance / base_alcance, 2) if base_alcance else None
        enriquecidos.append(item)
    return enriquecidos, base_alcance


def _agrupar(posts, chave):
    """Desempenho medio por grupo (formato, pilar, dia...)."""
    grupos = {}
    for post in posts:
        nome = post.get(chave) or "indefinido"
        grupos.setdefault(nome, []).append(post)

    saida = []
    for nome, itens in grupos.items():
        saida.append({
            "grupo": nome,
            "posts": len(itens),
            "alcance_mediano": int(_mediana([_num(p.get("alcance")) for p in itens])),
            "indice_mediano": round(_mediana([p["indice_alcance"] for p in itens
                                              if p["indice_alcance"] is not None]), 2),
            "taxa_engajamento": round(_mediana([p["taxa_engajamento"] for p in itens
                                                if p["taxa_engajamento"]]), 4),
            "taxa_salvamento": round(_mediana([p["taxa_salvamento"] for p in itens
                                               if p["taxa_salvamento"]]), 4),
            "taxa_compartilhamento": round(_mediana([p["taxa_compartilhamento"]
                                                     for p in itens
                                                     if p["taxa_compartilhamento"]]), 4),
        })
    return sorted(saida, key=lambda g: g["indice_mediano"], reverse=True)


def _heatmap(posts, minimo):
    """Mapa dia x faixa de horario ponderado pelo desempenho relativo.

    So devolve resultado com amostra suficiente: recomendar horario com 4
    posts e chute com cara de dado.
    """
    validos = [p for p in posts if p["dia_semana"] and p["indice_alcance"]]
    if len(validos) < minimo:
        return {"confiavel": False, "amostra": len(validos), "minimo": minimo,
                "celulas": [], "melhores": []}

    celulas = {}
    for post in validos:
        chave = (post["dia_semana"], post["faixa"])
        celulas.setdefault(chave, []).append(post["indice_alcance"])

    lista = [{"dia": dia, "faixa": faixa, "posts": len(v),
              "indice": round(_mediana(v), 2)}
             for (dia, faixa), v in celulas.items()]
    lista.sort(key=lambda c: c["indice"], reverse=True)
    melhores = [c for c in lista if c["posts"] >= 2][:5] or lista[:3]
    return {"confiavel": True, "amostra": len(validos), "minimo": minimo,
            "celulas": lista, "melhores": melhores}


def _serie_seguidores(snaps):
    pontos = [(s["data"], s["seguidores"]) for s in snaps if s.get("seguidores")]
    if len(pontos) < 2:
        return {"serie": pontos, "ganho_7d": None, "ganho_30d": None,
                "ritmo_semanal": None}

    def ganho(dias):
        alvo = (datetime.now(FUSO).date() - timedelta(days=dias)).isoformat()
        anteriores = [v for d, v in pontos if d <= alvo]
        if not anteriores:
            return None
        return pontos[-1][1] - anteriores[-1]

    g7 = ganho(7)
    return {"serie": pontos, "ganho_7d": g7, "ganho_30d": ganho(30),
            "ritmo_semanal": g7}


def _diagnosticos(perfil, resumo, por_pilar, por_formato, parametros):
    """Regras determinísticas. O que e fato vem daqui, nao de palpite."""
    achados = []

    def add(nivel, titulo, detalhe):
        achados.append({"nivel": nivel, "titulo": titulo, "detalhe": detalhe})

    eng = resumo.get("taxa_engajamento_mediana") or 0
    alvo_eng = parametros["benchmark_taxa_engajamento"]
    if eng and eng < alvo_eng * 0.6:
        add("alerta", "Engajamento abaixo do piso",
            "Mediana de {0:.1%} contra {1:.1%} de referencia. O conteudo esta "
            "alcancando gente que nao reage: o problema costuma ser gancho "
            "fraco nos 3 primeiros segundos.".format(eng, alvo_eng))
    elif eng > alvo_eng * 1.3:
        add("bom", "Engajamento acima da referencia",
            "Mediana de {0:.1%}. Quem ve, reage. Vale aumentar frequencia: "
            "o teto aqui e distribuicao, nao qualidade.".format(eng))

    salv = resumo.get("taxa_salvamento_mediana") or 0
    if salv and salv < parametros["benchmark_taxa_salvamento"] * 0.5:
        add("alerta", "Pouco salvamento",
            "Apenas {0:.2%} salvam. Salvamento e o sinal que mais expande "
            "alcance no Instagram hoje. Conteudo de referencia (checklist, "
            "passo a passo, tabela) corrige isso rapido.".format(salv))

    comp = resumo.get("taxa_compartilhamento_mediana") or 0
    if comp and comp > parametros["benchmark_taxa_compartilhamento"] * 1.5:
        add("bom", "Alto compartilhamento",
            "{0:.2%} compartilham. Esse e o vetor de crescimento organico "
            "mais barato que existe. Dobre o formato que gera isso.".format(comp))

    if resumo["posts_semana"] == 0:
        add("alerta", "Nenhum post na ultima semana",
            "Sem publicacao, o alcance cai e demora a voltar. Prioridade da semana.")
    elif resumo["posts_semana"] < 3:
        add("atencao", "Frequencia baixa",
            "{0} post(s) na semana. Abaixo de 3 o algoritmo tem pouca amostra "
            "para testar seu conteudo.".format(resumo["posts_semana"]))

    if len(por_pilar) >= 2:
        melhor, pior = por_pilar[0], por_pilar[-1]
        if melhor["grupo"] != "indefinido" and melhor["indice_mediano"] >= 1.3:
            add("acao", "Pilar campeao: {0}".format(melhor["grupo"]),
                "Alcance mediano {0}x o do perfil em {1} post(s). E a aposta "
                "obvia da proxima semana.".format(melhor["indice_mediano"],
                                                  melhor["posts"]))
        if pior["indice_mediano"] <= 0.7 and pior["posts"] >= 3:
            add("acao", "Pilar fraco: {0}".format(pior["grupo"]),
                "Rende {0}x a mediana em {1} post(s). Reduza ou mude o "
                "formato antes de abandonar.".format(pior["indice_mediano"],
                                                     pior["posts"]))

    indefinidos = next((g for g in por_pilar if g["grupo"] == "indefinido"), None)
    if indefinidos and indefinidos["posts"] >= max(3, len(por_pilar)):
        add("atencao", "Muitos posts sem pilar",
            "{0} posts nao casaram com nenhuma palavra-chave. Ajuste os "
            "pilares em config/perfis.json para a analise ficar util.".format(
                indefinidos["posts"]))

    if len(por_formato) >= 2:
        melhor = por_formato[0]
        add("acao", "Formato que mais rende: {0}".format(melhor["grupo"]),
            "Indice {0}x com {1} post(s) e engajamento de {2:.1%}.".format(
                melhor["indice_mediano"], melhor["posts"],
                melhor["taxa_engajamento"] or 0))

    return achados


def analisar_perfil(perfil, posts, snaps, parametros):
    janela = parametros["janela_semana_dias"]
    corte = datetime.now(FUSO) - timedelta(days=janela)

    enriquecidos, base_alcance = enriquecer(posts)
    da_semana = [p for p in enriquecidos if p["quando"] and p["quando"] >= corte]

    seguidores = _serie_seguidores(snaps)
    ultimo = snaps[-1] if snaps else {}

    # O numero que manda em tudo: conta parada nao tem desempenho, tem silencio.
    datas = [p["quando"] for p in enriquecidos if p["quando"]]
    ultimo_post = max(datas) if datas else None
    dias_parado = (datetime.now(FUSO) - ultimo_post).days if ultimo_post else None

    resumo = {
        "ultimo_post": ultimo_post.strftime("%d/%m/%Y") if ultimo_post else None,
        "dias_parado": dias_parado,
        "seguidores": ultimo.get("seguidores"),
        "ganho_7d": seguidores["ganho_7d"],
        "ganho_30d": seguidores["ganho_30d"],
        "alcance_conta": ultimo.get("alcance"),
        "visitas_perfil": ultimo.get("visitas_perfil"),
        "posts_total": len(enriquecidos),
        "posts_semana": len(da_semana),
        "alcance_mediano": int(base_alcance),
        "alcance_mediano_semana": int(_mediana([_num(p.get("alcance"))
                                                for p in da_semana])),
        "taxa_engajamento_mediana": round(
            _mediana([p["taxa_engajamento"] for p in enriquecidos
                      if p["taxa_engajamento"]]), 4),
        "taxa_salvamento_mediana": round(
            _mediana([p["taxa_salvamento"] for p in enriquecidos
                      if p["taxa_salvamento"]]), 4),
        "taxa_compartilhamento_mediana": round(
            _mediana([p["taxa_compartilhamento"] for p in enriquecidos
                      if p["taxa_compartilhamento"]]), 4),
    }

    por_pilar = _agrupar(enriquecidos, "pilar")
    por_formato = _agrupar(enriquecidos, "produto")
    por_dia = _agrupar([p for p in enriquecidos if p["dia_semana"]], "dia_semana")

    ordenados = sorted([p for p in enriquecidos if p["indice_alcance"] is not None],
                       key=lambda p: p["indice_alcance"], reverse=True)

    def resumir(post):
        return {
            "quando": post["quando"].strftime("%d/%m %H:%M") if post["quando"] else "",
            "dia_semana": post["dia_semana"],
            "pilar": post.get("pilar"),
            "formato": post.get("produto"),
            "gancho": (post.get("legenda") or "").strip().splitlines()[0][:110]
                      if post.get("legenda") else "(sem legenda)",
            "alcance": _num(post.get("alcance")),
            "indice": post["indice_alcance"],
            "taxa_engajamento": post["taxa_engajamento"],
            "taxa_salvamento": post["taxa_salvamento"],
            "permalink": post.get("permalink"),
        }

    return {
        "username": perfil["username"],
        "nome": perfil["nome"],
        "papel": perfil["papel"],
        "objetivo": perfil["objetivo"],
        "url": perfil["url"],
        "descricao": perfil.get("descricao", ""),
        "resumo": resumo,
        "seguidores": seguidores,
        "por_pilar": por_pilar,
        "por_formato": por_formato,
        "por_dia": por_dia,
        "horarios": _heatmap(enriquecidos, parametros["min_posts_para_heatmap"]),
        "melhores": [resumir(p) for p in ordenados[:5]],
        "piores": [resumir(p) for p in ordenados[-5:]][::-1],
        "posts_semana": [resumir(p) for p in da_semana],
        "diagnosticos": _diagnosticos(perfil, resumo, por_pilar, por_formato,
                                      parametros),
    }


def comparar(analises):
    """Leitura cruzada dos dois perfis - qual esta puxando o outro."""
    if len(analises) < 2:
        return {}
    ordenado = sorted(analises,
                      key=lambda a: a["resumo"]["alcance_mediano"], reverse=True)
    forte, fraco = ordenado[0], ordenado[-1]
    linhas = []
    if forte["resumo"]["alcance_mediano"] and fraco["resumo"]["alcance_mediano"]:
        razao = forte["resumo"]["alcance_mediano"] / fraco["resumo"]["alcance_mediano"]
        linhas.append(
            "@{0} alcanca {1:.1f}x mais que @{2} por post. Conteudo que funciona "
            "no forte deve ser adaptado para o outro, nao criado do zero.".format(
                forte["username"], razao, fraco["username"]))
    for analise in analises:
        eng = analise["resumo"]["taxa_engajamento_mediana"] or 0
        alc = analise["resumo"]["alcance_mediano"]
        if alc and eng:
            linhas.append(
                "@{0}: alcance mediano {1} e engajamento {2:.1%}.".format(
                    analise["username"], alc, eng))
    return {"forte": forte["username"], "fraco": fraco["username"],
            "observacoes": linhas}
