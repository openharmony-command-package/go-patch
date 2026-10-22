package main

import (
	"crypto/x509"
	"fmt"
	"io"
	"log"
	"log/hilog"
	"log/slog"
	"net"
	"os"
	"os/openharmony"
	"os/user"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"time"
)

func must(err error) {
	if err != nil {
		panic(err)
	}
}

func main() {
	if !runtime.IsOpenharmony {
		panic("wrong platform")
	}
	mode := "system"
	if len(os.Args) > 1 {
		mode = os.Args[1]
	}
	switch mode {
	case "panic":
		panic(("GO_OHOS_HILOG_PANIC " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
	case "stdio-closed":
		syscall.Close(1)
		syscall.Close(2)
		for i := 0; i < 2; i++ {
			n, e := fmt.Fprintln(os.Stdout, "GO_OHOS_CLOSED_STDOUT", os.Getenv("GO_OHOS_PLATFORM_RUN"))
			if n != 0 || e == nil {
				panic("logger reused stdout descriptor")
			}
		}
		for i := 0; i < 2; i++ {
			n, e := fmt.Fprintln(os.Stderr, "GO_OHOS_CLOSED_STDERR", os.Getenv("GO_OHOS_PLATFORM_RUN"))
			if n != 0 || e == nil {
				panic("logger reused stderr descriptor")
			}
		}
		println("GO_OHOS_CLOSED_RUNTIME " + os.Getenv("GO_OHOS_PLATFORM_RUN"))
	case "quiet":
		fmt.Println("GO_OHOS_HILOG_DISABLED", os.Getenv("GO_OHOS_PLATFORM_RUN"))
	case "copy":
		f, err := os.CreateTemp("", "go-ohos-copy-")
		must(err)
		defer os.Remove(f.Name())
		defer f.Close()
		text := "GO_OHOS_COPY_WRITETO " + os.Getenv("GO_OHOS_PLATFORM_RUN") + "\n"
		_, err = f.WriteString(text)
		must(err)
		_, err = f.Seek(0, 0)
		must(err)
		_, err = io.Copy(os.Stdout, f)
		must(err)
		text = "GO_OHOS_COPY_READFROM " + os.Getenv("GO_OHOS_PLATFORM_RUN") + "\n"
		must(f.Truncate(0))
		_, err = f.Seek(0, 0)
		must(err)
		_, err = f.WriteString(text)
		must(err)
		_, err = f.Seek(0, 0)
		must(err)
		_, err = os.Stderr.ReadFrom(io.LimitReader(f, int64(len(text))))
		must(err)
	case "long":
		_, err := (hilog.Writer{Domain: 0x1234, Tag: "GoPort", Level: hilog.Info}).Write([]byte(("GO_OHOS_LONG_START " + os.Getenv("GO_OHOS_PLATFORM_RUN")) + strings.Repeat("x", 8200) + ("GO_OHOS_LONG_END " + os.Getenv("GO_OHOS_PLATFORM_RUN"))))
		must(err)
		fmt.Println("GO_OHOS_LONG_OK")
	case "system":
		fmt.Println("GO_OHOS_PLATFORM_PID", os.Getpid(), os.Getenv("GO_OHOS_PLATFORM_RUN"))
		pool, err := x509.SystemCertPool()
		must(err)
		if len(pool.Subjects()) == 0 {
			panic("no system trust anchors")
		}
		fmt.Println("GO_OHOS_SYSTEM_CA_OK", len(pool.Subjects()))
		name, offset := time.Now().Zone()
		if len(os.Args) > 2 && name != os.Args[2] {
			panic("unexpected default timezone: " + name)
		}
		fmt.Println("GO_OHOS_LOCAL_ZONE_OK", name, offset)
		log.Println(("GO_OHOS_HILOG_LOG " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
		slog.Info(("GO_OHOS_HILOG_SLOG " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
		fmt.Println(("GO_OHOS_HILOG_STDOUT " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
		println(("GO_OHOS_HILOG_RUNTIME " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
		_, err = (hilog.Writer{Domain: 0x1234, Tag: "GoPort", Level: hilog.Warn}).Write([]byte(("GO_OHOS_HILOG_WRITER " + os.Getenv("GO_OHOS_PLATFORM_RUN"))))
		must(err)
		slog.New(hilog.NewHandler(0x1234, "GoPort", nil)).With("test", "attribute").Warn(("GO_OHOS_HILOG_HANDLER " + os.Getenv("GO_OHOS_PLATFORM_RUN")))
	case "context":
		root, err := os.MkdirTemp("", "go-ohos-context-")
		must(err)
		defer os.RemoveAll(root)
		c := openharmony.Config{FilesDir: root, CacheDir: root, TempDir: root, Timezone: "Asia/Shanghai"}
		old := os.Getenv("HOME")
		bad := c
		bad.TempDir = "relative"
		if openharmony.Configure(bad) == nil || os.Getenv("HOME") != old {
			panic("invalid Context changed environment")
		}
		must(openharmony.Configure(c))
		home, err := os.UserHomeDir()
		must(err)
		cache, err := os.UserCacheDir()
		must(err)
		if home != root || cache != root || os.TempDir() != root {
			panic("Context directories not used")
		}
		f, err := os.CreateTemp("", "context-")
		must(err)
		f.Close()
		if filepath.Dir(f.Name()) != root {
			panic("wrong temporary directory")
		}
		_, offset := time.Now().Zone()
		if offset != 8*3600 {
			panic("Context timezone not used")
		}
		u, err := user.Current()
		must(err)
		if u.Uid == "" {
			panic("missing UID")
		}
		fmt.Println("GO_OHOS_CONTEXT_OK", u.Uid)
	case "network":
		l, err := net.Listen("tcp", "127.0.0.1:0")
		must(err)
		defer l.Close()
		go func() { c, err := l.Accept(); must(err); c.Write([]byte("ok")); c.Close() }()
		c, err := net.DialTimeout("tcp", l.Addr().String(), 3*time.Second)
		must(err)
		var b [2]byte
		_, err = c.Read(b[:])
		must(err)
		c.Close()
		if string(b[:]) != "ok" {
			panic("TCP")
		}
		fmt.Println("GO_OHOS_SOCKET_OK")
	case "hook-denied":
		_, err := net.Listen("tcp", "127.0.0.1:0")
		if err == nil || !strings.Contains(err.Error(), "operation not permitted") {
			panic(fmt.Sprint("socket hook ignored: ", err))
		}
		fmt.Println("GO_OHOS_SOCKET_HOOK_OK")
	default:
		panic("unknown mode")
	}
}
