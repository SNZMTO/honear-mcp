# L'image du MCP de Honear. On installe le serveur et ses dépendances avec uv, d'après uv.lock, dans un environnement à part ;
# puis on ne garde que lui et Python : ni uv, ni sources, ni outils de développement. Il tourne sans droits ; compose.yaml lui
# donne son utilisateur, un système de fichiers en lecture seule et le seul dossier où il écrit, celui des listes.
#
#   docker build -t honear-mcp .        (deploiement/mettre-en-ligne.sh le fait, étiqueté à son commit)

# Python 3.13, Debian 13, et uv 0.13.1, figés à leur empreinte : la même image à chaque construction.
ARG PYTHON=python:3.13.16-slim-trixie@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
ARG UV=ghcr.io/astral-sh/uv:0.13.1@sha256:4a1f3666816dafadd20ceb71eac9a7d56d7ef30279f7d64048519ab901ada336

FROM ${UV} AS uv

FROM ${PYTHON} AS construction
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/mcp
WORKDIR /projet
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src src
RUN uv sync --frozen --no-dev --no-editable

FROM ${PYTHON}
COPY --from=construction /mcp /mcp
ENV PATH=/mcp/bin:$PATH \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  HONEAR_MCP_HOTE=0.0.0.0 \
  HONEAR_MCP_LISTES=/listes
USER nobody
EXPOSE 8790 8791
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8790/sante', timeout=2)"]
CMD ["honear-mcp"]
