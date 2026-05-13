FROM python:3.11-slim

WORKDIR /app

# Устанавливаем пакеты напрямую
RUN pip install --no-cache-dir \
    --index-url https://pypi.org/simple \
    fastapi \
    uvicorn \
    numpy \
    scipy \
    pydantic

COPY ./app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
