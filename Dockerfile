# Imagem base Python 3.11 (compatível com 3.10+)
FROM python:3.11-slim

# Evitar buffering e criar usuário não-root
ENV PYTHONUNBUFFERED=1
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar apenas app e src (produção)
COPY app/ ./app/
COPY src/ ./src/

# Dono dos arquivos
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Comando: API FastAPI (app.main:app na Fase 6)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
