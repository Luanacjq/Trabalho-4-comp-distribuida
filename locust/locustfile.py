"""Usuario virtual do teste de carga do Link Extractor.

Cada usuario executa repetidamente uma sequencia de 10 invocacoes ao servico
de extracao de links, passando uma URL diferente em cada invocacao.
O mesmo script serve para a versao Python (porta 5000) e Ruby (porta 4567);
basta mudar o --host.
"""

from locust import HttpUser, between, task

# Lista fixa de 10 URLs, igual para as duas versoes (Python e Ruby)
URLS = [
    "https://example.com/",
    "https://www.python.org/",
    "https://www.ruby-lang.org/en/",
    "https://www.sqlite.org/",
    "https://www.debian.org/",
    "https://www.w3.org/",
    "https://www.apache.org/",
    "https://www.kernel.org/",
    "https://www.php.net/",
    "https://www.postgresql.org/",
]


class LinkExtractorUser(HttpUser):
    # Pausa entre uma sequencia de 10 invocacoes e a proxima
    wait_time = between(1, 2)

    @task
    def sequencia_de_extracoes(self):
        for i, url in enumerate(URLS, start=1):
            # name agrupa as estatisticas por URL no relatorio do Locust
            self.client.get(f"/api/{url}", name=f"{i:02d} {url}", timeout=60)
