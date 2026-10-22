#!/usr/bin/env python3
"""Build the real OHOS self-signing helper from pinned hapsigner sources.

The target libcrypto is extracted from the same guest image, not a host library.
Third-party sources are inputs; the script only writes inside --work.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--arch', choices=['arm64', 'arm', 'amd64'], required=True)
p.add_argument('--sdk', type=Path, required=True)
p.add_argument('--hapsigner', type=Path, required=True)
p.add_argument('--third-party', type=Path, required=True)
p.add_argument('--libcrypto', type=Path, required=True)
p.add_argument('--work', type=Path, required=True)
a = p.parse_args()
a.sdk, a.hapsigner, a.third_party, a.libcrypto, a.work = [x.resolve() for x in
    [a.sdk, a.hapsigner, a.third_party, a.libcrypto, a.work]]
a.work.mkdir(parents=True, exist_ok=True)
triple = {'arm64': 'aarch64-linux-ohos', 'arm': 'arm-linux-ohos', 'amd64': 'x86_64-linux-ohos'}[a.arch]
openssl = a.work / 'openssl'
env = dict(os.environ, LC_ALL='C', LC_CTYPE='C', LANG='C')
if not (openssl / 'include/openssl/configuration.h').exists():
    shutil.copytree(a.third_party / 'openssl', openssl, dirs_exist_ok=True)
    target = {'arm64': 'linux-aarch64', 'arm': 'linux-armv4', 'amd64': 'linux-x86_64'}[a.arch]
    subprocess.run(['perl', 'Configure', target, 'no-shared', 'no-tests'], cwd=openssl, env=env, check=True)
    subprocess.run(['make', 'build_generated'], cwd=openssl, env=env, check=True)
base = a.hapsigner / 'binary_sign_tool'
variables = {}
for key, value in re.findall(r'^(\w+)\s*=\s*"([^"]+)"', (base / 'signature_tools.gni').read_text(), re.M):
    for k, v in variables.items():
        value = value.replace('${' + k + '}', v)
    value = value.replace('//developtools/hapsigner', str(a.hapsigner))
    variables[key] = value
sources, includes = [], []
for gni in sorted(base.rglob('*.gni')):
    for name, body in re.findall(r'(\w+)\s*=\s*\[(.*?)\]', gni.read_text(), re.S):
        destination = sources if name.endswith('_src') else includes if name.endswith('_include') else None
        if destination is None:
            continue
        for value in re.findall(r'"([^"]+)"', body):
            for k, v in variables.items():
                value = value.replace('${' + k + '}', v)
            if '${' in value:
                raise SystemExit('unresolved GN variable: ' + value)
            destination.append(Path(value))
sources += [base / 'main.cpp', base / 'api/src/sign_tool_service_impl.cpp', a.third_party / 'cJSON/cJSON.c']
sources += sorted((a.third_party / 'bounds_checking_function/src').glob('*.c'))
if a.arch == 'arm':
    # The upstream 2L expression overflows 32-bit long before conversion to
    # int64_t. Compile the patched private copy, leaving input sources intact.
    original = a.hapsigner / 'hapsigntool_cpp/common/src/byte_buffer.cpp'
    private = a.work / 'hapsigner-patched/hapsigntool_cpp/common/src/byte_buffer.cpp'
    private.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, private)
    patch = ROOT / 'patch/hapsigner-arm32.patch'
    subprocess.run(['git', 'init', '-q', str(a.work/'hapsigner-patched')], check=True)
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=a.work/'hapsigner-patched', check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=a.work/'hapsigner-patched', check=True)
    sources = [private if path == original else path for path in sources]
includes += [base / 'api/include', openssl / 'include', openssl / 'crypto/pkcs12',
             a.third_party / 'elfio', a.third_party / 'elfio/elfio',
             a.third_party / 'cJSON', a.third_party / 'bounds_checking_function/include']
# binary_sign_tool deliberately overrides headers from hapsigntool_cpp.
includes.sort(key=lambda path: 0 if path.is_relative_to(base) else 1)
# The supplied input paths are quoted as CMake string literals, not shell code.
def quote(v):
    return '"' + str(v).replace('\\', '/').replace('"', '\\"').replace(';', '\\;') + '"'
libdir = 'lib' if a.arch == 'arm' else 'lib64'
lines = ['cmake_minimum_required(VERSION 3.20)', 'set(CMAKE_SYSTEM_NAME Linux)',
         'set(CMAKE_C_COMPILER ' + quote(a.sdk / 'llvm/bin/clang') + ')',
         'set(CMAKE_CXX_COMPILER ' + quote(a.sdk / 'llvm/bin/clang++') + ')',
         'set(CMAKE_C_COMPILER_TARGET ' + triple + ')',
         'set(CMAKE_CXX_COMPILER_TARGET ' + triple + ')',
         'set(CMAKE_SYSROOT ' + quote(a.sdk / 'sysroot') + ')',
         'set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)',
         'project(ohos_binary_signer C CXX)', 'set(CMAKE_CXX_STANDARD 17)',
         'add_executable(binary-sign-tool\n' + '\n'.join(map(quote, dict.fromkeys(sources))) + '\n)',
         'target_include_directories(binary-sign-tool PRIVATE\n' + '\n'.join(map(quote, dict.fromkeys(includes))) + '\n)',
         'target_compile_options(binary-sign-tool PRIVATE -fno-rtti -Wno-deprecated-declarations)',
         'target_link_options(binary-sign-tool PRIVATE -static-libstdc++ -Wl,-rpath,/system/' + libdir + '/platformsdk)',
         'target_link_libraries(binary-sign-tool PRIVATE ' + quote(a.libcrypto) + ' dl m)']
if a.arch == 'arm':
    lines.append('target_compile_options(binary-sign-tool PRIVATE -march=armv7-a -mfloat-abi=softfp -mfpu=neon-vfpv4)')
(a.work / 'CMakeLists.txt').write_text('\n'.join(lines) + '\n')
subprocess.run(['cmake', '-S', a.work, '-B', a.work / 'build', '-G', 'Ninja'], env=env, check=True)
subprocess.run(['cmake', '--build', a.work / 'build', '-j', '4'], env=env, check=True)
print(a.work / 'build/binary-sign-tool')
