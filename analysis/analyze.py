"""Junta os resultados do Locust numa planilha unica e gera os graficos.

Le a linha "Aggregated" de cada results/<pc>_<versao>_<cache>_<N>u_stats.csv,
salva results/summary.csv e gera, para cada PC e metrica, um grafico de
metrica x numero de usuarios comparando Python e Ruby (com e sem cache)
DENTRO do mesmo PC.

Uso:
    python analysis/analyze.py
"""

import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # gera PNG sem precisar de janela
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
CHARTS = RESULTS / "charts"

FILENAME = re.compile(r"(?P<pc>[^_]+)_(?P<version>python|ruby)_(?P<cache>cache|nocache)_(?P<users>\d+)u_stats\.csv")

# coluna do CSV do Locust -> nome na planilha
COLUMNS = {
    "Request Count": "requests",
    "Failure Count": "failures",
    "Average Response Time": "avg_ms",
    "Median Response Time": "median_ms",
    "90%": "p90_ms",
    "95%": "p95_ms",
    "99%": "p99_ms",
    "Max Response Time": "max_ms",
    "Requests/s": "rps",
}

# metrica -> titulo do eixo Y
CHART_METRICS = {
    "median_ms": "Mediana do tempo de resposta (ms)",
    "avg_ms": "Tempo medio de resposta (ms)",
    "p95_ms": "Percentil 95 do tempo de resposta (ms)",
    "p99_ms": "Percentil 99 do tempo de resposta (ms)",
    "rps": "Vazao (requisicoes/s)",
    "failure_pct": "Falhas (%)",
}

SERIES_COLORS = {
    ("python", "cache"): "#1f77b4",
    ("python", "nocache"): "#9ecae9",
    ("ruby", "cache"): "#d62728",
    ("ruby", "nocache"): "#f4a3a3",
}


def read_test(path):
    """Uma linha da planilha: cenario (do nome do arquivo) + metricas agregadas."""
    scenario = FILENAME.fullmatch(path.name).groupdict()
    stats = pd.read_csv(path)
    aggregated = stats[stats["Name"] == "Aggregated"].iloc[0]
    row = {**scenario, **{new: aggregated[old] for old, new in COLUMNS.items()}}
    row["users"] = int(row["users"])
    return row


def summarize(results_dir):
    files = sorted(p for p in results_dir.glob("*_stats.csv") if FILENAME.fullmatch(p.name))
    if not files:
        return pd.DataFrame()
    summary = pd.DataFrame([read_test(p) for p in files])
    summary["failure_pct"] = 100 * summary["failures"] / summary["requests"].clip(lower=1)
    return summary.sort_values(["pc", "version", "cache", "users"], ignore_index=True)


def plot_pc(pc_data, pc, metric, label, out_dir, name=None):
    # Barras agrupadas: um grupo por quantidade de usuarios, uma barra por versao/cache
    table = pc_data.pivot(index="users", columns=["version", "cache"], values=metric)
    fig, ax = plt.subplots(figsize=(9, 5))
    table.plot.bar(ax=ax, rot=0, width=0.8, edgecolor="black", linewidth=0.5,
                   color=[SERIES_COLORS[col] for col in table.columns])
    # Valor em cima da barra: com cache (~1 ms) a barra fica invisivel ao lado do sem cache
    # (cenarios que nao rodaram, ex.: sem cache com 1000 usuarios, ficam sem rotulo)
    # (rotulos vem da tabela: o pandas desenha NaN como barra de altura 0)
    for bars, column in zip(ax.containers, table.columns):
        ax.bar_label(bars, labels=["" if pd.isna(v) else f"{v:.0f}" for v in table[column]],
                     fontsize=7, padding=2)
    ax.margins(y=0.1)
    ax.set_title(f"{label} - {pc}" + (f" ({name})" if name else ""))
    ax.set_xlabel("Usuarios virtuais")
    ax.set_ylabel(label)
    ax.grid(axis="y", alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend([f"{version} / {cache}" for version, cache in table.columns])
    fig.tight_layout()
    suffix = f"_{name}" if name else ""
    fig.savefig(out_dir / f"{pc}_{metric}{suffix}.png", dpi=150)
    plt.close(fig)


def main():
    summary = summarize(RESULTS)
    if summary.empty:
        sys.exit(f"Nenhum *_stats.csv encontrado em {RESULTS}")

    summary.to_csv(RESULTS / "summary.csv", index=False)
    print(summary.to_string(index=False))

    CHARTS.mkdir(exist_ok=True)
    for pc, pc_data in summary.groupby("pc"):
        # Comparacao base: so as quantidades de usuarios que rodaram nos 4 cenarios
        scenarios_per_users = pc_data.groupby("users").size()
        base_users = scenarios_per_users[scenarios_per_users == scenarios_per_users.max()].index
        base = pc_data[pc_data["users"].isin(base_users)]
        for metric, label in CHART_METRICS.items():
            plot_pc(base, pc, metric, label, CHARTS)

        # Escalonamento x10 (--until-failure): so com cache, ate o ponto de falha
        cache = pc_data[pc_data["cache"] == "cache"]
        if cache["users"].nunique() > len(base_users):
            for metric, label in CHART_METRICS.items():
                plot_pc(cache, pc, metric, label, CHARTS, name="escalonamento")
    print(f"\nPlanilha: {RESULTS / 'summary.csv'}\nGraficos: {CHARTS}")


if __name__ == "__main__":
    main()
