# Raw adb — when `adbm` is not enough

A reference for rare actions. Do everyday work through `adbm`: the commands below
do not log to the `save-flow` journal and do not sort frames into a run.

With more than one device connected, always write `adb -s <serial>`.
`adbm devices` maps API levels to serials. An emulator's serial changes between launches.

## Devices and server

```bash
adb devices -l                       # list
adb start-server                     # adb kill-server to stop
adb kill-server && adb start-server  # restart the server
adb -s SERIAL tcpip 5555             # Wi-Fi: over USB first
adb connect <ip>:5555
adb -s SERIAL shell ip route | grep src   # device IP
```

## State

```bash
adb -s SERIAL shell wm size
adb -s SERIAL shell wm density            # wm density 320 / wm density reset
adb -s SERIAL shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
adb -s SERIAL shell getprop ro.build.version.sdk
```

## App

```bash
adb -s SERIAL shell pm list packages | grep <package>
adb -s SERIAL shell cmd package resolve-activity --brief -c android.intent.category.LAUNCHER <package>
adb -s SERIAL shell am start -W -n <package>/<activity>
adb -s SERIAL shell am start -W -a android.intent.action.VIEW -d "<scheme://path>"   # deep link
adb -s SERIAL shell am force-stop <package>
adb -s SERIAL shell pm clear <package>
adb -s SERIAL uninstall <package>
```

On API 35 emulators `monkey -p <package> 1` prints `SYS_KEYS has no physical keys`
and does not start the app. That is why `adbm launch` uses `am start`.

## Input

```bash
adb -s SERIAL shell input tap X Y
adb -s SERIAL shell input tap X Y && sleep 0.1 && adb -s SERIAL shell input tap X Y   # double tap
adb -s SERIAL shell input swipe X Y X Y 3000             # long press
adb -s SERIAL shell input swipe X1 Y1 X2 Y2 300
adb -s SERIAL shell input keyevent KEYCODE_BACK          # HOME, ENTER, DEL, TAB, ESCAPE, MENU, APP_SWITCH
adb -s SERIAL shell input keyevent KEYCODE_VOLUME_UP     # VOLUME_DOWN, POWER
adb -s SERIAL shell input text "hello%sworld"            # ASCII only, space is %s
```

`input text` cannot type non-Latin text. In a flow use Maestro `inputText`, by hand —
`adbm type --unicode` (see `SKILL.md`, "Limitations").

Go to the home screen: `adbm key home`. To walk back through the stack,
press back until the launcher has focus:

```bash
HOME_PKG=$(adb -s SERIAL shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME | tail -1 | cut -d/ -f1)
for i in $(seq 1 20); do
  adb -s SERIAL shell dumpsys window | grep mCurrentFocus | grep -q "$HOME_PKG" && break
  adb -s SERIAL shell input keyevent KEYCODE_BACK; sleep 0.5
done
```

## Frames and tree

```bash
adb -s SERIAL exec-out screencap -p > shot.png
adb -s SERIAL exec-out sh -c 'uiautomator dump /sdcard/d.xml >/dev/null; cat /sdcard/d.xml' > d.xml
adb -s SERIAL shell screenrecord --time-limit 5 /sdcard/r.mp4 && adb -s SERIAL pull /sdcard/r.mp4
```

Do not read the frame or the XML into the context. Use `adbm ui` for the tree and `adbm look` for a frame.

## Logs

```bash
adb -s SERIAL logcat -b crash -d -t 50
adb -s SERIAL logcat --pid=$(adb -s SERIAL shell pidof <package>) -d -t 100
adb -s SERIAL logcat -s "TAG:*" -d -t 30
```

## Display settings

```bash
adb -s SERIAL shell cmd uimode night yes|no|auto
adb -s SERIAL shell settings put system font_scale 1.3     # 0.85, 1.0, 1.15, 1.3, even 2.0
adb -s SERIAL shell settings put global animator_duration_scale 0   # and window_, transition_
adb -s SERIAL shell cmd overlay enable-exclusive --category com.android.internal.systemui.navbar.gestural   # API 29+
adb -s SERIAL shell settings put secure high_text_contrast_enabled 1
adb -s SERIAL shell settings put secure accessibility_display_inversion_enabled 1
adb -s SERIAL shell settings put secure enabled_accessibility_services \
  com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService
```

## adb failures

| Failure | What to do |
|---|---|
| `device unauthorized` | confirm the dialog on the device, then `adb kill-server && adb start-server` |
| `device offline` | `adb reconnect`, reconnect the cable |
| `more than one device` | add `-s SERIAL` |
| `uiautomator dump` prints `could not get idle state` | an animation is running: `adbm prep`, then retry |
| a command hangs | `timeout 10 adb …` |
