.PHONY: up down test test-engine test-api test-web benchmark proto
up:
	docker compose up --build -d --wait
down:
	docker compose down
test: test-engine test-api test-web
test-engine:
	cd engine && go vet ./... && go test -race -count=1 ./...
test-api:
	./scripts/test-api.sh -v
test-web:
	cd web && npm ci && npm run check && npm run build
benchmark:
	./bench/run.sh
proto:
	./scripts/generate-proto.sh
