FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["sh", "-c", "python manage.py migrate contenttypes && python manage.py migrate auth && python manage.py migrate admin && python manage.py migrate sessions && python manage.py migrate --run-syncdb && python manage.py runserver 0.0.0.0:8001"