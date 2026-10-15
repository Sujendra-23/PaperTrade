// Package book implements a deterministic, integer-price, price-time order book.
package book

import (
	"container/heap"
	"container/list"
	"errors"
	"sort"
	"sync"
)

var ErrInvalid = errors.New("invalid order")
var ErrDuplicate = errors.New("duplicate order id")
var ErrNotFound = errors.New("open order not found for account")

const MaxPrice int64 = 1_000_000_000
const MaxQuantity int64 = 1_000_000

type Order struct {
	ID, AccountID, Symbol, Side, Kind string
	Price, Quantity                   int64
}
type Trade struct {
	BuyOrderID, SellOrderID, BuyerID, SellerID, Symbol string
	Price, Quantity                                    int64
}
type Result struct {
	OrderID, Status string
	Remaining       int64
	Trades          []Trade
}
type Level struct{ Price, Quantity, Orders int64 }
type Snapshot struct{ Bids, Asks []Level }
type resting struct {
	order     Order
	remaining int64
	element   *list.Element
}
type priceHeap struct {
	prices []int64
	buy    bool
}

func (h priceHeap) Len() int { return len(h.prices) }
func (h priceHeap) Less(i, j int) bool {
	if h.buy {
		return h.prices[i] > h.prices[j]
	}
	return h.prices[i] < h.prices[j]
}
func (h priceHeap) Swap(i, j int) { h.prices[i], h.prices[j] = h.prices[j], h.prices[i] }
func (h *priceHeap) Push(v any)   { h.prices = append(h.prices, v.(int64)) }
func (h *priceHeap) Pop() any {
	n := len(h.prices)
	v := h.prices[n-1]
	h.prices = h.prices[:n-1]
	return v
}

type side struct {
	levels map[int64]*list.List
	prices priceHeap
}

func newSide(buy bool) side { return side{levels: map[int64]*list.List{}, prices: priceHeap{buy: buy}} }
func (s *side) best() *resting {
	for s.prices.Len() > 0 {
		p := s.prices.prices[0]
		q := s.levels[p]
		if q == nil || q.Len() == 0 {
			heap.Pop(&s.prices)
			delete(s.levels, p)
			continue
		}
		return q.Front().Value.(*resting)
	}
	return nil
}
func (s *side) add(r *resting) {
	q := s.levels[r.order.Price]
	if q == nil {
		q = list.New()
		s.levels[r.order.Price] = q
		heap.Push(&s.prices, r.order.Price)
	}
	r.element = q.PushBack(r)
}
func (s *side) remove(r *resting) { s.levels[r.order.Price].Remove(r.element) }

type symbolBook struct{ bids, asks side }
type Engine struct {
	mu    sync.Mutex
	books map[string]*symbolBook
	open  map[string]*resting
	seen  map[string]bool
}

func New() *Engine {
	return &Engine{books: map[string]*symbolBook{}, open: map[string]*resting{}, seen: map[string]bool{}}
}
func Valid(o Order) bool {
	return o.ID != "" && o.AccountID != "" && o.Symbol != "" && (o.Side == "BUY" || o.Side == "SELL") && (o.Kind == "LIMIT" || o.Kind == "MARKET") && o.Price > 0 && o.Price <= MaxPrice && o.Quantity > 0 && o.Quantity <= MaxQuantity
}
func (e *Engine) Place(o Order) (Result, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	if !Valid(o) {
		return Result{}, ErrInvalid
	}
	if e.seen[o.ID] {
		return Result{}, ErrDuplicate
	}
	e.seen[o.ID] = true
	b := e.books[o.Symbol]
	if b == nil {
		b = &symbolBook{bids: newSide(true), asks: newSide(false)}
		e.books[o.Symbol] = b
	}
	own, opp := &b.bids, &b.asks
	if o.Side == "SELL" {
		own, opp = opp, own
	}
	result := Result{OrderID: o.ID, Remaining: o.Quantity, Status: "OPEN"}
	selfBlocked := false
	for result.Remaining > 0 {
		maker := opp.best()
		if maker == nil {
			break
		}
		p := maker.order.Price
		// A market order is IOC with a protection price supplied by risk checks.
		if (o.Side == "BUY" && p > o.Price) || (o.Side == "SELL" && p < o.Price) {
			break
		}
		// Cancel the taker remainder rather than manufacture self trades.
		if maker.order.AccountID == o.AccountID {
			selfBlocked = true
			break
		}
		qty := min(result.Remaining, maker.remaining)
		t := Trade{Symbol: o.Symbol, Price: p, Quantity: qty}
		if o.Side == "BUY" {
			t.BuyOrderID = o.ID
			t.BuyerID = o.AccountID
			t.SellOrderID = maker.order.ID
			t.SellerID = maker.order.AccountID
		} else {
			t.SellOrderID = o.ID
			t.SellerID = o.AccountID
			t.BuyOrderID = maker.order.ID
			t.BuyerID = maker.order.AccountID
		}
		result.Trades = append(result.Trades, t)
		result.Remaining -= qty
		maker.remaining -= qty
		if maker.remaining == 0 {
			opp.remove(maker)
			delete(e.open, maker.order.ID)
		}
	}
	if result.Remaining == 0 {
		result.Status = "FILLED"
	} else if o.Kind == "MARKET" || selfBlocked {
		result.Status = "CANCELLED"
	} else {
		r := &resting{order: o, remaining: result.Remaining}
		own.add(r)
		e.open[o.ID] = r
		if result.Remaining < o.Quantity {
			result.Status = "PARTIAL"
		}
	}
	return result, nil
}
func (e *Engine) Cancel(id, account, symbol string) (Result, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	r := e.open[id]
	if r == nil || r.order.AccountID != account || r.order.Symbol != symbol {
		return Result{}, ErrNotFound
	}
	b := e.books[symbol]
	s := &b.bids
	if r.order.Side == "SELL" {
		s = &b.asks
	}
	s.remove(r)
	delete(e.open, id)
	return Result{OrderID: id, Status: "CANCELLED", Remaining: r.remaining}, nil
}
func levels(s *side, depth int) []Level {
	rows := make([]Level, 0, len(s.levels))
	for p, q := range s.levels {
		if q.Len() == 0 {
			continue
		}
		l := Level{Price: p, Orders: int64(q.Len())}
		for it := q.Front(); it != nil; it = it.Next() {
			l.Quantity += it.Value.(*resting).remaining
		}
		rows = append(rows, l)
	}
	sort.Slice(rows, func(i, j int) bool {
		if s.prices.buy {
			return rows[i].Price > rows[j].Price
		}
		return rows[i].Price < rows[j].Price
	})
	if len(rows) > depth {
		rows = rows[:depth]
	}
	return rows
}
func (e *Engine) Snapshot(symbol string, depth int) Snapshot {
	e.mu.Lock()
	defer e.mu.Unlock()
	b := e.books[symbol]
	if b == nil {
		return Snapshot{Bids: []Level{}, Asks: []Level{}}
	}
	return Snapshot{Bids: levels(&b.bids, depth), Asks: levels(&b.asks, depth)}
}
