FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV WORKERS=4
EXPOSE 7878

CMD ["sh", "-c", "gunicorn -w $WORKERS --bind 0.0.0.0:7878 run:app"]