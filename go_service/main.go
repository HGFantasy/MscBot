package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

// fib computes the nth Fibonacci number iteratively.
func fib(n int) int {
	if n <= 1 {
		return n
	}
	a, b := 0, 1
	for i := 2; i <= n; i++ {
		a, b = b, a+b
	}
	return b
}

func fibHandler(w http.ResponseWriter, r *http.Request) {
	nStr := r.URL.Query().Get("n")
	n, err := strconv.Atoi(nStr)
	if err != nil {
		http.Error(w, "invalid n", http.StatusBadRequest)
		return
	}
	result := fib(n)
	resp := map[string]int{"result": result}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// priorityScore assigns points based on mission title keywords.
func priorityScore(name string) int {
	n := strings.ToLower(name)
	keywords := map[string]int{
		"major":      8,
		"mass":       8,
		"large":      6,
		"multiple":   5,
		"high-rise":  5,
		"industrial": 4,
		"chemical":   4,
		"airport":    4,
		"brush":      3,
		"wildfire":   5,
	}
	score := 0
	for kw, pts := range keywords {
		if strings.Contains(n, kw) {
			score += pts
		}
	}
	return score
}

func scoreHandler(w http.ResponseWriter, r *http.Request) {
	name := r.URL.Query().Get("name")
	score := priorityScore(name)
	resp := map[string]int{"score": score}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func main() {
	http.HandleFunc("/fib", fibHandler)
	http.HandleFunc("/score", scoreHandler)
	log.Println("Go service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
