"""Executa todos os cenarios de teste de uma versao do Link Extractor.

Para cada modo de cache (com/sem) sobe a aplicacao com docker compose e
roda o Locust em modo headless para cada quantidade de usuarios, salvando
os CSVs e o relatorio HTML em results/.

Exemplos:
    python locust/run_scenarios.py --pc pc1 --version python
    python locust/run_scenarios.py --pc pc1 --version ruby
    python locust/run_scenarios.py --pc pc1 --version python --users 1 --duration 20s --cache cache
    # ponto de falha: 1000, 10000, ... usuarios ate passar de 5% de falhas
    python locust/run_scenarios.py --pc pc1 --version python --cache cache --users 1000 --until-failure 5
"""

import argparse
import csv
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCUSTFILE = ROOT / "locust" / "locustfile.py"
RESULTS = ROOT / "results"

# Pasta do docker-compose.yml e endereco da API de cada versao
VERSIONS = {
    "python": (ROOT / "python", "http://localhost:5000"),
    "ruby": (ROOT / "ruby", "http://localhost:4567"),
}
CACHE_MODES = {"cache": "true", "nocache": "false"}
# O front-end nao e usado nos testes; porta alternativa evita conflito com a 80
DEFAULT_WEB_PORT = "8080"


def compose(compose_dir, *args, env=None):
    subprocess.run(["docker", "compose", *args], cwd=compose_dir, env=env, check=True)


def wait_for_api(host, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(host + "/", timeout=5)
            return
        except OSError:
            time.sleep(2)
    sys.exit(f"API nao respondeu em {host} apos {timeout}s")


def run_locust(host, users, duration, prefix):
    spawn_rate = max(1, users // 10)
    # Um processo do Locust satura uma CPU por volta de mil usuarios
    processes = ["--processes", "-1"] if users >= 1000 else []
    subprocess.run([
        sys.executable, "-m", "locust",
        "-f", str(LOCUSTFILE),
        "--headless",
        "--host", host,
        "-u", str(users),
        "-r", str(spawn_rate),
        "-t", duration,
        "--csv", str(prefix),
        "--html", f"{prefix}.html",
        "--only-summary",
        *processes,
    ], check=False)  # locust retorna 1 quando ha falhas; o teste ainda vale


def failure_pct(prefix):
    """Percentual de falhas da linha Aggregated do CSV gerado pelo Locust."""
    with open(f"{prefix}_stats.csv", newline="") as f:
        aggregated = next(row for row in csv.DictReader(f) if row["Name"] == "Aggregated")
    requests = int(aggregated["Request Count"])
    return 100 * int(aggregated["Failure Count"]) / max(requests, 1)


def user_counts(args):
    """Quantidades de usuarios a testar; com --until-failure, continua x10 apos a lista."""
    yield from args.users
    users = args.users[-1]
    while args.until_failure is not None and users * 10 <= args.max_users:
        users *= 10
        yield users


def run_cache_mode(args, cache_mode):
    compose_dir, host = VERSIONS[args.version]
    env = {**os.environ, "USE_CACHE": CACHE_MODES[cache_mode]}
    env.setdefault("WEB_PORT", DEFAULT_WEB_PORT)

    print(f"\n=== {args.version} / {cache_mode}: subindo aplicacao ===", flush=True)
    compose(compose_dir, "up", "-d", "--build", "--force-recreate", env=env)
    try:
        wait_for_api(host)
        for users in user_counts(args):
            # Cada teste comeca com o cache vazio, para ser comparavel
            compose(compose_dir, "exec", "-T", "redis", "redis-cli", "FLUSHALL", env=env)
            prefix = RESULTS / f"{args.pc}_{args.version}_{cache_mode}_{users}u"
            print(f"\n--- {prefix.name}: {users} usuarios por {args.duration} ---", flush=True)
            run_locust(host, users, args.duration, prefix)

            failures = failure_pct(prefix)
            print(f"--- {prefix.name}: {failures:.2f}% de falhas ---", flush=True)
            if args.until_failure is not None and failures > args.until_failure:
                print(f"=== ponto de falha: {users} usuarios ({failures:.2f}% > {args.until_failure}%) ===", flush=True)
                break
    finally:
        compose(compose_dir, "down", env=env)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pc", required=True, help="nome da maquina, ex.: pc1 (usado no nome dos arquivos)")
    parser.add_argument("--version", required=True, choices=VERSIONS)
    parser.add_argument("--users", type=int, nargs="+", default=[1, 10, 50, 100])
    parser.add_argument("--duration", default="2m")
    parser.add_argument("--cache", nargs="+", choices=CACHE_MODES, default=list(CACHE_MODES))
    parser.add_argument("--until-failure", type=float, metavar="PCT",
                        help="apos a lista de --users, multiplica por 10 ate as falhas passarem de PCT%%")
    parser.add_argument("--max-users", type=int, default=100_000, help="limite do --until-failure")
    return parser.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)
    for cache_mode in args.cache:
        run_cache_mode(args, cache_mode)


if __name__ == "__main__":
    main()
