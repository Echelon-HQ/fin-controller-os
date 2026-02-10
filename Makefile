.PHONY: setup up-ingest up-local sync-up sync-down clean

setup:
	chmod +x scripts/*.sh
	cp .env.example .env

# --- CLOUD VM COMMANDS (The Writer) ---
up-ingest:
	docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.ingest.yml up --build

sync-up:
	./scripts/snapshot_push.sh

# --- LOCAL LAPTOP COMMANDS (The Reader) ---
up-local:
	docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.local.yml up -d --build

sync-down:
	./scripts/snapshot_pull.sh

# --- UTILITIES ---
clean:
	docker compose -f infra/docker-compose.base.yml down --remove-orphans
