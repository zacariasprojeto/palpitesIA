# Usa python leve
FROM python:3.11-slim

# Evita problemas de buffer
ENV PYTHONUNBUFFERED=1

# Pasta da aplicação
WORKDIR /app

# Copia requisitos
COPY requirements.txt /app/

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o projeto inteiro
COPY . /app

# Expõe a porta usada pelo Fly
EXPOSE 8080

# Comando para iniciar o Flask
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
