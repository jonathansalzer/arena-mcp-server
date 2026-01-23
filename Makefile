SHELL = /bin/sh

IMAGE_NAME=arena-mcp-server

.PHONY: dbuild drun dshell dclean

dbuild:
	docker compose -f docker-compose.yml build

drun:
	docker compose -f docker-compose.yml up -d

dshell:
	docker compose exec -it $(IMAGE_NAME) /bin/sh

dclean:
	docker compose -f docker-compose.yml down --rmi