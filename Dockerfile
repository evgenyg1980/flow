FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN apt-get update && apt-get install -y ffmpeg

CMD ["gunicorn", "-b", "0.0.0.0:5000", "server:app"]
