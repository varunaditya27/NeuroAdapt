FROM python:3.11-slim

WORKDIR /app/quantum

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app/quantum

ENV PYTHONUNBUFFERED=1

USER app

# Batch-style default command; override in compose for retrain/inference jobs.
CMD ["python", "train.py"]
