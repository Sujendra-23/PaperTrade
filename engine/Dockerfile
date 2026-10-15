FROM golang:1.27-alpine AS build
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /engine ./cmd/server
FROM alpine:3.22
RUN adduser -D trader
USER trader
COPY --from=build /engine /engine
EXPOSE 50051
ENTRYPOINT ["/engine"]
