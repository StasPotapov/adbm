# Wireless pairing and connection

Use `adbm pair` for Android 11+ secure Wireless debugging. Android Studio and a USB cable are not required.

## First pairing: one command

```bash
adbm pair --open
# If mDNS discovery is unavailable, supply the phone's Wi-Fi address:
adbm pair --ip 192.168.1.20 --open
```

The command creates a QR image, waits for the phone, pairs and connects it. `--open` opens the image
in the system viewer; without it the first output line is `qr: /absolute/path/pair.png`.
On the phone enable Developer options → Wireless debugging → **Pair device with QR code** and scan
this image. Keep that screen open. Both devices must be on the same local Wi-Fi network.

QR generation needs `qrencode` (`brew install qrencode` on macOS, `sudo apt install qrencode` on Linux)
or Python `qrcode[pil]` installed for the interpreter that runs adbm. Missing tools produce an install
instruction; `pair` does not install packages or accept licenses. SDK Platform-Tools 37+ is recommended.
Use `sdkmanager "platform-tools"` to update after the person has accepted the SDK licenses.

A successful command prints `paired: <IP>` and then `connected: <IP>:<debugging-port>`.
Pairing alone is not a working device: confirm `adbm devices` shows the physical phone in `device`
state before installing an APK. A pairing success followed by a connection error means the key was
accepted; use `adbm connect`, rather than pairing again immediately.

## Agent workflow

1. Determine the current skill root and use its `bin/adbm`.
2. Start `pair` with an early tool yield (about 1 s), so its QR path reaches you while it is waiting.
   Embed that path as an image for the person. This is a generated QR, not a device screenshot.
3. Ask only for the physical action: open the QR scanner under Wireless debugging and scan the image.
   Continue waiting on the same running command, with progress updates as needed.
4. Wait for `connected:` and confirm `adbm devices`. Then use the reported `--serial` for all device work.

`--timeout` is the total wait and connection budget (default 120 s for pairing, 60 s for reconnect).
The temporary QR image is private and is deleted when the command exits, including timeout or Ctrl-C.
Do not reuse its path after exit: start a new command to create a new QR. Never copy its password,
payload or ADB private key into a repository, skill, logs or environment notes.

## Subsequent connections

```bash
adbm connect
adbm connect --ip 192.168.1.20
adbm connect --ip 192.168.1.20 --port 41234
```

The last successful phone address and debugging port live in `$ADBM_CACHE/wifi-peer.json` (normally
`~/.cache/adbm/wifi-peer.json`). No pairing secret is stored there. ADB keeps the workstation key in
its own Android configuration directory; do not delete it as a troubleshooting shortcut.

`connect` verifies `get-state == device`. It tries the supplied/cached port and the chosen phone's
mDNS service. If those fail, it discovers Android ephemeral TCP ports (32768–60999) on **that one
private IPv4 address**, with bounded concurrency and time. It does not scan subnets or public hosts.
`pair --ip` uses the same single-host fallback for the QR pairing endpoint when mDNS is empty.
Without an explicit or cached IP, pairing waits for its unique mDNS service and reports how to retry
with `--ip` on timeout. It never chooses an unrelated phone's pairing session.

The pairing port and debugging port are different. A port shown in the six-digit-code dialog is
for pairing, not `connect`. Ports can change after Wireless debugging is toggled or the phone reboots;
the saved port is a fast path, not a permanent setting.

## When it fails

| Symptom | Next action |
|---|---|
| QR generator missing | Install qrencode or qrcode[pil] for this Python, then rerun `pair`. |
| QR scan says connecting forever; mDNS is empty | Get the phone's actual Wi-Fi IPv4 in the Wi-Fi network details; rerun `pair --ip <IP>`. Keep the scanner open. |
| Phone shows a VPN/TUN address such as 172.19.0.1 | Use its Wi-Fi address instead. `--ip` also overrides an unusable address in the matched mDNS announcement. |
| Paired, but connection failed | Run `connect --ip <IP>`; use the debugging port from the main Wireless debugging screen with `--port` if known. |
| No open endpoint found | Confirm the current Wi-Fi IP, Wireless debugging switch and same network. Guest/AP isolation can block peers. The fallback covers Android's usual ephemeral range; another range needs an explicit debugging `--port`. |
| Connection refused | The host is reachable, but this port is closed or has changed; rerun `connect`. |
| Timeout / no route to host | Check network reachability, VPN routing and the host app's Local Network permission on macOS. Check the firewall before repeating pair attempts. |
| `offline` or `unauthorized` | The connection is not ready. Check the phone's trusted/paired computers and retry `connect`; do not report a successful install target. |

A workstation VPN kill switch can block both mDNS (UDP 224.0.0.251:5353) and direct TCP to the phone.
Do not disable the VPN or firewall automatically. A narrow exception for the chosen phone and mDNS
may be appropriate, but it is a separate host configuration action. Restore any VPN setting that was
temporarily changed for diagnosis. `pair` and `connect` themselves change no VPN, firewall, routing
or phone settings, and do not restart a shared ADB server or interrupt other devices.

ADB 37.0.1 uses libadbmdns; the old `ADB_MDNS_OPENSCREEN` variable no longer changes its backend.
Check the actual server with `adb server-status` when diagnosing a version mismatch. A terminal
`adb mdns services` talks to the already-running server; it does not prove that the server itself was
started by that terminal. Compare the process/server context only when it matters to OS permissions.

Protocol and current tool behavior: [ADB Wi-Fi architecture](https://android.googlesource.com/platform/packages/modules/adb/+/HEAD/docs/dev/adb_wifi.md),
[Platform-Tools release notes](https://developer.android.com/tools/releases/platform-tools).
