"""Gera os icones do app (PWA). Roda uma vez; o resultado vai versionado.

A marca segue a mesma direcao do painel: fundo ardosia, barras em teal e uma
unica barra em ambar - a que passou da linha de base. Mesma gramatica visual
do relatorio, para o icone na tela inicial nao parecer de outro produto.
"""

from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).parent / "site" / "icones"

CARVAO = (23, 26, 31)
TEAL = (79, 179, 196)
TEAL_FRACO = (43, 93, 105)
BRASA = (229, 162, 74)


def desenhar(lado, margem_segura=False):
    """margem_segura deixa 20% de folga: exigido pelo icone 'maskable',
    que o Android recorta em circulo."""
    escala = 4
    tela = lado * escala
    img = Image.new("RGBA", (tela, tela), CARVAO + (255,))
    d = ImageDraw.Draw(img)

    area = tela * (0.56 if margem_segura else 0.72)
    esq = (tela - area) / 2
    base = (tela + area) / 2

    # Quatro barras: tres em teal (as duas primeiras mais apagadas, sugerindo
    # progressao) e a ultima em ambar, o pico.
    alturas = [0.34, 0.55, 0.78, 1.0]
    cores = [TEAL_FRACO, TEAL_FRACO, TEAL, BRASA]
    larg = area / 6.4
    vao = (area - larg * 4) / 3

    for i, (h, cor) in enumerate(zip(alturas, cores)):
        x0 = esq + i * (larg + vao)
        y0 = base - area * h
        d.rounded_rectangle([x0, y0, x0 + larg, base],
                            radius=larg * 0.28, fill=cor + (255,))

    return img.resize((lado, lado), Image.LANCZOS)


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    saidas = [
        ("icone-192.png", 192, False),
        ("icone-512.png", 512, False),
        ("icone-maskable-512.png", 512, True),
        ("favicon-32.png", 32, False),
    ]
    for nome, lado, seguro in saidas:
        desenhar(lado, seguro).save(DESTINO / nome, "PNG", optimize=True)
        print("  +", DESTINO / nome)

    # Apple nao le manifest: precisa da tag apple-touch-icon apontando para um
    # PNG opaco de 180px.
    apple = desenhar(180).convert("RGB")
    apple.save(DESTINO / "apple-touch-icon.png", "PNG", optimize=True)
    print("  +", DESTINO / "apple-touch-icon.png")


if __name__ == "__main__":
    main()
