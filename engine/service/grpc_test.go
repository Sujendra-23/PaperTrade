package service

import (
	"context"
	"net"
	"testing"
	"time"

	pb "github.com/Sujendra-23/PaperTrade/engine/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/test/bufconn"
)

func TestGRPCTradeStream(t *testing.T) {
	listener := bufconn.Listen(1 << 20)
	srv := grpc.NewServer()
	impl := New()
	pb.RegisterMatchingEngineServer(srv, impl)
	go func() { _ = srv.Serve(listener) }()
	defer srv.Stop()
	conn, err := grpc.NewClient("passthrough:///bufnet", grpc.WithContextDialer(func(context.Context, string) (net.Conn, error) { return listener.Dial() }), grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	client := pb.NewMatchingEngineClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	stream, err := client.StreamTrades(ctx, &pb.Symbol{Symbol: "AAPL"})
	if err != nil {
		t.Fatal(err)
	}
	// Wait for subscription registration, rather than depending on RPC scheduling.
	deadline := time.Now().Add(time.Second)
	for {
		impl.mu.Lock()
		n := len(impl.subscribers)
		impl.mu.Unlock()
		if n == 1 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("subscriber was not registered")
		}
		time.Sleep(time.Millisecond)
	}
	_, err = client.PlaceOrder(ctx, &pb.Order{Id: "seller", AccountId: "s", Symbol: "AAPL", Side: "SELL", Kind: "LIMIT", Price: 100, Quantity: 2})
	if err != nil {
		t.Fatal(err)
	}
	_, err = client.PlaceOrder(ctx, &pb.Order{Id: "buyer", AccountId: "b", Symbol: "AAPL", Side: "BUY", Kind: "LIMIT", Price: 100, Quantity: 2})
	if err != nil {
		t.Fatal(err)
	}
	trade, err := stream.Recv()
	if err != nil {
		t.Fatal(err)
	}
	if trade.Quantity != 2 || trade.Price != 100 || trade.BuyerId != "b" || trade.SellerId != "s" {
		t.Fatalf("unexpected trade: %v", trade)
	}
}
