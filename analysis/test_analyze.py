"""Confere a leitura dos CSVs do Locust. Uso: python analysis/test_analyze.py"""

import tempfile
from pathlib import Path

from analyze import summarize

HEADER = "Type,Name,Request Count,Failure Count,Median Response Time,Average Response Time,Min Response Time,Max Response Time,Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%"
ROWS = [
    "GET,01 https://example.com/,10,0,5,6,1,9,100,1,0,5,6,6,7,8,9,9,9,9,9,9",
    ",Aggregated,20,5,40,50.5,1,300,100,2.5,0.1,40,50,60,70,90,95,98,99,300,300,300",
]


def test_summarize():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "pc1_ruby_nocache_50u_stats.csv").write_text("\n".join([HEADER, *ROWS]))
        (tmp / "pc1_ruby_nocache_50u_stats_history.csv").write_text(HEADER)  # deve ser ignorado
        summary = summarize(tmp)

    assert len(summary) == 1
    row = summary.iloc[0]
    assert (row["pc"], row["version"], row["cache"], row["users"]) == ("pc1", "ruby", "nocache", 50)
    assert (row["median_ms"], row["p95_ms"], row["rps"]) == (40, 95, 2.5)
    assert row["failure_pct"] == 25


if __name__ == "__main__":
    test_summarize()
    print("ok")
