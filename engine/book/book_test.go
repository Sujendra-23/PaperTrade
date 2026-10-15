package book

import (
	"fmt"
	"sync"
	"testing"
)

func order(id, side string, p, q int64) Order {
	return Order{ID: id, AccountID: id, Symbol: "AAPL", Side: side, Kind: "LIMIT", Price: p, Quantity: q}
}
func TestMatching(t *testing.T) {
	tests := []struct {
		name               string
		makers             []Order
		taker              Order
		prices, quantities []int64
		status             string
		remaining          int64
	}{
		{"best ask first", []Order{order("s1", "SELL", 102, 4), order("s2", "SELL", 101, 3)}, order("b", "BUY", 102, 5), []int64{101, 102}, []int64{3, 2}, "FILLED", 0},
		{"best bid first", []Order{order("b1", "BUY", 99, 2), order("b2", "BUY", 100, 3)}, order("s", "SELL", 99, 4), []int64{100, 99}, []int64{3, 1}, "FILLED", 0},
		{"fifo", []Order{order("first", "SELL", 100, 2), order("second", "SELL", 100, 3)}, order("b", "BUY", 100, 4), []int64{100, 100}, []int64{2, 2}, "FILLED", 0},
		{"partial rests", []Order{order("s", "SELL", 100, 2)}, order("b", "BUY", 100, 5), []int64{100}, []int64{2}, "PARTIAL", 3},
		{"uncrossed", []Order{order("s", "SELL", 101, 2)}, order("b", "BUY", 100, 5), nil, nil, "OPEN", 5},
		{"market ioc", []Order{order("s", "SELL", 100, 2)}, Order{ID: "b", AccountID: "buyer", Symbol: "AAPL", Side: "BUY", Kind: "MARKET", Price: 105, Quantity: 5}, []int64{100}, []int64{2}, "CANCELLED", 3},
		{"market collar", []Order{order("s", "SELL", 106, 2)}, Order{ID: "b", AccountID: "buyer", Symbol: "AAPL", Side: "BUY", Kind: "MARKET", Price: 105, Quantity: 2}, nil, nil, "CANCELLED", 2},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			e := New()
			for _, o := range tt.makers {
				if _, err := e.Place(o); err != nil {
					t.Fatal(err)
				}
			}
			r, err := e.Place(tt.taker)
			if err != nil {
				t.Fatal(err)
			}
			if r.Status != tt.status || r.Remaining != tt.remaining || len(r.Trades) != len(tt.prices) {
				t.Fatalf("got %+v", r)
			}
			for i, tr := range r.Trades {
				if tr.Price != tt.prices[i] || tr.Quantity != tt.quantities[i] {
					t.Fatalf("bad trade %+v", tr)
				}
			}
			if tt.name == "fifo" && r.Trades[0].SellOrderID != "first" {
				t.Fatal("lost time priority")
			}
		})
	}
}
func TestCancel(t *testing.T) {
	e := New()
	e.Place(order("a", "BUY", 100, 5))
	if _, err := e.Cancel("a", "wrong", "AAPL"); err != ErrNotFound {
		t.Fatal(err)
	}
	r, err := e.Cancel("a", "a", "AAPL")
	if err != nil || r.Remaining != 5 {
		t.Fatal(r, err)
	}
	if len(e.Snapshot("AAPL", 10).Bids) != 0 {
		t.Fatal("cancel still visible")
	}
	if _, err = e.Cancel("a", "a", "AAPL"); err != ErrNotFound {
		t.Fatal(err)
	}
}
func TestDuplicate(t *testing.T) {
	e := New()
	o := order("a", "BUY", 100, 1)
	e.Place(o)
	if _, err := e.Place(o); err != ErrDuplicate {
		t.Fatal(err)
	}
}
func TestInvalid(t *testing.T) {
	for _, o := range []Order{order("a", "BUY", 0, 1), order("a", "BUY", 100, -1), order("a", "BAD", 100, 1), order("a", "BUY", MaxPrice+1, 1), order("a", "BUY", 1, MaxQuantity+1)} {
		if _, err := New().Place(o); err != ErrInvalid {
			t.Fatal(o, err)
		}
	}
}
func TestSymbolIsolation(t *testing.T) {
	e := New()
	e.Place(order("s", "SELL", 100, 1))
	o := order("b", "BUY", 100, 1)
	o.Symbol = "MSFT"
	r, _ := e.Place(o)
	if len(r.Trades) != 0 {
		t.Fatal("cross symbol match")
	}
}
func TestSelfTradePrevention(t *testing.T) {
	e := New()
	o := order("s", "SELL", 100, 1)
	o.AccountID = "same"
	e.Place(o)
	o = order("b", "BUY", 100, 1)
	o.AccountID = "same"
	r, _ := e.Place(o)
	if r.Status != "CANCELLED" || len(r.Trades) != 0 {
		t.Fatal(r)
	}
}
func TestConcurrent(t *testing.T) {
	e := New()
	var wg sync.WaitGroup
	for i := range 1000 {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			side := "BUY"
			if i%2 == 0 {
				side = "SELL"
			}
			_, err := e.Place(order(fmt.Sprint(i), side, 100, 1))
			if err != nil {
				t.Error(err)
			}
			e.Snapshot("AAPL", 10)
		}(i)
	}
	wg.Wait()
	s := e.Snapshot("AAPL", 10)
	if len(s.Bids)+len(s.Asks) != 0 {
		t.Fatalf("unmatched balanced flow: %+v", s)
	}
}
func TestCancelPartial(t *testing.T) {
	e := New()
	e.Place(order("s", "SELL", 100, 5))
	e.Place(order("b", "BUY", 100, 2))
	r, err := e.Cancel("s", "s", "AAPL")
	if err != nil || r.Remaining != 3 {
		t.Fatal(r, err)
	}
}
