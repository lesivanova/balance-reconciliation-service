FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app_new.py

CMD ["streamlit", "run", "app_new.py", "--server.port=8501", "--server.address=0.0.0.0"]
