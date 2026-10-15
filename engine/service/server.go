package service

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"

	"github.com/Sujendra-23/PaperTrade/engine/book"
	pb "github.com/Sujendra-23/PaperTrade/engine/pb"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/proto"
)

type cached struct {
	request proto.Message
	result  *pb.Result
}
type Server struct {
	pb.UnimplementedMatchingEngineServer
	mu          sync.Mutex
	engine      *book.Engine
	boot        string
	commands    int64
	cache       map[string]cached
	subscribers map[uint64]chan *pb.Trade
	nextSub     uint64
}

func New() *Server { s := &Server{subscribers: map[uint64]chan *pb.Trade{}}; s.reset(); return s }
func (s *Server) reset() {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		panic(err)
	}
	s.boot = hex.EncodeToString(b)
	s.commands = 0
	s.cache = map[string]cached{}
	s.engine = book.New()
}
func (s *Server) Health(context.Context, *pb.Empty) (*pb.EngineState, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return &pb.EngineState{BootId: s.boot, Commands: s.commands}, nil
}
func (s *Server) Reset(context.Context, *pb.Empty) (*pb.EngineState, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.reset()
	return &pb.EngineState{BootId: s.boot}, nil
}
func (s *Server) PlaceOrder(_ context.Context, o *pb.Order) (*pb.Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if c, ok := s.cache[o.Id]; ok {
		if !proto.Equal(c.request, o) {
			return nil, status.Error(codes.AlreadyExists, "id reused with different payload")
		}
		return proto.Clone(c.result).(*pb.Result), nil
	}
	r, err := s.engine.Place(book.Order{ID: o.Id, AccountID: o.AccountId, Symbol: o.Symbol, Side: o.Side, Kind: o.Kind, Price: o.Price, Quantity: o.Quantity})
	if err != nil {
		return nil, status.Error(codes.InvalidArgument, err.Error())
	}
	result := &pb.Result{OrderId: r.OrderID, Status: r.Status, Remaining: r.Remaining}
	for i, t := range r.Trades {
		trade := &pb.Trade{Id: fmt.Sprintf("%s:%d", o.Id, i), Symbol: t.Symbol, Price: t.Price, Quantity: t.Quantity, BuyOrderId: t.BuyOrderID, SellOrderId: t.SellOrderID, BuyerId: t.BuyerID, SellerId: t.SellerID, TimestampMs: time.Now().UnixMilli()}
		result.Trades = append(result.Trades, trade)
		for id, ch := range s.subscribers {
			select {
			case ch <- trade:
			default:
				close(ch)
				delete(s.subscribers, id)
			}
		}
	}
	s.commands++
	s.cache[o.Id] = cached{request: proto.Clone(o), result: proto.Clone(result).(*pb.Result)}
	return result, nil
}
func (s *Server) CancelOrder(_ context.Context, c *pb.Cancel) (*pb.Result, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if c.CommandId == "" {
		return nil, status.Error(codes.InvalidArgument, "command id required")
	}
	if v, ok := s.cache[c.CommandId]; ok {
		if !proto.Equal(v.request, c) {
			return nil, status.Error(codes.AlreadyExists, "id reused")
		}
		return proto.Clone(v.result).(*pb.Result), nil
	}
	r, err := s.engine.Cancel(c.OrderId, c.AccountId, c.Symbol)
	if err != nil {
		return nil, status.Error(codes.NotFound, err.Error())
	}
	result := &pb.Result{OrderId: r.OrderID, Status: r.Status, Remaining: r.Remaining}
	s.commands++
	s.cache[c.CommandId] = cached{request: proto.Clone(c), result: proto.Clone(result).(*pb.Result)}
	return result, nil
}
func (s *Server) GetBook(_ context.Context, sym *pb.Symbol) (*pb.Snapshot, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	snap := s.engine.Snapshot(sym.Symbol, 20)
	r := &pb.Snapshot{Symbol: sym.Symbol}
	for _, l := range snap.Bids {
		r.Bids = append(r.Bids, &pb.Level{Price: l.Price, Quantity: l.Quantity, Orders: l.Orders})
	}
	for _, l := range snap.Asks {
		r.Asks = append(r.Asks, &pb.Level{Price: l.Price, Quantity: l.Quantity, Orders: l.Orders})
	}
	return r, nil
}
func (s *Server) StreamTrades(sym *pb.Symbol, stream pb.MatchingEngine_StreamTradesServer) error {
	s.mu.Lock()
	s.nextSub++
	id := s.nextSub
	ch := make(chan *pb.Trade, 256)
	s.subscribers[id] = ch
	s.mu.Unlock()
	defer func() { s.mu.Lock(); delete(s.subscribers, id); s.mu.Unlock() }()
	for {
		select {
		case <-stream.Context().Done():
			return stream.Context().Err()
		case t, ok := <-ch:
			if !ok {
				return status.Error(codes.ResourceExhausted, "slow subscriber; resync via API")
			}
			if sym.Symbol == "" || sym.Symbol == t.Symbol {
				if err := stream.Send(t); err != nil {
					return err
				}
			}
		}
	}
}
