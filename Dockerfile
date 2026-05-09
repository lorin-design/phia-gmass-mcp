FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY lib/ /app/lib/
COPY server.py /app/server.py
COPY gmass_client.py /app/gmass_client.py

ENV PORT=8000
EXPOSE 8000

CMD ["python", "server.py"]
