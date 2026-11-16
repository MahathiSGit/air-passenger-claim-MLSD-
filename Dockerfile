FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/* && python -m pip install --upgrade pip && python -m pip install -r requirements.txt
COPY app ./app
COPY rag ./rag
COPY agents ./agents
COPY documents ./documents
COPY eval ./eval
COPY contracts ./contracts
COPY docs ./docs
COPY loadtest ./loadtest
RUN mkdir -p /app/data/rag
EXPOSE 8000 8001 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

