#!/usr/bin/env python3
"""OHOS SDK C/C++ driver. Set OHOS_NDK_HOME to the SDK native directory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--arch', choices=['arm64', 'arm', 'amd64'], required=True)
p.add_argument('--cxx', action='store_true')
a, flags = p.parse_known_args()
sdk = Path(os.environ['OHOS_NDK_HOME']).expanduser().resolve()
triple = {'arm64': 'aarch64-linux-ohos', 'arm': 'arm-linux-ohos',
          'amd64': 'x86_64-linux-ohos'}[a.arch]
driver = sdk / 'llvm/bin' / ('clang++' if a.cxx else 'clang')
if os.name == 'nt':
    driver = driver.with_suffix('.exe')
cmd = [str(driver), '--target=' + triple, '--sysroot=' + str(sdk / 'sysroot')]
if a.arch == 'arm':
    cmd += ['-march=armv7-a', '-mfloat-abi=softfp', '-mfpu=neon-vfpv4']
sys.exit(subprocess.call(cmd + flags))
