// Native QEMU test compiler: Zig's OHOS Clang frontend plus the SDK's
// unmodified CRT and libraries, linked by LLD. Zig's high-level cc driver
// requires PIE on OHOS, while Go also tests explicit -buildmode=exe.
package main

import (
	"crypto/sha256"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func run(cmd string, args ...string) {
	c := exec.Command(cmd, args...)
	c.Stdin, c.Stdout, c.Stderr = os.Stdin, os.Stdout, os.Stderr
	if err := c.Run(); err != nil {
		if e, ok := err.(*exec.ExitError); ok {
			os.Exit(e.ExitCode())
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func main() {
	root := os.Getenv("GO_NATIVE_CC_ROOT")
	if root == "" {
		root = "/data/local/tmp/go-patch"
	}
	zig := filepath.Join(root, "native-zig/zig")
	for key, dir := range map[string]string{"ZIG_GLOBAL_CACHE_DIR": "zig-global", "ZIG_LOCAL_CACHE_DIR": "zig-cache"} {
		if os.Getenv(key) == "" {
			os.Setenv(key, filepath.Join(root, dir))
		}
	}
	triple := map[string]string{"arm64": "aarch64-linux-ohos", "arm": "arm-linux-ohos", "amd64": "x86_64-linux-ohos"}[runtime.GOARCH]
	interp := map[string]string{"arm64": "aarch64", "arm": "arm", "amd64": "x86_64"}[runtime.GOARCH]
	emulation := map[string]string{"arm64": "aarch64linux", "arm": "armelf_linux_eabi", "amd64": "elf_x86_64"}[runtime.GOARCH]
	stdlib := filepath.Join(root, "sdk/sysroot/usr/lib", triple)
	compilerlib := filepath.Join(root, "sdk/llvm/lib/clang/15.0.4/lib", triple)
	cxxlib := filepath.Join(root, "sdk/llvm/lib", triple)
	cxx := strings.Contains(filepath.Base(os.Args[0]), "cxx")
	driver := "cc"
	if cxx {
		driver = "c++"
	}
	front := []string{driver, "-target", triple, "-nostdinc", "-isystem", filepath.Join(root, "native-zig/lib/include"), "-isystem", filepath.Join(root, "sdk/sysroot/usr/include", triple), "-isystem", filepath.Join(root, "sdk/sysroot/usr/include")}
	// Match a regular Clang C compiler. Zig enables undefined-behavior
	// instrumentation by default, whose runtime the raw LLD invocation does
	// not implicitly link. Explicit sanitizer flags below still take effect.
	front = append(front, "-fno-sanitize=all")
	if runtime.GOARCH == "arm" {
		// Zig's -march parser treats armv7-a as a CPU name. Express the
		// ARMv7 ISA through its documented CPU/feature spelling instead.
		front = append(front, "-mcpu=generic+v7a", "-mfloat-abi=softfp", "-mfpu=neon-vfpv4")
	}
	if cxx {
		front = append(front, "-nostdinc++", "-isystem", filepath.Join(root, "sdk/llvm/include/libcxx-ohos/include/c++/v1"))
	}
	args := expandResponse(os.Args[1:])
	for _, a := range args {
		if a == "--print-prog-name=ar" || a == "-print-prog-name=ar" {
			fmt.Println(filepath.Join(root, "bin/ar"))
			return
		}
	}
	compileOnly := false
	for _, a := range args {
		if a == "-c" || a == "-E" || a == "-S" || a == "-fsyntax-only" || a == "--version" || a == "-###" || strings.HasPrefix(a, "-print-") {
			compileOnly = true
		}
	}
	if compileOnly {
		for _, a := range args {
			if a == "-###" || a == "--version" {
				c := exec.Command(zig, append(front, args...)...)
				out, err := c.CombinedOutput()
				self, _ := os.Executable()
				data, _ := os.ReadFile(self)
				id := fmt.Sprintf("%x", sha256.Sum256(data))[:12]
				for _, line := range strings.Split(strings.TrimRight(string(out), "\n"), "\n") {
					if strings.Contains(line, "clang version ") {
						line += " (ohos-native-cc " + id + ")"
					}
					fmt.Fprintln(os.Stderr, line)
				}
				if err != nil {
					os.Exit(1)
				}
				return
			}
		}
		run(zig, append(front, args...)...)
		return
	}
	shared, pie, static, nostart, nodefault := false, true, false, false, false
	relocatable := false
	out := "a.out"
	var ld, cflags, sources []string
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch {
		case a == "-o":
			i++
			out = args[i]
		case a == "-shared":
			shared = true
			ld = append(ld, a)
		case a == "-r":
			relocatable, nostart, nodefault = true, true, true
			ld = append(ld, a)
		case a == "-pie":
			pie = true
		case a == "-no-pie" || a == "-nopie":
			pie = false
		case a == "-static":
			static = true
			ld = append(ld, a)
		case a == "-nostdlib":
			nostart, nodefault = true, true
		case a == "-nostartfiles":
			nostart = true
		case a == "-nodefaultlibs":
			nodefault = true
		case a == "-rdynamic":
			ld = append(ld, "--export-dynamic")
		case a == "-s":
			ld = append(ld, "-s")
		case a == "-Xlinker":
			i++
			ld = append(ld, args[i])
		case strings.HasPrefix(a, "-Wl,"):
			ld = append(ld, strings.Split(a[4:], ",")...)
		case a == "-L" || a == "-l":
			i++
			ld = append(ld, a, args[i])
		case strings.HasPrefix(a, "-L") || strings.HasPrefix(a, "-l"):
			ld = append(ld, a)
		case a == "-I" || a == "-isystem" || a == "-include" || a == "-x" || a == "-isysroot":
			i++
			cflags = append(cflags, a, args[i])
		case strings.HasSuffix(a, ".c") || strings.HasSuffix(a, ".cc") || strings.HasSuffix(a, ".cpp") || strings.HasSuffix(a, ".cxx") || strings.HasSuffix(a, ".S"):
			sources = append(sources, a)
		case strings.HasSuffix(a, ".o") || strings.HasSuffix(a, ".a") || strings.HasSuffix(a, ".so"):
			ld = append(ld, a)
		case a == "-pthread":
			cflags = append(cflags, a)
		case strings.HasPrefix(a, "-fuse-ld=") || a == "-Qunused-arguments":
		case a == "-v":
		default:
			cflags = append(cflags, a)
		}
	}
	tmp, err := os.MkdirTemp("", "ohos-native-cc-")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(tmp)
	for i, source := range sources {
		obj := filepath.Join(tmp, fmt.Sprintf("%d.o", i))
		command := append(append([]string{}, front...), cflags...)
		command = append(command, "-fPIC", "-c", source, "-o", obj)
		run(zig, command...)
		ld = append(ld, obj)
	}
	command := []string{"ld.lld", "--sysroot=" + filepath.Join(root, "sdk/sysroot"), "-m", emulation, "-z", "now", "-z", "relro", "--hash-style=both", "--eh-frame-hdr", "-o", out}
	command = append(command, "-z", "max-page-size=4096")
	if !shared && !relocatable && pie {
		command = append(command, "-pie")
	}
	if !static && !relocatable {
		command = append(command, "-dynamic-linker", "/lib/ld-musl-"+interp+".so.1")
	}
	if !nostart {
		if !shared {
			crt := "crt1.o"
			if pie {
				crt = "Scrt1.o"
			}
			command = append(command, filepath.Join(stdlib, crt))
		}
		command = append(command, filepath.Join(stdlib, "crti.o"), filepath.Join(compilerlib, "clang_rt.crtbegin.o"))
	}
	command = append(command, "-L"+stdlib, "-L"+compilerlib, "-L"+cxxlib)
	for _, arg := range ld {
		if arg == "-lstdc++" || arg == "-lc++" {
			command = append(command, filepath.Join(cxxlib, "libc++_static.a"), filepath.Join(cxxlib, "libc++abi.a"))
			continue
		}
		command = append(command, arg)
	}
	if cxx {
		command = append(command, filepath.Join(cxxlib, "libc++_static.a"), filepath.Join(cxxlib, "libc++abi.a"))
	}
	if !nodefault {
		command = append(command, filepath.Join(compilerlib, "libclang_rt.builtins.a"), "-l:libunwind.a", "-lc", filepath.Join(compilerlib, "libclang_rt.builtins.a"), "-l:libunwind.a")
	}
	if !nostart {
		command = append(command, filepath.Join(compilerlib, "clang_rt.crtend.o"), filepath.Join(stdlib, "crtn.o"))
	}
	run(zig, command...)
	if !relocatable && os.Getenv("GOOHOS_SIGN_DEFER") != "1" {
		run(filepath.Join(root, "bin/binary-sign-tool"), "sign", "-inFile", out, "-outFile", out, "-selfSign", "1")
	}
}

// Go's response files use whitespace-separated arguments, quoting an entire
// argument with single or double quotes when it contains whitespace.
func expandResponse(args []string) []string {
	var result []string
	for _, arg := range args {
		if !strings.HasPrefix(arg, "@") {
			result = append(result, arg)
			continue
		}
		data, err := os.ReadFile(arg[1:])
		if err != nil {
			panic(err)
		}
		s := strings.TrimSpace(string(data))
		for s != "" {
			if s[0] == '\'' || s[0] == '"' {
				end := strings.IndexByte(s[1:], s[0])
				if end < 0 {
					panic("unterminated response file quote")
				}
				result = append(result, s[1:end+1])
				s = s[end+2:]
			} else {
				end := strings.IndexAny(s, " \r\n\t")
				if end < 0 {
					end = len(s)
				}
				result = append(result, s[:end])
				s = s[end:]
			}
			s = strings.TrimSpace(s)
		}
	}
	return result
}
