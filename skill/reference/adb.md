# Raw adb — only what `adbm` does not do

Do everyday work through `adbm`: apps (`launch`, `stop`, `clear`, `uninstall`, `open`, `perm`),
input (`tap`, `type`, `key`, `swipe`, `rotate`, several at once — `batch`), logs and crashes (`log`, `crashes`),
GPS (`location`), the clipboard (`clipboard`), files (`push`, `pull`), frames and the tree.
Raw adb commands do not log to the `save-flow` journal and do not sort frames into a run.

With more than one device connected, always write `adb -s <serial>`.
`adbm devices` maps API levels to serials. An emulator's serial changes between launches.

## Devices and server

```bash
adb kill-server && adb start-server  # restart the server
adb -s SERIAL tcpip 5555             # Wi-Fi: over USB first
adb connect <ip>:5555
adb -s SERIAL shell ip route | grep src   # device IP
```

## State

```bash
adb -s SERIAL shell wm density            # wm density 320 / wm density reset
adb -s SERIAL shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
```

Back to the launcher through the whole back stack:

```bash
HOME_PKG=$(adb -s SERIAL shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME | tail -1 | cut -d/ -f1)
for i in $(seq 1 20); do
  adb -s SERIAL shell dumpsys window | grep mCurrentFocus | grep -q "$HOME_PKG" && break
  adb -s SERIAL shell input keyevent KEYCODE_BACK; sleep 0.5
done
```

On API 35 emulators `monkey -p <package> 1` prints `SYS_KEYS has no physical keys`
and does not start the app. That is why `adbm launch` uses `am start`.

## Accessibility and display

`adbm restore` does not know about these. Before a change, read the value (`settings get secure <key>`,
`null` — never set); when the check is over, write it back (`settings delete` for `null`).
For `*_animation_scale` and `font_scale` write `1.0` instead of a delete: after a delete Android may keep the old scale.

```bash
adb -s SERIAL shell settings put secure high_text_contrast_enabled 1
adb -s SERIAL shell settings put secure accessibility_display_inversion_enabled 1
adb -s SERIAL shell settings put secure enabled_accessibility_services \
  com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService
adb -s SERIAL shell cmd uimode night auto                  # adbm prep sets only yes/no
```

Theme, navigation mode, font scale and animations: `adbm prep`, not raw adb: `adbm restore` undoes only what adbm saved.

## adb failures

| Failure | What to do |
|---|---|
| `device unauthorized` | confirm the dialog on the device, then `adb kill-server && adb start-server` |
| `device offline` | `adb reconnect`, reconnect the cable; an emulator — `adbm devices --stop N`, `--start N` |
| `more than one device` | add `-s SERIAL` |
| `uiautomator dump` prints `could not get idle state` | an animation is running: `adbm prep`, then retry |
| a command hangs | `timeout 10 adb …` |
