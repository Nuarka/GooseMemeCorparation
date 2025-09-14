
.PHONY: run dev set-webhook clear-webhook

run:
	docker compose up --build -d

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

set-webhook:
	. ./.env && bash scripts/set_webhook.sh

clear-webhook:
	. ./.env && bash scripts/clear_webhook.sh
