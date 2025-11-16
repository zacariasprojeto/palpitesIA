# -------------------------
# BASE IMAGE
# -------------------------
FROM python:3.11-slim

# -------------------------
# SISTEMA E DEPENDÊNCIAS
# -------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -------------------------
# DIRETORIO DO PROJETO
# -------------------------
WORKDIR /app

# -------------------------
# COPIAR ARQUIVOS
# -------------------------
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# -------------------------
# EXPOR PORTA PARA RENDER
# -------------------------
EXPOSE 10000

# -------------------------
# DEFINIR VARIÁVEIS GLOBAIS
# -------------------------
ENV PORT=10000
ENV PYTHONUNBUFFERED=1

# -------------------------
# COMANDO DE EXECUÇÃO
# -------------------------
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]
