FROM python:3.12-slim

WORKDIR /app

# Copied and installed before the rest of the source so Docker's layer
# cache only reinstalls dependencies when requirements.txt actually
# changes, not on every code edit.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
