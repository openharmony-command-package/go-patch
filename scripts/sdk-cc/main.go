// SDK compiler wrapper for Go's single-executable CC/CXX probes.
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func main() {
	sdk := os.Getenv("OHOS_NDK_HOME")
	if sdk == "" {
		fmt.Fprintln(os.Stderr, "set OHOS_NDK_HOME to the OpenHarmony native SDK")
		os.Exit(2)
	}
	name := strings.TrimSuffix(filepath.Base(os.Args[0]), ".exe")
	parts := strings.Split(name, "-")
	arch := parts[len(parts)-1]
	triple := map[string]string{"arm64": "aarch64-linux-ohos", "arm": "arm-linux-ohos", "amd64": "x86_64-linux-ohos"}[arch]
	if triple == "" {
		fmt.Fprintln(os.Stderr, "unknown wrapper architecture:", arch)
		os.Exit(2)
	}
	compiler := "clang"
	if strings.HasPrefix(name, "cxx-") {
		compiler = "clang++"
	}
	if runtime.GOOS == "windows" {
		compiler += ".exe"
	}
	args := []string{"--target=" + triple, "--sysroot=" + filepath.Join(sdk, "sysroot")}
	if arch == "arm" {
		args = append(args, "-march=armv7-a", "-mfloat-abi=softfp", "-mfpu=neon-vfpv4")
	}
	c := exec.Command(filepath.Join(sdk, "llvm", "bin", compiler), append(args, os.Args[1:]...)...)
	c.Stdin, c.Stdout, c.Stderr = os.Stdin, os.Stdout, os.Stderr
	if err := c.Run(); err != nil {
		if e, ok := err.(*exec.ExitError); ok {
			os.Exit(e.ExitCode())
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
