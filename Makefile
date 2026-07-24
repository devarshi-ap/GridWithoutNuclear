postgres:
	docker compose up -d postgres

init:
	docker compose up airflow-init

up:
	docker compose up -d

dev:
	source venv/bin/activate && streamlit run app/Home.py

down:
	docker compose down

ps:
	docker compose ps

logs-webserver:
	docker compose logs airflow-webserver

logs-scheduler:
	docker compose logs airflow-scheduler

clean:
	docker compose down -v
	rm -rf logs/*
	rm -rf dags/*