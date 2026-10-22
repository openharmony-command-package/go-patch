// Detach a full native test run from HDC's shell session.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
)

func main() {
	root := os.Getenv("GO_OHOS_TEST_ROOT")
	if root == "" {
		root = "/data/local/tmp/go-patch"
	}
	if len(os.Args) < 2 {
		panic("usage: native-runner GOARCH [CGO_ENABLED]")
	}
	f, err := os.OpenFile(filepath.Join(root, "launcher.log"), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		panic(err)
	}
	defer f.Close()
	args := os.Args[1:]
	if len(args) > 3 {
		os.Setenv("GO_OHOS_TEST_SCOPE", args[3])
	}
	if len(args) > 2 {
		os.Setenv("GO_OHOS_TEST_RUN_ID", args[2])
		args = args[:2]
	}
	c := exec.Command("/system/bin/sh", append([]string{filepath.Join(root, "run-native.sh")}, args...)...)
	c.Stdout, c.Stderr = f, f
	c.SysProcAttr = &syscall.SysProcAttr{Setsid: true}
	if err := c.Start(); err != nil {
		panic(err)
	}
	fmt.Println("native test PID", c.Process.Pid)
	c.Process.Release()
}
