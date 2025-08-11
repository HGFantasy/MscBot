package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
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

func main() {
	http.HandleFunc("/fib", fibHandler)
	log.Println("Go service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
