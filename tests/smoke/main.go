package main

import (
	"crypto/sha256"
	"fmt"
	"net"
	"os"
	"runtime"
	"sync"
	"time"
)

func main() {
	if !runtime.IsOpenharmony {
		panic("wrong runtime platform")
	}
	var wg sync.WaitGroup
	for i := 0; i < 64; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 10000; j++ {
				_ = sha256.Sum256([]byte("ohos"))
			}
			runtime.GC()
		}()
	}
	wg.Wait()
	f, err := os.CreateTemp("", "go-ohos-")
	if err != nil {
		panic(err)
	}
	defer os.Remove(f.Name())
	if _, err := f.WriteString("OHOS"); err != nil {
		panic(err)
	}
	f.Close()
	interfaces, err := net.Interfaces()
	if err != nil || len(interfaces) == 0 {
		panic("interfaces unavailable")
	}
	for _, ifi := range interfaces {
		if _, err := ifi.Addrs(); err != nil {
			panic(err)
		}
	}
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic(err)
	}
	go func() {
		c, err := l.Accept()
		if err != nil {
			panic(err)
		}
		c.Write([]byte("ok"))
		c.Close()
	}()
	c, err := net.DialTimeout("tcp", l.Addr().String(), 3*time.Second)
	if err != nil {
		panic(err)
	}
	var b [2]byte
	if _, err := c.Read(b[:]); err != nil || string(b[:]) != "ok" {
		panic("TCP roundtrip")
	}
	c.Close()
	l.Close()
	z, err := time.LoadLocation("Asia/Shanghai")
	if err != nil {
		panic(err)
	}
	_, offset := time.Unix(0, 0).In(z).Zone()
	if offset != 8*3600 {
		panic("timezone")
	}
	fmt.Println("GO_OHOS_SMOKE_OK", runtime.GOARCH)
}
