# Trabalho 4 – Testes de desempenho com o Link Extractor

Testes de carga com [Locust](https://locust.io/) nas versões Python e Ruby do
serviço de extração de links do [linkextractor](https://github.com/ibnesayeed/linkextractor),
com e sem cache (Redis).

## Estrutura

```
web/               front-end PHP (o mesmo para as duas versões)
python/            API Python (step5 do tutorial) + docker-compose.yml
ruby/              API Ruby (step6 do tutorial) + docker-compose.yml
locust/
  locustfile.py    usuário virtual: sequência de 10 invocações, 1 URL diferente em cada
  run_scenarios.py roda todos os cenários de uma versão e salva os resultados
analysis/
  analyze.py       junta os CSVs em results/summary.csv e gera os gráficos
  test_analyze.py  verificação rápida do analyze.py
results/           gerado pelos testes (CSVs, relatórios HTML, summary.csv, charts/)
ROTEIRO.md         passo a passo da execução e da montagem dos slides
```

## Pré-requisitos

- Docker com Docker Compose
- Python 3: `pip install -r requirements.txt` (locust, pandas, matplotlib)

## Subir a aplicação manualmente

```bash
cd python        # ou: cd ruby
docker compose up -d --build                     # com cache
USE_CACHE=false docker compose up -d --build     # sem cache
WEB_PORT=8080 docker compose up -d --build       # front em outra porta, se a 80 estiver ocupada
docker compose down
```

- API Python: http://localhost:5000/api/https://www.php.net/
- API Ruby: http://localhost:4567/api/https://www.php.net/
- Front-end: http://localhost/ (ou a porta do `WEB_PORT`)

## Rodar os testes

```bash
python locust/run_scenarios.py --pc pc1 --version python
python locust/run_scenarios.py --pc pc1 --version ruby
python analysis/analyze.py
```

Teste rápido de verificação: `--users 1 --duration 20s --cache cache`.

O `run_scenarios.py` sobe a versão com `docker compose`, esvazia o Redis antes de
cada teste e derruba tudo no final. Durante os testes, o front-end sobe na porta
8080 (ou na do `WEB_PORT`), para não conflitar com outro serviço na porta 80.

## Cenários

| Parâmetro       | Valores                          |
|-----------------|----------------------------------|
| Versão          | python, ruby                     |
| Cache           | cache, nocache                   |
| Usuários        | 1, 10, 50, 100 (spawn rate = usuários/10) |
| Duração         | 2 min por teste                  |
| Usuário virtual | 10 invocações seguidas (URLs em `locust/locustfile.py`), pausa de 1–2 s entre sequências |

16 testes por PC (cerca de 40 min), 32 no total. Python e Ruby são comparadas
dentro do mesmo PC; o segundo PC serve para ver se o resultado se repete.

## Resultados

Cada teste gera em `results/`:

- `<pc>_<versao>_<cache>_<N>u_stats.csv`: média, mediana, mín/máx, percentis e req/s, por URL e agregado (linha `Aggregated`)
- `<pc>_<versao>_<cache>_<N>u_failures.csv`: falhas
- `<pc>_<versao>_<cache>_<N>u_stats_history.csv`: evolução ao longo do tempo
- `<pc>_<versao>_<cache>_<N>u.html`: relatório com gráficos do próprio Locust

O `analysis/analyze.py` gera:

- `results/summary.csv`: uma linha por teste (abre no Excel/Google Sheets)
- `results/charts/<pc>_<metrica>.png`: barras agrupadas por nº de usuários, 4 barras por grupo (Python/Ruby × com/sem cache), com o valor em cima de cada barra

## Diferenças em relação ao tutorial

- `USE_CACHE=false` faz a API (nas duas versões) não ler nem gravar no Redis.
- Ruby: imagem `ruby:3.3` (a 2.6 não instala mais as gems atuais), `URI.open` no lugar de
  `open`, gems `rackup` e `puma` (exigidas pelo Sinatra 4) e `host_authorization` liberado
  para o front acessar a API como `api:4567`.
- Python: `timeout=60` no `requests.get`, igual ao padrão do open-uri do Ruby. Sem isso, um
  site que não responde prende a requisição para sempre.
- Front-end PHP único em `web/`: era idêntico nas duas versões.
