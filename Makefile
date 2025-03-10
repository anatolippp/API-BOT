build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down
.PHONY: logs
logs:
	docker-compose logs -f
