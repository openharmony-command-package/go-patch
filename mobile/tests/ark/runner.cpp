// Copyright 2026. Test harness for the pinned OHOS QEMU image.
// Inner runtime entry points are used only here, not in generated bindings.
#include <functional>
#include <memory>
#include <napi/native_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <unistd.h>
#include "runtime.h"

int main(int argc, char **argv) {
  if (argc != 3) return 2;
  void *runtime = dlopen("libruntime.z.so", RTLD_NOW | RTLD_GLOBAL);
  if (!runtime) { fprintf(stderr, "RUNTIME_LIBRARY %s\n", dlerror()); return 3; }
  using Configure = void (*)(const OHOS::AbilityRuntime::Runtime::Options &);
  auto configure = reinterpret_cast<Configure>(dlsym(runtime,
      "_ZN4OHOS14AbilityRuntime13JsRuntimeLite17InitJsRuntimeLiteERKNS0_7Runtime7OptionsE"));
  if (!configure) { fprintf(stderr, "CONFIGURE_SYMBOL %s\n", dlerror()); return 4; }
  OHOS::AbilityRuntime::Runtime::Options options;
  options.bundleName = "org.openharmony.gomobiletest";
  options.loadAce = false;
  options.isBundle = true;
  options.isStageModel = false;
  options.isDebugVersion = false;
  options.arkTSMode = "dynamic";
  options.apiTargetVersion = 26;
  configure(options);
  void *lib = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
  if (!lib) { fprintf(stderr, "BINDING_LIBRARY %s\n", dlerror()); return 6; }
  auto init = reinterpret_cast<napi_value (*)(napi_env, napi_value)>(
      dlsym(lib, "gomobileOHOSInit"));
  auto run = reinterpret_cast<bool (*)(void *, const char *, bool)>(
      dlsym(RTLD_DEFAULT, "_ZN15ArkNativeEngine13RunScriptPathEPKcb"));
  if (!init || !run) { fprintf(stderr, "ENTRY_SYMBOL %s\n", dlerror()); return 7; }
  for (int round = 1; round <= 2; round++) {
    napi_env env = nullptr;
    if (napi_create_ark_runtime(&env) != napi_ok || !env) return 5;
    napi_handle_scope scope;
    if (napi_open_handle_scope(env, &scope) != napi_ok) return 8;
    napi_value exports, global, roundValue;
    napi_create_object(env, &exports);
    if (!init(env, exports)) return 8;
    napi_get_global(env, &global);
    napi_set_named_property(env, global, "native", exports);
    napi_create_int32(env, round, &roundValue);
    napi_set_named_property(env, global, "GOMOBILE_TEST_ROUND", roundValue);
    if (!run(env, argv[2], true)) return 9;
    bool passed = false;
    char errorText[4096] = {};
    for (unsigned i = 0; i < 30000; i++) {
      if (napi_run_event_loop(env, napi_event_mode_nowait) != napi_ok) break;
      napi_value ok, error;
      napi_get_named_property(env, global, "GO_OHOS_TEST_OK", &ok);
      napi_get_value_bool(env, ok, &passed);
      size_t len = 0;
      napi_get_named_property(env, global, "GO_OHOS_TEST_ERROR", &error);
      napi_get_value_string_utf8(env, error, errorText, sizeof(errorText), &len);
      if (passed || len) break;
      usleep(10000);
    }
    if (passed) {
      napi_value report;
      char reportText[16384] = {};
      size_t len = 0;
      napi_get_named_property(env, global, "GO_OHOS_TEST_REPORT", &report);
      if (napi_get_value_string_utf8(env, report, reportText, sizeof(reportText), &len) != napi_ok || !len)
        return 11;
      printf("GOMOBILE_ARK_REPORT %s\n", reportText);
      fflush(stdout);
    } else fprintf(stderr, "ARK_FAILED round=%d %s\n", round, errorText);
    napi_close_handle_scope(env, scope);
    if (napi_destroy_ark_runtime(&env) != napi_ok) return 12;
    if (!passed) return 10;
  }
  return 0;
}
