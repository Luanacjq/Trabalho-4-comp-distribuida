"""Executa todos os cenarios de teste de uma versao do Link Extractor.

Para cada modo de cache (com/sem) sobe a aplicacao com docker compose e
roda o Locust em modo headless para cada quantidade de usuarios, salvando
os CSVs e o relatorio HTML em results/.

Exemplos:
    python locust/run_scenarios.py --pc pc1 --version python --compose-dir python --host http://localhost:5000
    python locust/run_scenarios.py --pc pc1 --version ruby   --compose-dir ruby   --host http://localhost:4567
"""

import argparse
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCUSTFILE = ROOT / "locust" / "locustfile.py"
RESULTS = ROOT / "results"


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
    ], check=False)  # locust retorna 1 quando ha falhas; o teste ainda vale


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pc", required=True, help="nome da maquina, ex.: pc1 (usado no nome dos arquivos)")
    parser.add_argument("--version", required=True, help="python ou ruby (usado no nome dos arquivos)")
    parser.add_argument("--compose-dir", required=True, help="pasta com o docker-compose.yml da versao")
    parser.add_argument("--host", required=True, help="ex.: http://localhost:5000")
    parser.add_argument("--users", type=int, nargs="+", default=[1, 10, 50, 100])
    parser.add_argument("--duration", default="2m")
    parser.add_argument("--cache", nargs="+", choices=["cache", "nocache"], default=["cache", "nocache"])
    args = parser.parse_args()

    compose_dir = (ROOT / args.compose_dir).resolve()
    RESULTS.mkdir(exist_ok=True)

    for cache_mode in args.cache:
        env = {**os.environ, "USE_CACHE": "true" if cache_mode == "cache" else "false"}
        print(f"\n=== {args.version} / {cache_mode}: subindo aplicacao ===", flush=True)
        compose(compose_dir, "up", "-d", "--build", "--force-recreate", env=env)
        wait_for_api(args.host)
        try:
            for users in args.users:
                # Cada teste comeca com o cache vazio, para ser comparavel
                compose(compose_dir, "exec", "-T", "redis", "redis-cli", "FLUSHALL")
                prefix = RESULTS / f"{args.pc}_{args.version}_{cache_mode}_{users}u"
                print(f"\n--- {prefix.name}: {users} usuarios por {args.duration} ---", flush=True)
                run_locust(args.host, users, args.duration, prefix)
        finally:
            compose(compose_dir, "down")


if __name__ == "__main__":
    main()
