FROM python:3.11-slim
RUN pip install --no-cache-dir fastapi==0.115.6 "uvicorn[standard]==0.32.1" pandas==2.2.3
WORKDIR /srv
COPY app.py .
ENV TRANS_FILE=/data/raw/trans.asc
EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
