.PHONY: install run test seed migrate docker-up docker-down lint

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	. .venv/bin/activate && python run_api.py

test:
	. .venv/bin/activate && pytest -q

seed:
	. .venv/bin/activate && python -m scripts.seed

migrate:
	. .venv/bin/activate && alembic upgrade head

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
