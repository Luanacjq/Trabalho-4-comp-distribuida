# Trabalho 4 – Testes de desempenho com o Link Extractor

Testes de carga com [Locust](https://locust.io/) nas versões Python e Ruby do
serviço de extração de links do [linkextractor](https://github.com/ibnesayeed/linkextractor),
com e sem cache (Redis).

## Estrutura

```
python/            versão Python da API (step5 do tutorial) + front PHP + Redis
ruby/              versão Ruby da API (step6) – Pessoa B
locust/
  locustfile.py    usuário virtual: sequência de 10 invocações, 1 URL diferente em cada
  run_scenarios.py roda todos os cenários de uma versão e salva os resultados
results/           CSVs e relatórios HTML gerados pelo Locust
```

## Pré-requisitos

- Docker com Docker Compose
- Python 3 e Locust: `pip install -r locust/requirements.txt`

## Subir a aplicação manualmente (versão Python)

```bash
cd python
docker compose up -d --build                    # com cache
USE_CACHE=false docker compose up -d --build    # sem cache (bash)
$env:USE_CACHE="false"; docker compose up -d --build   # sem cache (PowerShell)
```

- API: http://localhost:5000/api/https://example.com/
- Front-end: http://localhost/

## Rodar os testes

Os testes rodam em dois PCs (`pc1` e `pc2`), e **cada PC roda as duas versões**.
Assim Python e Ruby são comparadas dentro da mesma máquina, e as duas máquinas
servem para conferir se o resultado se repete. Em cada PC, rode os dois comandos,
um depois do outro, trocando `pc1` pelo nome do PC:

```bash
python locust/run_scenarios.py --pc pc1 --version python --compose-dir python --host http://localhost:5000
python locust/run_scenarios.py --pc pc1 --version ruby   --compose-dir ruby   --host http://localhost:4567
```

Cada comando roda, para cada modo de cache, 4 testes de 2 minutos (1, 10, 50 e 100
usuários). São 8 testes por versão, cerca de 40 minutos por PC. Antes de cada teste
o Redis é esvaziado, para que todos os testes comecem do mesmo estado. Não rodem
os dois PCs ao mesmo tempo na mesma rede: nos testes sem cache um atrapalharia a
internet do outro.

Para um teste rápido de verificação:

```bash
python locust/run_scenarios.py --pc pc1 --version python --compose-dir python --host http://localhost:5000 --users 1 --duration 20s --cache cache
```

## Cenários

| Parâmetro       | Valores                          |
|-----------------|----------------------------------|
| Versão          | python, ruby                     |
| Cache           | cache, nocache                   |
| Usuários        | 1, 10, 50, 100 (spawn rate = usuários/10) |
| Duração         | 2 min por teste                  |
| Usuário virtual | 10 invocações seguidas (URLs em `locust/locustfile.py`), pausa de 1–2 s entre sequências |

Total: 2 × 2 × 4 = 16 testes por PC, 32 no total.

## Resultados

Cada teste gera em `results/`:

- `<pc>_<versao>_<cache>_<N>u_stats.csv`: média, mediana, mín/máx, percentis (50–100%) e req/s, por URL e agregado (linha `Aggregated`)
- `<pc>_<versao>_<cache>_<N>u_failures.csv`: falhas
- `<pc>_<versao>_<cache>_<N>u_stats_history.csv`: evolução ao longo do tempo
- `<pc>_<versao>_<cache>_<N>u.html`: relatório com gráficos

Exemplo: `pc2_ruby_nocache_50u_stats.csv`. Como o nome do PC está no arquivo,
os resultados das duas máquinas podem ir para a mesma pasta `results/` no git
sem sobrescrever um ao outro.

## Contrato para a versão Ruby (Pessoa B)

Para usar os mesmos scripts, a pasta `ruby/` precisa de:

1. um `docker-compose.yml` com os serviços `api`, `web` e `redis`, sendo que o serviço Redis precisa se chamar `redis`;
2. a API exposta em `http://localhost:4567/api/<url>`;
3. a variável `USE_CACHE` (padrão `true`; `false` faz a API não ler nem gravar no Redis), repassada no compose como `USE_CACHE=${USE_CACHE:-true}`.

O script de análise e gráficos da Pessoa B deve ler o nome do PC do arquivo e
comparar Python × Ruby **dentro de cada PC**, nunca Python de um PC com Ruby do
outro.
