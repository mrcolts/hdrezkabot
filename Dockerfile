FROM python:3.6
COPY requirements.txt /app/requirements/
RUN pip install -r /app/requirements/requirements.txt
COPY . /app/

