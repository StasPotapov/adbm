"""Wi-Fi pairing tests: no Android device, no LAN scanning beyond a localhost fixture."""
import argparse
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adbm_wifi_tested', ROOT / 'skill/bin/adbm_wifi.py')
wifi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wifi)


def result(out='', code=0):
    return subprocess.CompletedProcess([], code, out, '')


class WifiTests(unittest.TestCase):
    def test_private_scope_rejects_public_loopback_subnet_and_special_addresses(self):
        for value in ['8.8.8.8', '127.0.0.1', '192.168.1.0/24', '192.0.2.1', '255.255.255.255', '::1']:
            with self.subTest(value=value), self.assertRaises(wifi.WifiError):
                wifi.lan_ip(value)
        self.assertEqual(wifi.lan_ip('192.168.1.20'), '192.168.1.20')

    def test_mdns_ignores_unrelated_kinds_and_invalid_endpoints(self):
        text = ('List of discovered mdns services\n'
                'first _adb-tls-connect._tcp 192.168.1.20:41111 Android.local\n'
                'second _adb-tls-pairing._tcp 192.168.1.21:42222\n'
                'bad _adb-tls-connect._tcp 8.8.8.8:33\n'
                'bad _adb-tls-connect._tcp 192.168.1.20:99999\n')
        self.assertEqual(wifi.services(text, '_adb-tls-connect._tcp'), [('first', '192.168.1.20', 41111)])

    def test_saved_peer_has_no_credentials_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as cache:
            wifi.save_peer(cache, '192.168.1.20', 41111)
            self.assertEqual(wifi.read_peer(cache), {'ip': '192.168.1.20', 'port': 41111})
            self.assertEqual(os.stat(Path(cache) / 'wifi-peer.json').st_mode & 0o777, 0o600)
            (Path(cache) / 'wifi-peer.json').write_text('not json')
            self.assertEqual(wifi.read_peer(cache), {})

    def test_verified_connection_is_required_and_failed_probe_is_disconnected(self):
        for state in ['offline', 'unauthorized', '']:
            responses = [result('connected to 192.168.1.20:41111'), result(state), result()]
            with patch.object(wifi, 'call', side_effect=responses) as call:
                self.assertIsNone(wifi.try_connect('adb', '192.168.1.20', 41111, time.monotonic() + 10))
                self.assertEqual(call.call_args.args[1], ['disconnect', '192.168.1.20:41111'])
        with patch.object(wifi, 'call', side_effect=[result(), result('device\n')]):
            self.assertEqual(wifi.try_connect('adb', '192.168.1.20', 41111, time.monotonic() + 10),
                             '192.168.1.20:41111')

    def test_cached_connection_avoids_port_scan_and_ignores_another_phones_cache(self):
        with tempfile.TemporaryDirectory() as cache:
            wifi.save_peer(cache, '192.168.1.20', 41111)
            with patch.object(wifi, 'call', return_value=result()), \
                 patch.object(wifi, 'try_connect', return_value='192.168.1.20:41111') as connect, \
                 patch.object(wifi, 'open_ports') as scan, contextlib.redirect_stdout(io.StringIO()):
                self.assertTrue(wifi.connect_phone('adb', cache, '192.168.1.20', time.monotonic() + 10))
                scan.assert_not_called()
                self.assertEqual(connect.call_args.args[2], 41111)
            with patch.object(wifi, 'call', return_value=result()), patch.object(wifi, 'try_connect') as connect:
                self.assertIsNone(wifi.connect_phone('adb', cache, '192.168.1.21', time.monotonic() + 10, scan=False))
                connect.assert_not_called()

    def test_single_host_scanner_with_real_localhost_listener(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen(2)
            port = server.getsockname()[1]
            self.assertEqual(wifi.open_ports('127.0.0.1', time.monotonic() + 2, ports=[port], workers=2), [port])
        start = time.monotonic()
        self.assertEqual(wifi.open_ports('127.0.0.1', start - 1, ports=range(1000), workers=2), [])
        self.assertLess(time.monotonic() - start, 0.5)

    def test_pair_uses_only_current_qr_service_and_overrides_advertised_vpn_ip(self):
        for connected in [True, False]:
            with self.subTest(connected=connected), tempfile.TemporaryDirectory() as cache:
                qr_paths = []
                seen = []
                def fake_qr(payload, path):
                    self.assertIn('WIFI:T:ADB;S:studio-adbm-session;P:password;;', payload)
                    path.write_bytes(b'qr fixture')
                    qr_paths.append(path)
                def fake_call(adb, arguments, deadline, maximum=5, secret=None):
                    seen.append((arguments, secret))
                    if arguments[0] == 'start-server':
                        return result()
                    if arguments[0] == 'mdns':
                        return result('other-session _adb-tls-pairing._tcp 192.168.1.99:40000\n'
                                      'studio-adbm-session _adb-tls-pairing._tcp 172.19.0.1:42222\n')
                    if arguments[0] == 'pair':
                        self.assertEqual(arguments, ['pair', '192.168.1.20:42222'])
                        self.assertEqual(secret, 'password')
                        return result('Successfully paired to 192.168.1.20:42222')
                    self.fail(str(arguments))
                args = argparse.Namespace(ip='192.168.1.20', timeout=5, open=False)
                output = io.StringIO()
                with patch.object(wifi.secrets, 'token_hex', side_effect=['session', 'password']), \
                     patch.object(wifi, 'write_qr', side_effect=fake_qr), \
                     patch.object(wifi, 'call', side_effect=fake_call), \
                     patch.object(wifi, 'connect_phone', return_value='serial' if connected else None), \
                     contextlib.redirect_stdout(output):
                    if connected:
                        self.assertEqual(wifi.pair(args, 'adb', cache), 0)
                    else:
                        with self.assertRaisesRegex(wifi.WifiError, 'Pairing succeeded'):
                            wifi.pair(args, 'adb', cache)
                self.assertTrue(qr_paths)
                self.assertFalse(qr_paths[0].exists())
                self.assertNotIn('password', output.getvalue())
                self.assertEqual(len([x for x in seen if x[0][0] == 'pair']), 1)
                self.assertNotIn('password', (Path(cache) / 'wifi-peer.json').read_text())

    def test_bad_timeout_and_port_fail_before_network(self):
        for timeout in [-1, 0, float('inf'), float('nan')]:
            with self.subTest(timeout=timeout), self.assertRaises(wifi.WifiError):
                wifi.validate_options(argparse.Namespace(timeout=timeout))
        with self.assertRaises(wifi.WifiError):
            wifi.validate_options(argparse.Namespace(timeout=10, port=70000))

    def test_current_qr_address_beats_cache_and_transient_pair_failure_retries(self):
        with tempfile.TemporaryDirectory() as cache:
            wifi.save_peer(cache, '192.168.1.99', 41111)
            clock = [0.0]
            attempts = []
            def fake_call(adb, arguments, deadline, maximum=5, secret=None):
                if arguments[0] == 'start-server':
                    return result()
                if arguments[0] == 'mdns':
                    return result('studio-adbm-session _adb-tls-pairing._tcp 192.168.1.20:42222\n')
                self.assertEqual(arguments, ['pair', '192.168.1.20:42222'])
                attempts.append(clock[0])
                return result(code=124) if len(attempts) == 1 else result('Successfully paired')
            with patch.object(wifi.secrets, 'token_hex', side_effect=['session', 'password']), \
                 patch.object(wifi, 'write_qr', side_effect=lambda payload, path: path.write_bytes(b'qr')), \
                 patch.object(wifi, 'call', side_effect=fake_call), \
                 patch.object(wifi, 'connect_phone', return_value='serial'), \
                 patch.object(wifi.time, 'monotonic', side_effect=lambda: clock[0]), \
                 patch.object(wifi.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(wifi.pair(argparse.Namespace(ip=None, timeout=20, open=False), 'adb', cache), 0)
            self.assertEqual(len(attempts), 2)
            self.assertGreaterEqual(attempts[1] - attempts[0], 5)
            self.assertEqual(wifi.read_peer(cache)['ip'], '192.168.1.20')

    def test_incomplete_qrcode_backend_reports_install_instructions(self):
        def missing_backend(*args, **kwargs):
            raise ImportError('PIL is missing')
        with tempfile.TemporaryDirectory() as cache, patch.object(wifi.shutil, 'which', return_value=None), \
             patch.dict(sys.modules, {'qrcode': SimpleNamespace(make=missing_backend)}):
            with self.assertRaisesRegex(wifi.WifiError, 'qrcode\\[pil\\]'):
                wifi.write_qr('test payload', Path(cache) / 'pair.png')

    def test_qr_is_deleted_on_timeout_and_interrupt(self):
        for interrupt in [False, True]:
            with self.subTest(interrupt=interrupt), tempfile.TemporaryDirectory() as cache:
                clock = [0.0]
                images = []
                def fake_qr(payload, path):
                    path.write_bytes(b'qr'); images.append(path)
                def fake_call(adb, arguments, deadline, maximum=5, secret=None):
                    if interrupt and arguments[0] == 'mdns':
                        raise KeyboardInterrupt()
                    return result()
                with patch.object(wifi, 'write_qr', side_effect=fake_qr), \
                     patch.object(wifi, 'call', side_effect=fake_call), \
                     patch.object(wifi.time, 'monotonic', side_effect=lambda: clock[0]), \
                     patch.object(wifi.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)), \
                     contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(KeyboardInterrupt if interrupt else wifi.WifiError):
                        wifi.pair(argparse.Namespace(ip=None, timeout=2, open=False), 'adb', cache)
                self.assertTrue(images)
                self.assertFalse(images[0].exists())


if __name__ == '__main__':
    unittest.main()
