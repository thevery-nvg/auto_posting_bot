FROM python:3.11-slim as builder

WORKDIR /app


RUN pip install poetry==1.7.1


COPY pyproject.toml poetry.lock ./


RUN poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app


COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/requirements.txt .


COPY src ./src
COPY run_polling.py .


ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1


CMD ["python", "run_polling.py"]