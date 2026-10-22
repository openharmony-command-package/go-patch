#!/usr/bin/env python3
"""Boot checksum-pinned full OHOS systems with private disks, ports and HDC."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import shutil
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
LOCK = json.loads((ROOT / 'manifest.json').read_text())


def hdc(a, *args, target=True, timeout=120):
    cmd = [a.hdc, '-s', '127.0.0.1:' + str(a.server)]
    if target:
        cmd += ['-t', '127.0.0.1:' + str(a.port)]
    result = subprocess.run(cmd + list(map(str, args)), capture_output=True,
                            text=True, timeout=timeout)
    output = result.stdout + result.stderr
    if result.returncode or re.search(r'\[Fail\]|Device not found|E001005', output):
        raise RuntimeError(output)
    return output


def shell(a, command, timeout=120):
    # Keep explicit exit/exec in a caller's script from bypassing the status
    # trailer. The parent shell reports the subshell's actual exit status.
    output = hdc(a, 'shell', '(\n' + command.rstrip() + '\n)\nrc=$?; echo __GO_PATCH_EXIT__=$rc', timeout=timeout)
    statuses = re.findall(r'__GO_PATCH_EXIT__=(\d+)', output)
    if not statuses or statuses[-1] != '0':
        log = a.work / a.arch / 'last-shell-error.log'
        log.write_text(output)
        if len(output) > 12000:
            output = output[:4000] + '\n... full output: ' + str(log) + '\n' + output[-6000:]
        raise RuntimeError(output)
    return output.rsplit('__GO_PATCH_EXIT__=', 1)[0]


def state_path(a):
    return a.work / a.arch / 'state.json'


def posix_profile(a, package):
    """Tolerate the pinned ARMv7 image's unrelated GUI-service crash.

    Change only the critical flag byte in our offline ext4 copy. Keeping the
    inode preserves its ownership, mode and SELinux xattrs. Every read and
    physical offset is checked before writing; no system library is changed.
    """
    debugfs = shutil.which('debugfs') or '/opt/homebrew/opt/e2fsprogs/sbin/debugfs'
    image = package / 'images/system.img'
    records = []
    def query(command):
        return subprocess.check_output([debugfs, '-R', command, str(image)], stderr=subprocess.DEVNULL)
    stats = query('stats').decode()
    blocksize = int(re.search(r'Block size:\s+(\d+)', stats).group(1))
    for name in ['foundation', 'graphic']:
        path = '/etc/init/' + name + '.cfg'
        original = query('cat ' + path)
        json.loads(original)
        matches = list(re.finditer(rb'("critical"\s*:\s*\[\s*)([01])(?=\s*,)', original))
        if len(matches) != 1:
            raise SystemExit('unrecognized private ARMv7 configuration: ' + path)
        blocks = [int(value) for value in query('blocks ' + path).split()]
        match = matches[0]
        with open(image, 'r+b') as stream:
            data = bytearray()
            for block in blocks:
                stream.seek(block * blocksize)
                data.extend(stream.read(blocksize))
            if data[:len(original)] != original:
                raise SystemExit('inode mapping does not match contents: ' + path)
            offset = match.start(2)
            stream.seek(blocks[offset // blocksize] * blocksize + offset % blocksize)
            stream.write(b'0')
        patched = original[:offset] + b'0' + original[offset + 1:]
        if query('cat ' + path) != patched:
            raise SystemExit('private profile verification failed: ' + path)
        dest = a.work / a.arch
        backup = dest / (name + '.cfg.original')
        if not backup.exists():
            backup.write_bytes(original)
        records.append(dict(file=path, change='critical[0] = 0',
            before_sha256=hashlib.sha256(backup.read_bytes()).hexdigest(),
            after_sha256=hashlib.sha256(patched).hexdigest()))
    (dest / 'profile.json').write_text(json.dumps(dict(profile='posix', edits=records), indent=2) + '\n')


def load(a):
    s = json.loads(state_path(a).read_text())
    a.port, a.server, a.hdc = s['port'], s['server'], s['hdc']
    ensure_server(a, s)
    return s


def ensure_server(a, state):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', a.server)) == 0:
            return
    log = open(a.work / a.arch / 'hdc-server.log', 'a')
    # HDC's singleton lock is keyed by its temporary directory, not -s port.
    # Separate it from the user's SDK daemon and other private server ports.
    runtime = a.work / 'hdc-runtime' / str(a.server)
    runtime.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen([a.hdc, '-m', '-s', '127.0.0.1:' + str(a.server)],
                            env=dict(os.environ, TMPDIR=str(runtime)),
                            start_new_session=True, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT)
    state['server_pid'] = proc.pid
    state_path(a).write_text(json.dumps(state, indent=2) + '\n')
    time.sleep(1)


def boot(a):
    dest = a.work / a.arch
    dest.mkdir(parents=True, exist_ok=True)
    if state_path(a).exists():
        raise SystemExit('state exists; stop this private QEMU before booting again')
    t = next(t for t in LOCK['qemu']['targets'] if t['name'] == a.arch)
    archive = a.packages / t['package']
    h = hashlib.sha256()
    with open(archive, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    if h.hexdigest() != t['sha256']:
        raise SystemExit('QEMU archive checksum mismatch: ' + str(archive))
    print('verified QEMU archive:', archive, flush=True)
    package = dest / t['package'].removesuffix('.tar.gz')
    # Restore pristine disks unless explicitly resuming our own offline image.
    if not a.reuse_images:
        subprocess.run(['tar', '-xzf', archive, '-C', dest], check=True,
                       env=dict(os.environ, LC_ALL='C'))
        for profile_file in ['profile.json', 'profile.log']:
            (dest / profile_file).unlink(missing_ok=True)
    elif not package.is_dir():
        raise SystemExit('--reuse-images requires an existing private image')
    elif a.profile == 'stock' and (dest / 'profile.json').exists():
        raise SystemExit('private image contains POSIX profile edits; restore pristine disks for a stock run')
    if a.profile == 'posix' and a.arch == 'armv7a':
        posix_profile(a, package)
    launcher = package / 'launch/qemu_run.sh'
    s = launcher.read_text()
    if a.memory_mib < 512:
        raise SystemExit('memory-mib must be at least 512')
    s, memory_count = re.subn(r'(?<!\S)-m\s+\d+', '-m ' + str(a.memory_mib), s)
    if memory_count != 1:
        raise SystemExit('unrecognized QEMU launcher memory argument')
    s, count = re.subn(r'hostfwd=tcp:(?:127\.0\.0\.1)?:\d+-:5555',
                      'hostfwd=tcp:127.0.0.1:' + str(a.port) + '-:5555', s)
    if count != 1:
        raise SystemExit('unrecognized QEMU launcher network arguments')
    qmp=dest/'qmp.sock'
    qmp.unlink(missing_ok=True)
    qmp_arg='-qmp unix:'+str(qmp)+',server=on,wait=off'
    if '-qmp ' in s:
        s=re.sub(r'-qmp\s+\S+',qmp_arg,s)
    else:
        binary='qemu-system-'+{'arm64':'aarch64','armv7a':'arm','x86_64':'x86_64'}[a.arch]
        # ARM launchers first probe -accel help; modify only the actual command.
        command=re.search(r'(?m)^(?:QEMU_CMD="(?:\$\{SUDO\}\s+)?|exec )'+re.escape(binary)+r'\s+',s)
        if command is None:raise SystemExit('unrecognized QEMU launch command')
        s=s[:command.end()]+qmp_arg+' '+s[command.end():]
    if a.arch == 'armv7a':
        # ARMv7's compositor needs an actual scanout even for shell testing.
        # With -display none foundation dies and init deliberately panics.
        # A loopback-only VNC backend supplies scanout without opening a UI.
        s = s.replace('-display none', '-vnc 127.0.0.1:' + str(a.vnc_display))
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 5900 + a.vnc_display))
    launcher.write_text(s)
    userdata = package / 'images/userdata.img'
    wanted = a.userdata_gib * 1024**3
    if userdata.stat().st_size <= wanted:
        resize = shutil.which('resize2fs')
        if not resize and Path('/opt/homebrew/opt/e2fsprogs/sbin/resize2fs').exists():
            resize = '/opt/homebrew/opt/e2fsprogs/sbin/resize2fs'
        if not resize:
            raise SystemExit('resize2fs is required for the full Go suite disk')
        # A stopped guest may leave an ext4 journal. Replay it before changing
        # the offline geometry, or the next boot can undo the new superblock.
        fsck = str(Path(resize).with_name('e2fsck'))
        result = subprocess.run([fsck, '-f', '-y', str(userdata)])
        if result.returncode not in (0, 1, 2):
            raise SystemExit('private userdata fsck failed')
        os.truncate(userdata, wanted)
        subprocess.run([resize, '-f', str(userdata)], check=True)
    if a.accel == 'auto' and a.arch == 'arm64' and platform.system() == 'Darwin' and platform.machine() == 'arm64':
        if 'ACCEL_ARGS="-accel hvf"' not in s:
            s = s.replace('NET_ARGS=(', 'ACCEL_ARGS="-accel hvf"\nNET_ARGS=(', 1)
        s = s.replace('-cpu cortex-a57', '-cpu host')
        launcher.write_text(s)
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', a.port))
    log = open(dest / 'serial.log', 'w')
    entry = package / 'launch' / ('macos.command' if platform.system() == 'Darwin' else 'linux.sh')
    proc = subprocess.Popen(['bash', str(entry)], cwd=package,
                            env=dict(os.environ, QEMU_DISPLAY='none'),
                            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    state_path(a).write_text(json.dumps(dict(pid=proc.pid, port=a.port, server=a.server,
                                            hdc=a.hdc, archive_sha256=t['sha256'], profile=a.profile,qmp=str(qmp),memory_mib=a.memory_mib), indent=2) + '\n')
    ensure_server(a, json.loads(state_path(a).read_text()))
    deadline = time.monotonic() + a.boot_timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError('QEMU exited; inspect ' + str(dest / 'serial.log'))
        try:
            hdc(a, 'tconn', '127.0.0.1:' + str(a.port), target=False, timeout=10)
            if 'GO_PATCH_READY' in shell(a, 'echo GO_PATCH_READY', timeout=15):
                # A headless device's power service can suspend the complete
                # guest while Go is busy. Disable that service for this test VM.
                awake=shell(a,'begetctl stop_service powermgr',timeout=30)
                (dest/'power.log').write_text(awake)
                state=json.loads(state_path(a).read_text())
                state['power_policy']='powermgr stopped during headless Go tests'
                state_path(a).write_text(json.dumps(state,indent=2)+'\n')
                if a.profile == 'posix':
                    output = shell(a, 'begetctl stop_service render_service; begetctl stop_service foundation', timeout=30)
                    (dest / 'profile.log').write_text('POSIX test profile: begetctl stop_service foundation\n' + output)
                print('QEMU ready:', a.arch, 'PID', proc.pid, flush=True)
                return
        except (RuntimeError, subprocess.TimeoutExpired):
            pass
        time.sleep(3)
    raise RuntimeError('QEMU boot timeout; logs and state preserved')


def stop(a):
    s = load(a)
    try:
        os.killpg(s['pid'], signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(20):
        try:
            os.killpg(s['pid'], 0)
        except (ProcessLookupError, PermissionError):
            break
        time.sleep(0.25)
    try:
        hdc(a, 'tconn', '127.0.0.1:' + str(a.port), '-remove', target=False)
    except RuntimeError as error:
        if 'No target available' not in str(error):
            raise
    finally:
        state_path(a).unlink()
        if s.get('qmp'):Path(s['qmp']).unlink(missing_ok=True)


def wake(a):
    state=load(a)
    if not state.get('qmp'):
        raise SystemExit('this older instance has no QMP control socket')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect(state['qmp'])
        stream=sock.makefile('rwb')
        json.loads(stream.readline())
        for number,command in enumerate(['qmp_capabilities','system_wakeup','query-status']):
            stream.write((json.dumps(dict(execute=command,id=number))+'\n').encode());stream.flush()
            while True:
                result=json.loads(stream.readline())
                if result.get('id')==number:break
            if 'error' in result and not (command=='system_wakeup' and 'not in suspended state' in result['error'].get('desc','')):
                raise RuntimeError(result['error'])
        print(json.dumps(result['return']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arch', choices=['arm64', 'armv7a', 'x86_64'], required=True)
    p.add_argument('--work', type=Path, default=ROOT / '.work/qemu')
    p.add_argument('--packages', type=Path)
    p.add_argument('--hdc', default=os.environ.get('HDC', 'hdc'))
    p.add_argument('--port', type=int, default=5569)
    p.add_argument('--server', type=int, default=18769)
    p.add_argument('--boot-timeout', type=int, default=720)
    p.add_argument('--userdata-gib', type=int, default=24)
    p.add_argument('--memory-mib', type=int, default=4096, help='private QEMU RAM in MiB')
    p.add_argument('--reuse-images', action='store_true', help='resume this private disk instead of extracting pristine images')
    p.add_argument('--profile', choices=['stock', 'posix'], default='stock', help='posix stops the graphical foundation service via begetctl')
    p.add_argument('--accel', choices=['auto', 'tcg'], default='auto')
    p.add_argument('--vnc-display', type=int, default=71, help='loopback ARMv7 scanout (TCP 5900+N)')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('boot')
    sub.add_parser('stop')
    sub.add_parser('wake')
    s = sub.add_parser('shell')
    s.add_argument('script')
    s.add_argument('--timeout', type=int, default=120)
    for direction in ['send', 'recv']:
        f = sub.add_parser(direction)
        f.add_argument('source')
        f.add_argument('destination')
    a = p.parse_args()
    a.work = a.work.resolve()
    if a.command == 'boot':
        if a.packages is None:
            p.error('boot requires --packages')
        boot(a)
    elif a.command == 'wake':
        wake(a)
    elif a.command == 'stop':
        stop(a)
    else:
        load(a)
        hdc(a, 'tconn', '127.0.0.1:' + str(a.port), target=False)
        if a.command == 'shell':
            output = shell(a, a.script, timeout=a.timeout)
            if len(output) > 16000:
                log = a.work / a.arch / 'last-shell-output.log'
                log.write_text(output)
                output = output[:2000] + '\n... full output: ' + str(log) + '\n' + output[-6000:]
            print(output, end='')
        else:
            print(hdc(a, 'file', a.command, a.source, a.destination, timeout=1200), end='')


if __name__ == '__main__':
    main()
