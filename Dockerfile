FROM python:3.12.3

WORKDIR /app


RUN apt-get update && \
    apt-get install -y make && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["make", "run"]