#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../engine"
go run ./cmd/bench -n 1000000
