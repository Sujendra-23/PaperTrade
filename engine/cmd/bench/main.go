// Benchmark the in-process book, without network, database, simulator or race instrumentation.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"github.com/Sujendra-23/PaperTrade/engine/book"
	"math/rand"
	"os"
	"runtime"
	"sort"
	"strconv"
	"time"
)

func main() {
	n := flag.Int("n", 1_000_000, "number of orders")
	flag.Parse()
	if *n < 100 {
		panic("n must be >=100")
	}
	rng := rand.New(rand.NewSource(2026))
	orders := make([]book.Order, *n)
	for i := range orders {
		side, account := "BUY", "buyer"
		if rng.Intn(2) == 0 {
			side, account = "SELL", "seller"
		}
		orders[i] = book.Order{ID: strconv.Itoa(i), AccountID: account, Symbol: "BENCH", Side: side, Kind: "LIMIT", Price: 10000 + int64(rng.Intn(101)-50), Quantity: int64(1 + rng.Intn(20))}
	}
	e := book.New()
	lat := make([]int64, *n)
	runtime.GC()
	start := time.Now()
	fills := 0
	for i, o := range orders {
		t := time.Now()
		r, err := e.Place(o)
		lat[i] = time.Since(t).Nanoseconds()
		if err != nil {
			panic(err)
		}
		fills += len(r.Trades)
	}
	elapsed := time.Since(start)
	sort.Slice(lat, func(i, j int) bool { return lat[i] < lat[j] })
	out := map[string]any{"orders": *n, "seed": 2026, "trades": fills, "elapsed_seconds": elapsed.Seconds(), "orders_per_second": float64(*n) / elapsed.Seconds(), "p50_microseconds": float64(lat[(*n-1)*50/100]) / 1000, "p99_microseconds": float64(lat[(*n-1)*99/100]) / 1000, "go_version": runtime.Version(), "os": runtime.GOOS, "arch": runtime.GOARCH, "logical_cpus": runtime.NumCPU(), "gomaxprocs": runtime.GOMAXPROCS(0), "measured_at": time.Now().UTC().Format(time.RFC3339), "scope": "single-threaded in-process Engine.Place wall-clock; includes locks, allocation and per-order timing; pre-generated inputs; excludes RPC, ledger, Redis and UI"}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(out); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
