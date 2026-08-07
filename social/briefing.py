"""Monta um briefing pronto para colar em qualquer IA.

Nao e um dump de numeros. Um LLM recebendo so a tabela responde generico -
ele precisa saber o que cada metrica significa neste contexto, o que ja foi
tentado e onde estao os limites do dado. Por isso o texto carrega definicao,
posicionamento e ressalvas junto com os valores.
"""

from datetime import datetime, timedelta, timezone

FUSO = timezone(timedelta(hours=-3))


def _pct(valor, casas=1):
    if not valor:
        return "sem dado"
    return ("{:." + str(casas) + "%}").format(valor)


def _n(valor):
    return "sem dado" if valor is None else "{:,}".format(int(valor)).replace(",", ".")


def _perfil(a):
    r = a["resumo"]
    linhas = []
    add = linhas.append

    add("## @{0} — {1}".format(a["username"], a["nome"]))
    add("")
    add("- Papel: {0} | Objetivo declarado: {1}".format(a["papel"], a["objetivo"]))
    add("- {0}".format(a.get("descricao") or ""))
    add("")

    if r["posts_total"] == 0:
        add("**Este perfil nao tem nenhum post publicado.** Nao existe metrica "
            "a analisar. O que falta aqui e conteudo, nao diagnostico.")
        add("")
        return "\n".join(linhas)

    add("### Situacao")
    add("")
    add("- Seguidores: {0}".format(_n(r["seguidores"])))
    if r.get("dias_parado") is not None:
        add("- Ultimo post: {0} ({1} dias atras)".format(
            r.get("ultimo_post"), r["dias_parado"]))
    add("- Posts medidos na janela: {0}".format(r["posts_total"]))
    add("- Posts na ultima semana: {0}".format(r["posts_semana"]))
    add("")
    add("### Metricas (medianas, nao medias)")
    add("")
    add("| Metrica | Valor | Referencia de mercado |")
    add("|---|---|---|")
    add("| Alcance por post | {0} | — |".format(_n(r["alcance_mediano"])))
    add("| Engajamento (interacoes/alcance) | {0} | 4,5% |".format(
        _pct(r["taxa_engajamento_mediana"])))
    add("| Salvamento (salvos/alcance) | {0} | 1,2% |".format(
        _pct(r["taxa_salvamento_mediana"], 2)))
    add("| Compartilhamento (compart./alcance) | {0} | 0,8% |".format(
        _pct(r["taxa_compartilhamento_mediana"], 2)))
    add("")

    if a["por_pilar"]:
        add("### Desempenho por pilar de conteudo")
        add("")
        add("Indice 1.0x = o alcance tipico do proprio perfil. 2.0x = o dobro.")
        add("")
        add("| Pilar | Posts | Indice | Engajamento |")
        add("|---|---|---|---|")
        for g in a["por_pilar"]:
            add("| {0} | {1} | {2}x | {3} |".format(
                g["grupo"], g["posts"], g["indice_mediano"],
                _pct(g["taxa_engajamento"])))
        add("")

    if a["por_formato"]:
        add("### Por formato")
        add("")
        add("| Formato | Posts | Indice | Engajamento |")
        add("|---|---|---|---|")
        for g in a["por_formato"]:
            add("| {0} | {1} | {2}x | {3} |".format(
                g["grupo"], g["posts"], g["indice_mediano"],
                _pct(g["taxa_engajamento"])))
        add("")

    h = a["horarios"]
    add("### Horarios")
    add("")
    if h.get("confiavel"):
        add("Janelas com melhor desempenho relativo:")
        add("")
        for c in h["melhores"]:
            add("- {0}, {1}h: {2}x ({3} posts de amostra)".format(
                c["dia"], c["faixa"], c["indice"], c["posts"]))
    else:
        add("Amostra insuficiente ({0} de {1} posts). **Nao invente "
            "recomendacao de horario a partir deste dado.**".format(
                h.get("amostra", 0), h.get("minimo", 15)))
    add("")

    if a["melhores"]:
        add("### Os posts que mais renderam")
        add("")
        for p in a["melhores"]:
            add('- **{0}x** — {1} | {2} | {3} | alcance {4}, eng {5}'.format(
                p["indice"], p["quando"], p["formato"], p["pilar"],
                _n(p["alcance"]), _pct(p["taxa_engajamento"])))
            add('  > "{0}"'.format(p["gancho"]))
        add("")

    if a["piores"]:
        add("### Os que menos renderam")
        add("")
        for p in a["piores"]:
            add('- **{0}x** — {1} | {2} | {3}'.format(
                p["indice"], p["quando"], p["formato"], p["pilar"]))
            add('  > "{0}"'.format(p["gancho"]))
        add("")

    if a["diagnosticos"]:
        add("### Diagnosticos automaticos ja apurados")
        add("")
        for d in a["diagnosticos"]:
            add("- **[{0}] {1}** — {2}".format(
                d["nivel"], d["titulo"], d["detalhe"]))
        add("")

    return "\n".join(linhas)


def gerar(analises, comparacao, janela_dias):
    agora = datetime.now(FUSO)
    partes = []
    add = partes.append

    add("# Briefing de desempenho no Instagram")
    add("")
    add("Gerado em {0}. Janela de analise: {1} dias.".format(
        agora.strftime("%d/%m/%Y"), janela_dias))
    add("")
    add("## Como ler estes numeros")
    add("")
    add("- **Engajamento** e interacoes dividido por **alcance**, nao por "
        "seguidores. Mede a qualidade do post, nao o tamanho da conta.")
    add("- **Indice de alcance** compara o perfil com ele mesmo: 1.0x e o "
        "alcance tipico dele, 2.0x e o dobro. Nao compara com outras contas.")
    add("- Tudo usa **mediana**, nao media: um unico viral distorce a media e "
        "faz o perfil parecer melhor do que entrega toda semana.")
    add("- **Salvamento** e hoje o sinal que mais expande alcance no Instagram; "
        "**compartilhamento** e o que traz publico novo.")
    add("")

    for a in analises:
        add(_perfil(a))

    if comparacao.get("observacoes"):
        add("## Leitura cruzada")
        add("")
        for o in comparacao["observacoes"]:
            add("- {0}".format(o))
        add("")

    add("## O que eu quero de voce")
    add("")
    add("Analise os dados acima e proponha uma estrategia de conteudo para as "
        "proximas 4 semanas. Requisitos:")
    add("")
    add("1. Comece apontando o **gargalo real** — o que trava o crescimento "
        "hoje. Se for falta de publicacao e nao qualidade de conteudo, diga "
        "isso com todas as letras em vez de sugerir otimizacao fina.")
    add("2. Toda recomendacao precisa citar o **numero especifico** que a "
        "sustenta. Recomendacao sem dado por tras e chute.")
    add("3. Proponha uma grade semanal concreta: quantos posts, em que "
        "formato, de que pilar, em que dia e horario.")
    add("4. Para cada post, escreva o **gancho** (primeira linha) e o CTA.")
    add("5. Diga explicitamente o que **nao** fazer, com base no que ja "
        "performou mal.")
    add("6. Se algum dado for insuficiente para uma conclusao, aponte a "
        "lacuna em vez de preencher com suposicao.")
    add("")

    return "\n".join(partes)
