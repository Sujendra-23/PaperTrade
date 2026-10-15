#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
# Requires protoc, Go, and uv; generated clients are checked into the repository.
go install google.golang.org/protobuf/cmd/protoc-gen-go@v1.36.11
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@v1.6.1
PATH="$(go env GOPATH)/bin:$PATH" protoc -I engine/pb \
  --go_out=engine/pb --go_opt=paths=source_relative \
  --go-grpc_out=engine/pb --go-grpc_opt=paths=source_relative engine/pb/engine.proto
uv run --project api python -m grpc_tools.protoc -I engine/pb \
  --python_out=api/papertrade/generated --grpc_python_out=api/papertrade/generated engine/pb/engine.proto
uv run --project api python -c "from pathlib import Path; p=Path('api/papertrade/generated/engine_pb2_grpc.py'); p.write_text(p.read_text().replace('import engine_pb2 as engine__pb2','from . import engine_pb2 as engine__pb2'))"
