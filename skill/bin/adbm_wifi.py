"""Wireless ADB pairing and reconnection. No device UI or host settings are changed."""
import concurrent.futures
import ipaddress
import json
import math
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
import webbrowser


class WifiError(Exception):
    pass


def lan_ip(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise WifiError("Use the phone's Wi-Fi IPv4 address, for example --ip 192.168.1.20")
    networks = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
    if address.version != 4 or not any(address in ipaddress.ip_network(n) for n in networks):
        raise WifiError('--ip must be a private LAN IPv4 address; no subnet or public-host scanning')
    return str(address)


def remaining(deadline, maximum):
    value = min(maximum, deadline - time.monotonic())
    if value <= 0:
        raise WifiError('Wireless ADB timed out. See skill/reference/connection.md for the failed step.')
    return value


def call(adb, arguments, deadline, maximum=5, secret=None):
    try:
        return subprocess.run([adb] + list(arguments), input=None if secret is None else secret + '\n',
                              capture_output=True, text=True, timeout=remaining(deadline, maximum))
    except FileNotFoundError:
        raise WifiError('adb not found; run adbm doctor and install SDK Platform-Tools')
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(arguments, 124, '', 'ADB request timed out')


def services(text, kind):
    result = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or kind not in parts[1]:
            continue
        host, separator, port = parts[2].rpartition(':')
        if not separator or not port.isdecimal() or not 0 < int(port) < 65536:
            continue
        try:
            host = lan_ip(host)
        except WifiError:
            continue
        result.append((parts[0].removesuffix('.'), host, int(port)))
    return result


def read_peer(cache):
    try:
        peer = json.loads((Path(cache) / 'wifi-peer.json').read_text())
        return peer if isinstance(peer, dict) else {}
    except (OSError, ValueError):
        return {}


def save_peer(cache, ip, port):
    root = Path(cache)
    root.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix='.wifi-peer-', dir=root)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump({'ip': ip, 'port': port}, stream)
            stream.write('\n')
        os.replace(name, root / 'wifi-peer.json')
    finally:
        if os.path.exists(name):
            os.unlink(name)


def qr_payload(service, password):
    return f'WIFI:T:ADB;S:{service};P:{password};;'


