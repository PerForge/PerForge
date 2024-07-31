FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV WORKERS=4
ENV THREADS=4
ENV TIMEOUT=600
ENV PORT=7878

CMD ["sh", "-c", "gunicorn -w $WORKERS --threads $THREADS -t $TIMEOUT --bind 0.0.0.0:$PORT run:app"]