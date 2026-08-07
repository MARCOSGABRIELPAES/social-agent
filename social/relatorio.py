"""Gera o painel de desempenho.

Duas saidas do mesmo conteudo:
  gerar()      - documento completo, abre offline no navegador
  fragmento()  - so estilo + marcacao, para publicar como pagina hospedada

Direcao visual: painel de instrumento, nao dashboard corporativo. Todo numero
sai em monoespacada tabular - a leitura e de ficha de treino, medida a medida.
Ambar aparece unicamente onde o dado supera a linha de base do proprio perfil;
se ele estiver em tudo, perde a funcao de sinal.
"""

import html
from datetime import datetime, timedelta, timezone

FUSO = timezone(timedelta(hours=-3))

DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
ABREV = {"segunda": "SEG", "terca": "TER", "quarta": "QUA", "quinta": "QUI",
         "sexta": "SEX", "sabado": "SAB", "domingo": "DOM"}
FAIXAS = ["06-09", "09-12", "12-15", "15-18", "18-21", "21-00"]

CSS = """
:root {
  --ground: #ECEEF1;      --surface: #F7F8FA;     --sunken: #E2E6EB;
  --line: #D3D8DF;        --line-forte: #B9C1CB;
  --ink: #171A1F;         --ink-medio: #454E5B;   --ink-suave: #6E7885;
  --ancora: #0B6E7F;      --ancora-fraco: #D7EAED;
  --brasa: #B45309;       --brasa-fraco: #F7E6CE;
  --ok: #157F4C;          --atencao: #B45309;     --critico: #B42318;
  --nivel-0: #E3E7EC; --nivel-1: #C3D8DC; --nivel-2: #8FBFC7;
  --nivel-3: #4E9BA8; --nivel-4: #0B6E7F;
  --sombra: 0 1px 2px rgba(23,26,31,.06), 0 4px 12px rgba(23,26,31,.04);
  --prosa: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  --medida: ui-monospace, "Cascadia Mono", "SF Mono", "Consolas", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --ground: #171A1F;    --surface: #1E232A;     --sunken: #12151A;
    --line: #2C333C;      --line-forte: #3D4651;
    --ink: #E8EBEF;       --ink-medio: #AEB7C2;   --ink-suave: #7C8794;
    --ancora: #4FB3C4;    --ancora-fraco: #14333A;
    --brasa: #E5A24A;     --brasa-fraco: #3A2C16;
    --ok: #4CBE85;          --atencao: #E0913A;     --critico: #F0736A;
    --nivel-0: #232931; --nivel-1: #1E3D45; --nivel-2: #2B5D69;
    --nivel-3: #3C8595; --nivel-4: #4FB3C4;
    --sombra: 0 1px 2px rgba(0,0,0,.4), 0 4px 14px rgba(0,0,0,.25);
  }
}
:root[data-theme="dark"] {
  --ground: #171A1F;      --surface: #1E232A;     --sunken: #12151A;
  --line: #2C333C;        --line-forte: #3D4651;
  --ink: #E8EBEF;         --ink-medio: #AEB7C2;   --ink-suave: #7C8794;
  --ancora: #4FB3C4;      --ancora-fraco: #14333A;
  --brasa: #E5A24A;       --brasa-fraco: #3A2C16;
  --ok: #4CBE85;          --atencao: #E0913A;     --critico: #F0736A;
  --nivel-0: #232931; --nivel-1: #1E3D45; --nivel-2: #2B5D69;
  --nivel-3: #3C8595; --nivel-4: #4FB3C4;
  --sombra: 0 1px 2px rgba(0,0,0,.4), 0 4px 14px rgba(0,0,0,.25);
}
:root[data-theme="light"] {
  --ground: #ECEEF1;      --surface: #F7F8FA;     --sunken: #E2E6EB;
  --line: #D3D8DF;        --line-forte: #B9C1CB;
  --ink: #171A1F;         --ink-medio: #454E5B;   --ink-suave: #6E7885;
  --ancora: #0B6E7F;      --ancora-fraco: #D7EAED;
  --brasa: #B45309;       --brasa-fraco: #F7E6CE;
  --ok: #157F4C;          --atencao: #B45309;     --critico: #B42318;
  --nivel-0: #E3E7EC; --nivel-1: #C3D8DC; --nivel-2: #8FBFC7;
  --nivel-3: #4E9BA8; --nivel-4: #0B6E7F;
  --sombra: 0 1px 2px rgba(23,26,31,.06), 0 4px 12px rgba(23,26,31,.04);
}

* { box-sizing: border-box; }
body {
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: var(--prosa); font-size: 16px; line-height: 1.5;
  -webkit-text-size-adjust: 100%;
}
.folha { max-width: 720px; margin: 0 auto; padding: 20px 16px 72px; }

/* --- cabecalho ---------------------------------------------------------- */
.topo { display: flex; flex-direction: column; gap: 4px; margin-bottom: 20px; }
.topo h1 {
  margin: 0; font-size: 1.5rem; font-weight: 700; letter-spacing: -.02em;
  text-wrap: balance;
}
.carimbo {
  font-family: var(--medida); font-size: .7rem; color: var(--ink-suave);
  text-transform: uppercase; letter-spacing: .09em;
}

/* --- abas de perfil ------------------------------------------------------ */
.radio { position: absolute; opacity: 0; width: 1px; height: 1px; }
.abas {
  display: flex; gap: 4px; padding: 4px; margin-bottom: 20px;
  background: var(--sunken); border: 1px solid var(--line); border-radius: 10px;
  position: sticky; top: 8px; z-index: 5;
  backdrop-filter: blur(8px);
}
.abas label {
  flex: 1; text-align: center; padding: 9px 8px; border-radius: 7px;
  font-family: var(--medida); font-size: .76rem; letter-spacing: .01em;
  color: var(--ink-suave); cursor: pointer; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
  transition: background .15s ease, color .15s ease;
}
.abas label:hover { color: var(--ink-medio); }
.paineis > section { display: none; }
.radio:focus-visible + .abas label { outline: 2px solid var(--ancora); outline-offset: 2px; }

/* --- veredito ------------------------------------------------------------ */
.veredito {
  display: grid; gap: 10px; padding: 18px;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: 12px; box-shadow: var(--sombra); margin-bottom: 16px;
}
.veredito .marca {
  font-family: var(--medida); font-size: .68rem; letter-spacing: .12em;
  text-transform: uppercase; color: var(--ink-suave);
}
.veredito .numero {
  font-family: var(--medida); font-size: 2.6rem; line-height: 1;
  font-weight: 600; letter-spacing: -.03em; font-variant-numeric: tabular-nums;
}
.veredito .numero.alerta { color: var(--critico); }
.veredito .numero.bom { color: var(--ok); }
.veredito p { margin: 0; color: var(--ink-medio); font-size: .93rem; text-wrap: pretty; }

/* --- kpis ---------------------------------------------------------------- */
.kpis {
  display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px;
  margin-bottom: 22px;
}
@media (min-width: 560px) { .kpis { grid-template-columns: repeat(3, 1fr); } }
.kpi {
  padding: 13px 14px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 10px;
  display: flex; flex-direction: column; gap: 3px;
}
.kpi .rotulo {
  font-family: var(--medida); font-size: .64rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--ink-suave);
}
.kpi .valor {
  font-family: var(--medida); font-size: 1.5rem; font-weight: 600;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.kpi .nota { font-size: .72rem; color: var(--ink-suave); line-height: 1.35; }
.kpi.destaque { border-color: var(--brasa); background: var(--brasa-fraco); }
.kpi.destaque .valor { color: var(--brasa); }
.kpi.abaixo .valor { color: var(--critico); }

/* --- secoes -------------------------------------------------------------- */
h2 {
  font-family: var(--medida); font-size: .7rem; font-weight: 600;
  letter-spacing: .12em; text-transform: uppercase; color: var(--ink-suave);
  margin: 26px 0 10px; padding-bottom: 7px; border-bottom: 1px solid var(--line);
}

/* --- diagnosticos -------------------------------------------------------- */
.achado {
  display: grid; grid-template-columns: 3px 1fr; gap: 12px;
  padding: 12px 0; border-bottom: 1px solid var(--line);
}
.achado:last-child { border-bottom: 0; }
.achado .risco { border-radius: 2px; background: var(--line-forte); }
.achado.bom .risco { background: var(--ok); }
.achado.acao .risco { background: var(--ancora); }
.achado.atencao .risco { background: var(--atencao); }
.achado.alerta .risco { background: var(--critico); }
.achado .titulo { font-weight: 600; font-size: .93rem; margin-bottom: 2px; }
.achado .detalhe { color: var(--ink-medio); font-size: .86rem; text-wrap: pretty; }

/* --- barras de grupo ----------------------------------------------------- */
.grupo { display: grid; gap: 3px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.grupo:last-child { border-bottom: 0; }
.grupo .linha { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.grupo .nome { font-size: .9rem; font-weight: 550; }
.grupo .indice {
  font-family: var(--medida); font-size: .95rem; font-weight: 600;
  font-variant-numeric: tabular-nums; color: var(--ink-medio);
}
.grupo.acima .indice { color: var(--brasa); }
.trilho { height: 6px; background: var(--sunken); border-radius: 3px; overflow: hidden; }
.trilho span { display: block; height: 100%; background: var(--ancora); border-radius: 3px; }
.grupo.acima .trilho span { background: var(--brasa); }
.grupo .meta {
  font-family: var(--medida); font-size: .68rem; color: var(--ink-suave);
  letter-spacing: .04em;
}

/* --- mapa de horarios ---------------------------------------------------- */
.rolagem { overflow-x: auto; -webkit-overflow-scrolling: touch; padding-bottom: 4px; }
.mapa {
  display: grid; grid-template-columns: 40px repeat(6, minmax(46px, 1fr));
  gap: 3px; min-width: 340px;
}
.mapa .cab, .mapa .lin {
  font-family: var(--medida); font-size: .6rem; letter-spacing: .06em;
  color: var(--ink-suave); display: flex; align-items: center;
}
.mapa .cab { justify-content: center; padding-bottom: 3px; }
.mapa .lin { justify-content: flex-end; padding-right: 6px; }
.cel {
  aspect-ratio: 1.5; border-radius: 5px; display: flex;
  align-items: center; justify-content: center;
  font-family: var(--medida); font-size: .66rem; font-variant-numeric: tabular-nums;
  background: var(--nivel-0); color: var(--ink-suave);
}
.cel.n1 { background: var(--nivel-1); color: var(--ink); }
.cel.n2 { background: var(--nivel-2); color: #0C2126; }
.cel.n3 { background: var(--nivel-3); color: #fff; }
.cel.n4 { background: var(--nivel-4); color: #fff; font-weight: 600; }

/* --- posts --------------------------------------------------------------- */
.post {
  display: grid; gap: 7px; padding: 13px 0; border-bottom: 1px solid var(--line);
}
.post:last-child { border-bottom: 0; }
.post .cabeca { display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
.selo {
  font-family: var(--medida); font-size: .62rem; letter-spacing: .07em;
  text-transform: uppercase; padding: 2px 7px; border-radius: 4px;
  background: var(--sunken); color: var(--ink-suave); border: 1px solid var(--line);
}
.selo.pilar { background: var(--ancora-fraco); color: var(--ancora); border-color: transparent; }
.post .gancho { font-size: .92rem; line-height: 1.4; text-wrap: pretty; }
.post .gancho a { color: inherit; text-decoration-color: var(--line-forte); text-underline-offset: 3px; }
.post .gancho a:hover { text-decoration-color: var(--ancora); }
.post .numeros {
  display: flex; gap: 14px; flex-wrap: wrap;
  font-family: var(--medida); font-size: .7rem; color: var(--ink-suave);
  font-variant-numeric: tabular-nums;
}
.post .numeros b { color: var(--ink-medio); font-weight: 600; }
.post.campeao .numeros b.ind { color: var(--brasa); }

/* --- exportar ------------------------------------------------------------ */
.exportar {
  margin-top: 34px; padding: 18px; border-radius: 12px;
  background: var(--surface); border: 1px solid var(--line); box-shadow: var(--sombra);
  display: grid; gap: 12px;
}
.exportar h3 {
  margin: 0; font-family: var(--medida); font-size: .7rem; font-weight: 600;
  letter-spacing: .12em; text-transform: uppercase; color: var(--ink-suave);
}
.exportar p { margin: 0; font-size: .87rem; color: var(--ink-medio); text-wrap: pretty; }
.botoes { display: flex; gap: 8px; flex-wrap: wrap; }
.botoes button, .botoes a {
  flex: 1 1 auto; min-height: 44px; padding: 11px 16px; border-radius: 9px;
  font-family: var(--medida); font-size: .78rem; letter-spacing: .04em;
  cursor: pointer; border: 1px solid var(--line-forte); background: var(--ground);
  color: var(--ink); text-align: center; text-decoration: none;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background .15s ease, border-color .15s ease;
}
.botoes button.principal { background: var(--ancora); border-color: var(--ancora); color: #fff; }
.botoes button.principal.feito { background: var(--ok); border-color: var(--ok); }
.botoes button:hover, .botoes a:hover { border-color: var(--ancora); }
.botoes button:focus-visible, .botoes a:focus-visible {
  outline: 2px solid var(--ancora); outline-offset: 2px;
}

/* --- vazio / rodape ------------------------------------------------------ */
.vazio {
  padding: 22px 18px; border: 1px dashed var(--line-forte); border-radius: 10px;
  color: var(--ink-medio); font-size: .9rem; text-wrap: pretty;
}
.cruzado { display: grid; gap: 7px; margin-bottom: 20px; padding: 16px 18px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 12px; }
.cruzado p { margin: 0; font-size: .88rem; color: var(--ink-medio); text-wrap: pretty; }
footer {
  margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--line);
  font-size: .76rem; color: var(--ink-suave); line-height: 1.55;
}
footer b { color: var(--ink-medio); font-weight: 600; }
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

# As abas sao geradas por perfil, entao a regra de :checked tambem.
def _css_abas(quantidade):
    regras = []
    for i in range(quantidade):
        regras.append(
            "#perfil{0}:checked ~ .paineis > #painel{0} {{ display: block; }}\n"
            "#perfil{0}:checked ~ .abas label[for=\"perfil{0}\"] {{"
            " background: var(--surface); color: var(--ink);"
            " box-shadow: var(--sombra); }}".format(i))
    return "\n".join(regras)


# --- formatadores ---------------------------------------------------------

def e(valor):
    return html.escape(str(valor if valor is not None else ""))


def n(valor):
    if valor is None:
        return "—"
    return "{:,}".format(int(valor)).replace(",", ".")


def pct(valor, casas=1):
    if not valor:
        return "—"
    return ("{:." + str(casas) + "%}").format(valor)


def _plural(quantidade, singular, plural):
    return singular if quantidade == 1 else plural


# --- blocos ---------------------------------------------------------------

def _veredito(a):
    """A leitura honesta do estado da conta, antes de qualquer metrica."""
    r = a["resumo"]
    parado = r.get("dias_parado")

    if r["posts_total"] == 0:
        return ('<div class="veredito"><div class="marca">Estado da conta</div>'
                '<div class="numero alerta">0</div>'
                '<p>Nenhum post publicado. Nao ha desempenho a medir aqui &mdash; '
                'o que falta neste perfil e conteudo, nao analise.</p></div>')

    if parado is None:
        corpo = "Sem data de publicacao nos dados coletados."
        classe, numero, marca = "", "—", "Estado da conta"
    elif parado >= 60:
        meses = parado // 30
        corpo = ("Ultimo post em {0}. Alcance organico decai com a inatividade e "
                 "leva semanas de publicacao constante para voltar ao patamar "
                 "anterior.".format(r.get("ultimo_post") or "data desconhecida"))
        classe, numero = "alerta", str(meses)
        marca = "Meses sem publicar"
    elif parado >= 8:
        corpo = ("Ultimo post em {0}. Acima de uma semana sem publicar, o "
                 "algoritmo perde amostra para testar seu conteudo.".format(
                     r.get("ultimo_post")))
        classe, numero, marca = "alerta", str(parado), "Dias sem publicar"
    else:
        corpo = ("Ultimo post em {0}. Cadencia dentro da janela em que o alcance "
                 "se sustenta.".format(r.get("ultimo_post")))
        classe, numero, marca = "bom", str(parado), "Dias sem publicar"

    return ('<div class="veredito"><div class="marca">{0}</div>'
            '<div class="numero {1}">{2}</div><p>{3}</p></div>').format(
        e(marca), classe, e(numero), e(corpo))


def _kpis(a, parametros):
    r = a["resumo"]
    eng = r["taxa_engajamento_mediana"] or 0
    salv = r["taxa_salvamento_mediana"] or 0
    comp = r["taxa_compartilhamento_mediana"] or 0
    alvo_eng = parametros["benchmark_taxa_engajamento"]
    alvo_salv = parametros["benchmark_taxa_salvamento"]
    alvo_comp = parametros["benchmark_taxa_compartilhamento"]

    ganho = r.get("ganho_7d")
    if ganho is None:
        nota_seg = "primeira medicao"
    else:
        nota_seg = "{0}{1} em 7 dias".format("+" if ganho > 0 else "", ganho)

    cartoes = [
        ("", "Seguidores", n(r["seguidores"]), nota_seg),
        ("", "Alcance tipico", n(r["alcance_mediano"]), "mediana por post"),
        ("", "Posts medidos", str(r["posts_total"]), "na janela analisada"),
        ("destaque" if eng > alvo_eng else ("abaixo" if eng and eng < alvo_eng * .6 else ""),
         "Engajamento", pct(eng), "ref. {0}".format(pct(alvo_eng))),
        ("destaque" if salv > alvo_salv else ("abaixo" if salv and salv < alvo_salv * .5 else ""),
         "Salvamento", pct(salv, 2), "ref. {0}".format(pct(alvo_salv, 2))),
        ("destaque" if comp > alvo_comp else ("abaixo" if comp and comp < alvo_comp * .5 else ""),
         "Compartilham.", pct(comp, 2), "ref. {0}".format(pct(alvo_comp, 2))),
    ]
    itens = "".join(
        '<div class="kpi {0}"><div class="rotulo">{1}</div>'
        '<div class="valor">{2}</div><div class="nota">{3}</div></div>'.format(
            classe, e(rot), val, e(nota))
        for classe, rot, val, nota in cartoes)
    return '<div class="kpis">{0}</div>'.format(itens)


def _diagnosticos(itens):
    if not itens:
        return ""
    blocos = "".join(
        '<div class="achado {0}"><div class="risco"></div><div>'
        '<div class="titulo">{1}</div><div class="detalhe">{2}</div>'
        '</div></div>'.format(e(d["nivel"]), e(d["titulo"]), e(d["detalhe"]))
        for d in itens)
    return "<h2>Leitura de desempenho</h2>{0}".format(blocos)


def _grupos(grupos, titulo, rotulo_vazio):
    if not grupos:
        return '<h2>{0}</h2><div class="vazio">{1}</div>'.format(
            e(titulo), e(rotulo_vazio))
    maximo = max(g["indice_mediano"] for g in grupos) or 1
    linhas = []
    for g in grupos:
        acima = "acima" if g["indice_mediano"] >= 1.15 else ""
        largura = max(2, int((g["indice_mediano"] / maximo) * 100))
        linhas.append(
            '<div class="grupo {0}">'
            '<div class="linha"><span class="nome">{1}</span>'
            '<span class="indice">{2}x</span></div>'
            '<div class="trilho"><span style="width:{3}%"></span></div>'
            '<div class="meta">{4} {5} &middot; alcance {6} &middot; eng {7}</div>'
            '</div>'.format(
                acima, e(g["grupo"]), g["indice_mediano"], largura,
                g["posts"], _plural(g["posts"], "post", "posts"),
                n(g["alcance_mediano"]), pct(g["taxa_engajamento"])))
    return "<h2>{0}</h2>{1}".format(e(titulo), "".join(linhas))


def _mapa(horarios):
    if not horarios.get("confiavel"):
        return ('<h2>Melhores horarios</h2><div class="vazio">'
                'Amostra insuficiente: {0} de {1} posts necessarios. Recomendar '
                'horario com poucos dados e chute com cara de dado. Ate la vale a '
                'referencia geral do Instagram &mdash; terca e quarta, entre 18h e 21h '
                '&mdash; e o mapa assume assim que houver historico proprio.'
                '</div>').format(horarios.get("amostra", 0), horarios.get("minimo", 15))

    indice = {(c["dia"], c["faixa"]): c for c in horarios["celulas"]}
    partes = ['<div class="mapa"><div></div>']
    partes += ['<div class="cab">{0}</div>'.format(f) for f in FAIXAS]
    for dia in DIAS:
        partes.append('<div class="lin">{0}</div>'.format(ABREV[dia]))
        for faixa in FAIXAS:
            cel = indice.get((dia, faixa))
            if not cel:
                partes.append('<div class="cel">&middot;</div>')
                continue
            v = cel["indice"]
            nivel = "n4" if v >= 1.6 else "n3" if v >= 1.2 else "n2" if v >= .9 \
                else "n1" if v >= .6 else ""
            partes.append('<div class="cel {0}" title="{1} post(s)">{2}</div>'.format(
                nivel, cel["posts"], v))
    partes.append("</div>")

    melhores = " &middot; ".join(
        "{0} {1} <b>{2}x</b>".format(ABREV[c["dia"]], c["faixa"], c["indice"])
        for c in horarios["melhores"])
    return ('<h2>Melhores horarios</h2><div class="rolagem">{0}</div>'
            '<div class="post"><div class="numeros">{1}</div></div>'
            '<div class="achado"><div class="risco"></div><div class="detalhe">'
            'Janelas com um unico post ficam fora da recomendacao: com amostra de '
            'um, o numero e sorte e nao padrao.</div></div>').format(
        "".join(partes), melhores)


def _posts(posts, titulo, vazio):
    if not posts:
        return '<h2>{0}</h2><div class="vazio">{1}</div>'.format(e(titulo), e(vazio))
    blocos = []
    for p in posts:
        gancho = e(p["gancho"])
        if p.get("permalink"):
            gancho = '<a href="{0}" rel="noreferrer">{1}</a>'.format(
                e(p["permalink"]), gancho)
        campeao = "campeao" if (p["indice"] or 0) >= 1.5 else ""
        selos = '<span class="selo">{0}</span>'.format(e(p["quando"]))
        if p.get("pilar") and p["pilar"] != "indefinido":
            selos += '<span class="selo pilar">{0}</span>'.format(e(p["pilar"]))
        if p.get("formato"):
            selos += '<span class="selo">{0}</span>'.format(e(p["formato"]))
        blocos.append(
            '<div class="post {0}"><div class="cabeca">{1}</div>'
            '<div class="gancho">{2}</div>'
            '<div class="numeros">'
            '<span>alcance <b>{3}</b></span>'
            '<span>indice <b class="ind">{4}x</b></span>'
            '<span>eng <b>{5}</b></span>'
            '<span>salv <b>{6}</b></span>'
            '</div></div>'.format(
                campeao, selos, gancho, n(p["alcance"]),
                p["indice"] if p["indice"] is not None else "—",
                pct(p["taxa_engajamento"]), pct(p["taxa_salvamento"], 2)))
    return "<h2>{0}</h2>{1}".format(e(titulo), "".join(blocos))


def _painel(a, indice, parametros):
    if a["resumo"]["posts_total"] == 0:
        miolo = _veredito(a) + _kpis(a, parametros)
    else:
        miolo = (
            _veredito(a)
            + _kpis(a, parametros)
            + _diagnosticos(a["diagnosticos"])
            + _grupos(a["por_pilar"], "Por pilar de conteudo",
                      "Nenhum post classificado ainda.")
            + _grupos(a["por_formato"], "Por formato", "Sem formatos medidos.")
            + _mapa(a["horarios"])
            + _posts(a["melhores"], "Os que mais renderam",
                     "Nenhum post na janela.")
            + _posts(a["piores"], "Os que menos renderam",
                     "Nenhum post na janela."))
    return '<section id="painel{0}">{1}</section>'.format(indice, miolo)


def _exportar(texto):
    """Bloco de exportacao: leva o dado para fora, pronto para uma IA.

    O texto vai embutido num elemento escondido em vez de arquivo separado,
    para o botao continuar funcionando com o app aberto sem rede.
    """
    if not texto:
        return ""
    return (
        '<div class="exportar">'
        "<h3>Levar para uma IA</h3>"
        "<p>Copia um briefing completo &mdash; numeros, definicao de cada metrica, "
        "o que ja performou bem e mal, e o pedido de estrategia ja escrito. "
        "Cole no ChatGPT, no Claude ou em qualquer assistente e peca o plano.</p>"
        '<div class="botoes">'
        '<button type="button" id="copiar" class="principal">Copiar briefing</button>'
        '<button type="button" id="baixar">Baixar .md</button>'
        "</div>"
        '<div id="briefing" hidden>{0}</div>'
        "</div>"
        "<script>(function () {{\n"
        "  var fonte = document.getElementById('briefing');\n"
        "  var copiar = document.getElementById('copiar');\n"
        "  var baixar = document.getElementById('baixar');\n"
        "  function texto() {{ return fonte.textContent; }}\n"
        "  copiar.addEventListener('click', function () {{\n"
        "    var alvo = texto();\n"
        "    var fim = function (ok) {{\n"
        "      copiar.textContent = ok ? 'Copiado' : 'Selecione e copie';\n"
        "      copiar.classList.toggle('feito', ok);\n"
        "      setTimeout(function () {{\n"
        "        copiar.textContent = 'Copiar briefing';\n"
        "        copiar.classList.remove('feito');\n"
        "      }}, 2200);\n"
        "    }};\n"
        "    if (navigator.clipboard && window.isSecureContext) {{\n"
        "      navigator.clipboard.writeText(alvo).then(function () {{ fim(true); }},\n"
        "        function () {{ fim(false); }});\n"
        "    }} else {{\n"
        "      var caixa = document.createElement('textarea');\n"
        "      caixa.value = alvo; caixa.style.position = 'fixed';\n"
        "      caixa.style.opacity = '0'; document.body.appendChild(caixa);\n"
        "      caixa.select();\n"
        "      var ok = false;\n"
        "      try {{ ok = document.execCommand('copy'); }} catch (erro) {{ ok = false; }}\n"
        "      document.body.removeChild(caixa); fim(ok);\n"
        "    }}\n"
        "  }});\n"
        "  baixar.addEventListener('click', function () {{\n"
        "    var blob = new Blob([texto()], {{ type: 'text/markdown;charset=utf-8' }});\n"
        "    var url = URL.createObjectURL(blob);\n"
        "    var a = document.createElement('a');\n"
        "    a.href = url; a.download = 'briefing-instagram.md';\n"
        "    document.body.appendChild(a); a.click();\n"
        "    document.body.removeChild(a);\n"
        "    setTimeout(function () {{ URL.revokeObjectURL(url); }}, 1000);\n"
        "  }});\n"
        "}})();</script>"
    ).format(e(texto))


def corpo(analises, comparacao, janela_dias, briefing_texto=None):
    agora = datetime.now(FUSO)

    radios = "".join(
        '<input class="radio" type="radio" name="perfil" id="perfil{0}"{1}>'.format(
            i, " checked" if i == 0 else "")
        for i in range(len(analises)))

    abas = '<div class="abas">{0}</div>'.format("".join(
        '<label for="perfil{0}">@{1}</label>'.format(i, e(a["username"]))
        for i, a in enumerate(analises)))

    paineis = '<div class="paineis">{0}</div>'.format("".join(
        _painel(a, i, {"benchmark_taxa_engajamento": 0.045,
                       "benchmark_taxa_salvamento": 0.012,
                       "benchmark_taxa_compartilhamento": 0.008})
        for i, a in enumerate(analises)))

    if comparacao.get("observacoes"):
        cruzado = '<div class="cruzado">{0}</div>'.format("".join(
            "<p>{0}</p>".format(e(o)) for o in comparacao["observacoes"]))
    else:
        cruzado = ""

    return (
        "<style>{css}\n{abas_css}</style>"
        '<div class="folha">'
        '<div class="topo"><h1>Painel de desempenho</h1>'
        '<div class="carimbo">{data} &middot; janela {janela} dias &middot; medianas</div>'
        "</div>"
        "{cruzado}{radios}{abas}{paineis}{exportar}"
        "<footer>"
        "<b>Indice de alcance</b> compara voce com voce: 1.0x e o alcance tipico "
        "do proprio perfil, 2.0x e o dobro dele. "
        "<b>Engajamento</b> divide interacoes por alcance, nao por seguidores &mdash; "
        "e o que mede a qualidade do post em vez do tamanho da conta. "
        "Tudo usa <b>mediana</b>: um unico viral distorce a media e faz o perfil "
        "parecer melhor do que entrega toda semana. "
        "Ambar marca o que supera a linha de base."
        "<br><br>Dados da API oficial da Meta. Gerado por social-agent."
        "</footer></div>"
    ).format(css=CSS, abas_css=_css_abas(len(analises)),
             data=agora.strftime("%d/%m/%Y %H:%M"), janela=janela_dias,
             cruzado=cruzado, radios=radios, abas=abas, paineis=paineis,
             exportar=_exportar(briefing_texto))


def fragmento(analises, comparacao, janela_dias, briefing_texto=None):
    """Sem doctype/html/head/body: para publicar como pagina hospedada."""
    return corpo(analises, comparacao, janela_dias, briefing_texto)


def gerar(analises, comparacao, janela_dias, briefing_texto=None):
    """Documento completo, para abrir direto do disco."""
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Painel de desempenho</title></head><body>{0}</body></html>"
    ).format(corpo(analises, comparacao, janela_dias, briefing_texto))
