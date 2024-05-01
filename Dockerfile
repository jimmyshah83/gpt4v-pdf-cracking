FROM python:3.12-slim-bookworm

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install poppler-utils
RUN apt-get update && apt-get install -y poppler-utils

COPY . .

CMD ["python", "app.py"]