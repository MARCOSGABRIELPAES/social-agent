# social-agent

Agente de metricas e analise para dois perfis do Instagram:

- **@marcosgabriel_ia** — pessoal / fundador, meta de autoridade
- **@bombeiro_ia** — especializado, meta de conversao

Ele faz a parte analitica inteira. Voce faz a parte manual (gravar, editar,
postar). O agente diz **o que postar, em que formato, em que dia e horario** —
sempre com o numero que sustenta a recomendacao.

## 📱 Painel

**<https://marcosgabrielpaes.github.io/social-agent/>**

Instalavel: abra no celular e use *Compartilhar → Adicionar a Tela de Inicio*.
Vira um app em tela cheia e continua abrindo sem rede.

Atualiza sozinho **toda segunda as 8h** por GitHub Actions — nao depende de PC
ligado nem de nenhum app aberto. Para rodar na hora, use o botao *Run workflow*
na aba Actions, ou:

```bash
gh workflow run painel.yml
```

## Como funciona

```
GitHub Actions (cron semanal)
  -> coleta na API oficial da Meta
  -> banco SQLite versionado no repo (o historico que o Instagram nao guarda)
  -> motor de metricas
  -> site/ publicado no GitHub Pages como PWA
  -> briefing.md pronto para colar numa IA
```

O banco fica **versionado de proposito**: sem ele, cada execucao na nuvem
comecaria do zero e o historico se perderia.

## Levar os dados para uma IA

O painel tem um botao **Copiar briefing**. Ele copia um texto que ja carrega
os numeros, a definicao de cada metrica no contexto, o que performou bem e mal,
e o pedido de estrategia escrito. Cole em qualquer assistente e peca o plano.

O mesmo texto fica em <https://marcosgabrielpaes.github.io/social-agent/briefing.md>.

O banco importa porque o Instagram apaga o passado: varios recortes so mostram
os ultimos dias. A cada coleta o agente carimba os numeros e monta a serie
historica que o app nao guarda.

## Rodar

```bash
py -3.13 -m pip install -r requirements.txt
```

### Modo manual (funciona hoje, sem configurar nada)

```bash
py -3.13 importar.py --modelo                    # cria dados/modelo_import.csv
py -3.13 importar.py dados/modelo_import.csv     # importa
py -3.13 importar.py --seguidores bombeiro_ia=4820 marcosgabriel_ia=1960
py -3.13 analisar.py --abrir
```

O importador tambem le direto o export CSV do **Metricool** e do **Later** —
as colunas sao reconhecidas por apelido, entao nome e ordem nao importam.

### Modo automatico (a partir do token da Meta)

```bash
py -3.13 coletar.py --descobrir    # preenche os ig_user_id sozinho
py -3.13 coletar.py                # puxa 90 dias das duas contas
py -3.13 analisar.py
```

### No Claude Code

```
/social-semanal
```

Roda o ciclo inteiro e ainda escreve a pauta da proxima semana em
`relatorios/plano-AAAA-MM-DD.md`.

## Ligando o modo automatico

So a API oficial da Meta e usada. Nada de login com senha ou scraping — e
exatamente isso que separa coleta legitima de automacao que derruba a conta.

1. As duas contas precisam ser **Profissional** (Business ou Creator):
   Instagram > Configuracoes > Tipo de conta.
2. Vincule cada uma a uma **Pagina do Facebook** (pode ser uma pagina vazia,
   criada so para isso): Instagram > Configuracoes > Central de Contas.
3. Crie um app em <https://developers.facebook.com/apps> do tipo **Business**.
4. Adicione o produto **Instagram Graph API**.
5. Em <https://developers.facebook.com/tools/explorer>, selecione o app e gere
   um token com as permissoes:
   `instagram_basic`, `instagram_manage_insights`, `pages_show_list`,
   `pages_read_engagement`, `business_management`.
6. Troque por um token de 60 dias em
   <https://developers.facebook.com/tools/debug/accesstoken> (botao
   *Extend Access Token*).
7. `copy .env.example .env` e cole o token em `IG_ACCESS_TOKEN`.
8. `py -3.13 coletar.py --descobrir`

O agente avisa no terminal quando faltarem menos de 10 dias para o token
expirar. Renove repetindo os passos 5 e 6.

## Como ler os numeros

| Metrica | Definicao | Por que essa e nao outra |
|---|---|---|
| **Engajamento** | interacoes / **alcance** | Dividir por seguidores mistura quem nem viu o post. Por alcance mede a qualidade real do conteudo. |
| **Indice de alcance** | alcance / mediana do perfil | 1.0x = seu post tipico. 2.0x = o dobro. Compara voce com voce, nao com influenciador de outro porte. |
| **Taxa de salvamento** | salvamentos / alcance | Hoje e o sinal que mais expande alcance no Instagram. |
| **Taxa de compartilhamento** | compartilhamentos / alcance | Vetor de crescimento organico mais barato que existe. |

Tudo usa **mediana**, nao media: um unico post viral distorce a media e faz o
perfil parecer melhor do que entrega toda semana.

O mapa de horarios so aparece com **15+ posts** no historico, e janelas com um
unico post ficam fora da recomendacao. Com n=1 o numero e sorte, nao padrao.

## Pilares de conteudo

`config/perfis.json` define os pilares e as palavras-chave que classificam
cada post pela legenda. **Esse arquivo e o que da qualidade a analise** — sem
pilar bem definido o agente so consegue dizer "esse post foi bem", em vez de
"posts tecnicos rendem 1.5x".

Os pilares atuais sao um chute inicial pelo nome dos perfis. Ajuste as
palavras-chave para as que voce realmente usa nas legendas.

## Arquivos

```
config/perfis.json     perfis, pilares e parametros de analise
coletar.py             modo auto: Graph API
importar.py            modo manual: CSV
analisar.py            analise + relatorio + resumo.json
social/graph.py        cliente da Meta, com fallback de metricas por versao
social/metricas.py     KPIs, ranking, heatmap, diagnosticos
social/relatorio.py    HTML auto-contido (tema claro e escuro)
dados/social.db        historico (nao versionado)
relatorios/ultimo.html sempre o relatorio mais recente
```

## Limpar os dados de teste

O banco vem com 52 posts sinteticos usados para validar o pipeline:

```bash
del dados\social.db dados\teste_sintetico.csv
```
