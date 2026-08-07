"""Monta a pasta site/ que o GitHub Pages publica.

Transforma o painel num app instalavel: manifest, service worker e icones.
Depois de instalado na tela inicial, abre em tela cheia e continua abrindo
sem rede - o service worker guarda a ultima versao carregada.
"""

import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from social import briefing, config, db, metricas, relatorio

FUSO = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).parent
SITE = RAIZ / "site"

MANIFEST = {
    "name": "Painel de desempenho",
    "short_name": "Painel",
    "description": "Metricas dos perfis @marcosgabriel_ia e @bombeiro_ia",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#171A1F",
    "theme_color": "#171A1F",
    "lang": "pt-BR",
    "icons": [
        {"src": "icones/icone-192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "icones/icone-512.png", "sizes": "512x512", "type": "image/png"},
        {"src": "icones/icone-maskable-512.png", "sizes": "512x512",
         "type": "image/png", "purpose": "maskable"},
    ],
}

# Cache-first com revalidacao: abre instantaneo e offline, e troca pelo novo
# assim que a rede responder. O nome do cache carrega a data da geracao, entao
# cada publicacao invalida a anterior sozinha.
SERVICE_WORKER = """
const CACHE = 'painel-{versao}';
const ESSENCIAIS = ['./', './index.html', './manifest.json'];

self.addEventListener('install', (evento) => {{
  evento.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ESSENCIAIS)).then(() => self.skipWaiting())
  );
}});

self.addEventListener('activate', (evento) => {{
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(
        nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
}});

self.addEventListener('fetch', (evento) => {{
  if (evento.request.method !== 'GET') return;
  evento.respondWith(
    caches.match(evento.request).then((guardado) => {{
      const rede = fetch(evento.request).then((resposta) => {{
        if (resposta && resposta.status === 200) {{
          const copia = resposta.clone();
          caches.open(CACHE).then((c) => c.put(evento.request, copia));
        }}
        return resposta;
      }}).catch(() => guardado);
      return guardado || rede;
    }})
  );
}});
"""

CABECA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Painel de desempenho</title>
<meta name="description" content="Metricas dos perfis @marcosgabriel_ia e @bombeiro_ia">
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#ECEEF1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171A1F" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Painel">
<link rel="apple-touch-icon" href="icones/apple-touch-icon.png">
<link rel="icon" href="icones/favicon-32.png" sizes="32x32">
<style>
  body { padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); }
</style>
</head>
<body>
"""

RODAPE_HTML = """
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('sw.js').catch(function () {});
  });
}
</script>
</body>
</html>
"""


def main():
    dados = config.carregar()
    parametros = dict(dados["parametros"])
    janela = parametros["janela_analise_dias"]
    agora = datetime.now(FUSO)

    desde = (agora - timedelta(days=janela)).isoformat()
    desde_data = (agora - timedelta(days=janela)).date().isoformat()

    con = db.conectar()
    analises = []
    for perfil in dados["perfis"]:
        posts = db.posts_com_metricas(con, perfil["username"], desde)
        snaps = db.snapshots(con, perfil["username"], desde_data)
        analises.append(metricas.analisar_perfil(perfil, posts, snaps, parametros))
    con.close()

    if not analises:
        print("! Nenhum perfil em config/perfis.json")
        return 1

    comparacao = metricas.comparar(analises)
    texto = briefing.gerar(analises, comparacao, janela)

    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(
        CABECA + relatorio.corpo(analises, comparacao, janela, texto) + RODAPE_HTML,
        encoding="utf-8")
    # Tambem como arquivo solto, para quem preferir baixar direto pela URL.
    (SITE / "briefing.md").write_text(texto, encoding="utf-8")
    (SITE / "manifest.json").write_text(
        json.dumps(MANIFEST, indent=2, ensure_ascii=False), encoding="utf-8")
    (SITE / "sw.js").write_text(
        SERVICE_WORKER.format(versao=agora.strftime("%Y%m%d%H%M")),
        encoding="utf-8")
    # Impede o Jekyll do Pages de engolir arquivos e pastas iniciados por _
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    if not (SITE / "icones" / "icone-192.png").exists():
        print("! icones ausentes - rode antes: py gerar_icones.py")

    print("site/ pronto:")
    for arquivo in sorted(SITE.rglob("*")):
        if arquivo.is_file():
            print("   {0:<34} {1:>7} bytes".format(
                str(arquivo.relative_to(SITE)), arquivo.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