def write_qr(payload, path):
    generator = shutil.which('qrencode')
    if generator:
        result = subprocess.run([generator, '-o', str(path), '-s', '9', '-m', '4'],
                                input=payload, capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise WifiError('qrencode failed to generate the pairing QR image')
    else:
        try:
            import qrcode
            qrcode.make(payload, box_size=9, border=4).save(path)
        except ImportError:
            raise WifiError('QR generator missing or incomplete: brew install qrencode (macOS), '
                            'sudo apt install qrencode (Linux), or install qrcode[pil] for this Python')
    path.chmod(0o600)


def open_ports(ip, deadline, ports=range(32768, 61000), workers=192):
    """Bounded discovery of Android's ephemeral ports on one explicit/cached LAN address."""
    found = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    pending = set()
    source = iter(ports)

    def probe(port):
        try:
            with socket.create_connection((ip, port), timeout=0.2):
                return port
        except OSError:
            return None

    def fill():
        while len(pending) < workers and time.monotonic() < deadline:
            try:
                pending.add(pool.submit(probe, next(source)))
            except StopIteration:
                break

    try:
        fill()
        while pending and time.monotonic() < deadline:
            done, pending = concurrent.futures.wait(pending, timeout=min(0.25, max(0, deadline - time.monotonic())),
                                                   return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                port = future.result()
                if port is not None:
                    found.append(port)
            fill()
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)
    return sorted(set(found))


def try_connect(adb, ip, port, deadline):
    target = f'{ip}:{port}'
    result = call(adb, ['connect', target], deadline, maximum=3)
    if result.returncode == 0:
        state = call(adb, ['-s', target, 'get-state'], deadline, maximum=2)
        if state.returncode == 0 and state.stdout.strip() == 'device':
            return target
    call(adb, ['disconnect', target], deadline, maximum=1)
    return None


def connect_phone(adb, cache, ip, deadline, port=None, candidates=(), scan=True):
    peer = read_peer(cache)
    choices = [port]
    if peer.get('ip') == ip:
        choices.append(peer.get('port'))
    mdns = call(adb, ['mdns', 'services'], deadline)
    choices.extend(p for _, host, p in services(mdns.stdout, '_adb-tls-connect._tcp') if host == ip)
    choices.extend(candidates)
    tried = set()

    def attempt(values):
        for candidate in values:
            if (isinstance(candidate, bool) or not isinstance(candidate, int)
                    or not 0 < candidate < 65536 or candidate in tried):
                continue
            tried.add(candidate)
            target = try_connect(adb, ip, candidate, deadline)
            if target:
                save_peer(cache, ip, candidate)
                print(f'connected: {target}', flush=True)
                return target
        return None

    target = attempt(choices)
    if not target and scan:
        print(f'mDNS/cache did not connect; discovering ADB ports only on {ip}', flush=True)
        # Reserve time to authenticate discovered endpoints, even on a filtering network.
        scan_deadline = min(deadline - 8, time.monotonic() + 35)
        target = attempt(open_ports(ip, scan_deadline))
    return target


def ensure_server(adb, deadline):
    result = call(adb, ['start-server'], deadline, maximum=15)
    if result.returncode:
        raise WifiError('ADB server did not start. Run adbm doctor; check SDK Platform-Tools and local-network access.')


def validate_options(args):
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise WifiError('--timeout must be a positive finite number of seconds')
    port = getattr(args, 'port', None)
    if port is not None and not 0 < port < 65536:
        raise WifiError('--port must be in 1..65535 and be the debugging port, not the pairing port')


def connect(args, adb, cache):
    validate_options(args)
    peer = read_peer(cache)
    value = args.ip or peer.get('ip')
    if not value:
        raise WifiError('No saved phone. Use adbm pair, or adbm connect --ip <phone-Wi-Fi-IP>')
    ip = lan_ip(value)
    deadline = time.monotonic() + args.timeout
    ensure_server(adb, deadline)
    if connect_phone(adb, cache, ip, deadline, port=args.port):
        return 0
    raise WifiError('No authenticated ADB connection. Keep the phone on the same Wi-Fi, enable Wireless debugging, '
                    'check VPN/firewall and use adbm pair if this computer is not paired. '
                    'See skill/reference/connection.md.')


def pair(args, adb, cache):
    validate_options(args)
    peer = read_peer(cache)
    explicit_ip = lan_ip(args.ip) if args.ip else None
    ip = explicit_ip or (lan_ip(peer['ip']) if peer.get('ip') else None)
    deadline = time.monotonic() + args.timeout
    ensure_server(adb, deadline)
    service = 'studio-adbm-' + secrets.token_hex(6)
    password = secrets.token_hex(12)
    Path(cache).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wifi-qr-', dir=cache) as folder:
        image = Path(folder) / 'pair.png'
        write_qr(qr_payload(service, password), image)
        print(f'qr: {image.resolve()}', flush=True)
        print('On the phone: Settings > Developer options > Wireless debugging > Pair device with QR code.', flush=True)
        print('Scan this image and keep the pairing screen open. Waiting for the phone…', flush=True)
        if args.open:
            webbrowser.open(image.resolve().as_uri())
        attempted = {}
        scanned = []
        next_scan = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = call(adb, ['mdns', 'services'], deadline)
            endpoints = [(explicit_ip or host, port) for name, host, port in
                         services(result.stdout, '_adb-tls-pairing._tcp') if name == service]
            if not endpoints and ip and time.monotonic() >= next_scan:
                print(f'No matching mDNS service; looking for the QR pairing port only on {ip}', flush=True)
                scanned = open_ports(ip, min(time.monotonic() + 35, deadline - 15))
                endpoints = [(ip, port) for port in scanned if not
                             (peer.get('ip') == ip and peer.get('port') == port)]
                next_scan = time.monotonic() + 10
            for host, port in endpoints:
                last_attempt = attempted.get((host, port))
                if last_attempt is not None and time.monotonic() - last_attempt < 5:
                    continue
                attempted[(host, port)] = time.monotonic()
                response = call(adb, ['pair', f'{host}:{port}'], deadline, maximum=4, secret=password)
                if response.returncode == 0 and 'Successfully paired' in response.stdout:
                    print(f'paired: {host}', flush=True)
                    save_peer(cache, host, peer.get('port') if peer.get('ip') == host else None)
                    if connect_phone(adb, cache, host, deadline, candidates=scanned):
                        return 0
                    raise WifiError('Pairing succeeded, but the debugging port did not connect. '
                                    f'Keep Wireless debugging enabled and run adbm connect --ip {host}. '
                                    'Pairing and debugging ports are different.')
            time.sleep(min(1, max(0, deadline - time.monotonic())))
    raise WifiError('QR pairing timed out. If mDNS is empty, re-run adbm pair --ip <phone-Wi-Fi-IP>. '
                    'Confirm the QR screen was scanned and VPN/firewall permits this phone. '
                    'Use the Wi-Fi IP, not a VPN/TUN address. See skill/reference/connection.md.')
