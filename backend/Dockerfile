FROM python:3.12-slim

COPY . /app

WORKDIR /app

EXPOSE 8800

RUN apt-get update && apt-get install -y libmagic1

RUN pip install -r requirements.txt

CMD [ "uvicorn", "--host", "0.0.0.0", "--port", "8800", "main:app" ]