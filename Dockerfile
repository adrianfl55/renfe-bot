FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml requirements.txt /app/
RUN uv pip install --system -r requirements.txt

COPY . /app

ENV PYTHONPATH="/app/src"

CMD ["python3", "-u", "src/bot.py"]
