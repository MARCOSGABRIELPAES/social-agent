"""Classifica cada post em um pilar de conteudo a partir da legenda.

Sem isso a analise so consegue dizer "esse post foi bem". Com isso ela diz
"posts do pilar X vao 2x melhor que a media" - que e a informacao que muda
a pauta da semana.
"""

import re
import unicodedata


def normalizar(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def detectar_pilar(legenda, pilares):
    """Pilar com mais palavras-chave batendo. 'indefinido' se nenhuma bater."""
    texto = normalizar(legenda)
    if not texto:
        return "indefinido"
    melhor, melhor_placar = "indefinido", 0
    for pilar in pilares:
        placar = 0
        for chave in pilar.get("palavras_chave", []):
            alvo = normalizar(chave)
            if not alvo:
                continue
            # Palavra inteira quando e um termo curto, substring quando e frase.
            if " " in alvo:
                placar += texto.count(alvo)
            elif re.search(r"\b" + re.escape(alvo) + r"\b", texto):
                placar += 1
        if placar > melhor_placar:
            melhor, melhor_placar = pilar["nome"], placar
    return melhor


def extrair_gancho(legenda, limite=90):
    """Primeira linha da legenda: e o que decide a parada do scroll."""
    if not legenda:
        return ""
    primeira = legenda.strip().splitlines()[0].strip()
    return primeira[:limite]


def contar_hashtags(legenda):
    return len(re.findall(r"#\w+", legenda or ""))
