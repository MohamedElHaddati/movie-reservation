FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
