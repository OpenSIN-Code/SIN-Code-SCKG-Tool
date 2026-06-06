package main

import "fmt"

// Server is a simple HTTP server.
type Server struct {
	port int
}

// helper prints a greeting.
func helper() {
	fmt.Println("hello")
}

// Start starts the server.
func (s *Server) Start() {
	helper()
}

func main() {
	s := &Server{port: 8080}
	s.Start()
	helper()
}
