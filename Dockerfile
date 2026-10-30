FROM python:3.12-slim
WORKDIR /srv/app
ENV PYTHONUNBUFFERED=1
COPY app/backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt pymupdf pypdf python-multipart
COPY app/backend backend
COPY app/data data
WORKDIR /srv/app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
