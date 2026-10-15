package service

import (
	"context"
	pb "github.com/Sujendra-23/PaperTrade/engine/pb"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"testing"
)

func TestIdempotency(t *testing.T) {
	s := New()
	ctx := context.Background()
	o := &pb.Order{Id: "a", AccountId: "u", Symbol: "AAPL", Side: "BUY", Kind: "LIMIT", Price: 100, Quantity: 2}
	a, err := s.PlaceOrder(ctx, o)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := s.PlaceOrder(ctx, o)
	if a.Remaining != b.Remaining {
		t.Fatal("repeated execution")
	}
	o.Quantity = 3
	if _, err = s.PlaceOrder(ctx, o); status.Code(err) != codes.AlreadyExists {
		t.Fatal(err)
	}
	state, _ := s.Health(ctx, &pb.Empty{})
	if state.Commands != 1 {
		t.Fatal(state)
	}
}
func TestReset(t *testing.T) {
	s := New()
	a, _ := s.Health(context.Background(), &pb.Empty{})
	b, _ := s.Reset(context.Background(), &pb.Empty{})
	if a.BootId == b.BootId {
		t.Fatal("boot must change")
	}
}
func TestCancelIdempotency(t *testing.T) {
	s := New()
	ctx := context.Background()
	s.PlaceOrder(ctx, &pb.Order{Id: "o", AccountId: "u", Symbol: "AAPL", Side: "BUY", Kind: "LIMIT", Price: 100, Quantity: 2})
	c := &pb.Cancel{CommandId: "c", OrderId: "o", AccountId: "u", Symbol: "AAPL"}
	a, err := s.CancelOrder(ctx, c)
	if err != nil {
		t.Fatal(err)
	}
	b, err := s.CancelOrder(ctx, c)
	if err != nil || b.Remaining != a.Remaining {
		t.Fatal(b, err)
	}
}
