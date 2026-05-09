FROM python:3.11-slim

WORKDIR /app/quantum

RUN addgroup --system app && adduser --system --ingroup app app

COPY quantum/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=app:app quantum /app/quantum
COPY --chown=app:app backend /app/backend
COPY --chown=app:app shared_config.py /app/shared_config.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER app

# Batch-style default command; override in compose for retrain/inference jobs.
CMD ["python", "train.py"]
