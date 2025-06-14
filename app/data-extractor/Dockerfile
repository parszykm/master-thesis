FROM python:3.9-slim

WORKDIR /app

COPY app.py /app/

RUN pip install --no-cache-dir flask psycopg2-binary

EXPOSE 8000

CMD ["flask", "run", "--host=0.0.0.0", "--port=8000"]
ENV FLASK_APP=app.py