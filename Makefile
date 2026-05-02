.PHONY: install dev migrate test lint format deploy logs

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

dev:
	.venv/bin/watchfiles ".venv/bin/python -m bot" bot/

migrate:
	.venv/bin/python -m bot.db migrate

test:
	.venv/bin/pytest -v

lint:
	.venv/bin/ruff check .
	.venv/bin/mypy --strict bot/

format:
	.venv/bin/ruff format .

deploy:
	bash deploy/deploy.sh

logs:
	@if [ -f .env.deploy ]; then . .env.deploy; fi && \
	ssh "$${DROPLET_USER:-root}@$${DROPLET_IP}" "journalctl -u youtube-smart-transcriber -f --no-pager"
