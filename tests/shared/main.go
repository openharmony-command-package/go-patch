package main

/*
#include <stdint.h>
static int64_t twice(int64_t x) { return x * 2; }
*/
import "C"

import (
	"os"
	"runtime"
)

//export GoAnswer
func GoAnswer(x C.int64_t) C.int64_t {
	runtime.GC()
	return C.twice(x) + 1
}

//export GoEnvironmentLength
func GoEnvironmentLength() C.int { return C.int(len(os.Getenv("GO_OHOS_LONG_ENV"))) }

func main() {}
