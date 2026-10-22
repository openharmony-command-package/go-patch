package hello

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// Listener tests callbacks from arbitrary Go goroutines.
type Listener interface {
	OnMessage(message string) (string, error)
}
type Counter struct {
	Value int
	Label string
	mu    sync.Mutex
}

func (c *Counter) Add(n int) int    { c.mu.Lock(); defer c.mu.Unlock(); c.Value += n; return c.Value }
func NewCounter(value int) *Counter { return &Counter{Value: value, Label: "OHOS"} }
func Hello(name string) string      { fmt.Println("GOMOBILE_OHOS_HELLO", name); return "Hello, " + name }
func EchoBytes(b []byte) []byte     { return append([]byte(nil), b...) }
func EchoInt64(n int64) int64       { return n }
func Divide(a, b float64) (float64, error) {
	if b == 0 {
		return 0, errors.New("division by zero")
	}
	return a / b, nil
}
func Invoke(l Listener, s string) (string, error) {
	if l == nil {
		return "", errors.New("nil listener")
	}
	return l.OnMessage(s)
}
func InvokeLater(l Listener, s string) (string, error) {
	ch := make(chan struct {
		v string
		e error
	}, 1)
	go func() {
		time.Sleep(time.Millisecond)
		v, e := l.OnMessage(s)
		ch <- struct {
			v string
			e error
		}{v, e}
	}()
	r := <-ch
	return r.v, r.e
}
func NewListener() Listener { return &prefixListener{} }

type prefixListener struct{}

func (*prefixListener) OnMessage(s string) (string, error) { return "Go: " + s, nil }

var Greeting = "Hello"

const Version = "1.0"

var savedMu sync.Mutex
var saved Listener

func SaveListener(l Listener) { savedMu.Lock(); saved = l; savedMu.Unlock() }
func FireSaved(s string) (string, error) {
	savedMu.Lock()
	l := saved
	savedMu.Unlock()
	if l == nil {
		return "", errors.New("no listener")
	}
	return l.OnMessage(s)
}
func PanicNow()             { panic("fixture panic") }
func ByteValue(b byte) byte { return b }

// DirectoryState lets the device test observe the Context received by Go.
func DirectoryState() string {
	cache, _ := os.UserCacheDir()
	return os.Getenv("HOME") + "\n" + cache + "\n" + os.TempDir()
}

func WritePrivateFile(name, text string) error {
	if name == "." || name == "" || filepath.Base(name) != name {
		return errors.New("expected a file name")
	}
	return os.WriteFile(filepath.Join(os.Getenv("HOME"), name), []byte(text), 0600)
}

type ListenerFactory interface{ Create() (Listener, error) }

func InvokeFactory(f ListenerFactory, s string) (string, error) {
	l, e := f.Create()
	if e != nil {
		return "", e
	}
	return l.OnMessage(s)
}

type ObjectListener interface {
	Update(c *Counter, data []byte, n int64) (*Counter, error)
}

func InvokeObject(l ObjectListener) (*Counter, error) {
	return l.Update(NewCounter(10), []byte{0, 128, 255}, 9223372036854775807)
}

func EchoFloat(n float64) float64   { return n }
func EchoFloat32(n float32) float32 { return n }

type Clock interface {
	Delay(d time.Duration) (time.Duration, error)
}

func ClockDelay(c Clock, n int64) (int64, error) {
	r, e := c.Delay(time.Duration(n))
	return int64(r), e
}
