package main

import (
	pb "github.com/Sujendra-23/PaperTrade/engine/pb"
	"github.com/Sujendra-23/PaperTrade/engine/service"
	"google.golang.org/grpc"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	addr := os.Getenv("ENGINE_LISTEN")
	if addr == "" {
		addr = ":50051"
	}
	l, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()
	pb.RegisterMatchingEngineServer(s, service.New())
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	go func() { <-stop; s.GracefulStop() }()
	log.Printf("matching engine listening on %s", addr)
	if err = s.Serve(l); err != nil {
		log.Fatal(err)
	}
}
