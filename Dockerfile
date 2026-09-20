FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY run_api.py .

ENV DATABASE_URL=postgresql+psycopg2://realworld:realworld@db:5432/realworld
ENV SECRET_KEY=change-me-in-production
ENV HOST=0.0.0.0
ENV PORT=8000
ENV AUTO_CREATE_TABLES=true

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python run_api.py"]
