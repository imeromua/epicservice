COMPOSE ?= docker compose

.PHONY: up down logs ps migrate restart

up:
	$(COMPOSE) up -d --build db redis
	$(COMPOSE) run --rm migrate
	$(COMPOSE) up -d --build webapp bot

migrate:
	$(COMPOSE) run --rm migrate

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=100

down:
	$(COMPOSE) down -v

restart:
	$(COMPOSE) restart webapp bot
