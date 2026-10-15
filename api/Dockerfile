FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY papertrade ./papertrade
RUN useradd -m trader
USER trader
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "papertrade.main:app", "--host", "0.0.0.0", "--port", "8000"]
