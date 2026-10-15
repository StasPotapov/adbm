# Сырой adb — когда `adbm` не хватает

Справочник для редких действий. Обычную работу делай через `adbm`: команды ниже
не пишут журнал для `save-flow` и не раскладывают кадры по прогону.

Если подключено больше одного устройства, всегда пиши `adb -s <serial>`.
Serial по API даёт `adbm devices`. Serial эмулятора меняется между запусками.

## Устройства и сервер

```bash
adb devices -l                       # список
adb start-server                     # adb kill-server — остановить
adb kill-server && adb start-server  # перезапуск сервера
adb -s SERIAL tcpip 5555             # Wi-Fi: сначала по USB
adb connect <ip>:5555
adb -s SERIAL shell ip route | grep src   # IP устройства
```

## Состояние

```bash
adb -s SERIAL shell wm size
adb -s SERIAL shell wm density            # wm density 320 / wm density reset
adb -s SERIAL shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'
adb -s SERIAL shell getprop ro.build.version.sdk
```

## Приложение

```bash
adb -s SERIAL shell pm list packages | grep <package>
adb -s SERIAL shell cmd package resolve-activity --brief -c android.intent.category.LAUNCHER <package>
adb -s SERIAL shell am start -W -n <package>/<activity>
adb -s SERIAL shell am start -W -a android.intent.action.VIEW -d "<scheme://path>"   # deep link
adb -s SERIAL shell am force-stop <package>
adb -s SERIAL shell pm clear <package>
adb -s SERIAL uninstall <package>
```

`monkey -p <package> 1` на эмуляторах API 35 печатает `SYS_KEYS has no physical keys`
и приложение не запускает. Поэтому `adbm launch` запускает через `am start`.

## Ввод

```bash
adb -s SERIAL shell input tap X Y
adb -s SERIAL shell input tap X Y && sleep 0.1 && adb -s SERIAL shell input tap X Y   # двойной тап
adb -s SERIAL shell input swipe X Y X Y 3000             # долгое нажатие
adb -s SERIAL shell input swipe X1 Y1 X2 Y2 300
adb -s SERIAL shell input keyevent KEYCODE_BACK          # HOME, ENTER, DEL, TAB, ESCAPE, MENU, APP_SWITCH
adb -s SERIAL shell input keyevent KEYCODE_VOLUME_UP     # VOLUME_DOWN, POWER
adb -s SERIAL shell input text "hello%sworld"            # только ASCII, пробел — %s
```

Кириллицу `input text` не вводит. Есть два способа:
- во flow — Maestro `inputText`;
- руками — ADB Keyboard, если он стоит:
  `ime set com.android.adbkeyboard/.AdbIME`, затем
  `am broadcast -a ADB_INPUT_B64 --es msg "$(echo -n 'текст' | base64)"`;
  очистить поле — `am broadcast -a ADB_CLEAR_TEXT`.

Вернуться на главный экран: `adbm key home`. Если нужно пройти назад по стеку,
жми «назад», пока в фокусе не окажется лаунчер:

```bash
HOME_PKG=$(adb -s SERIAL shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME | tail -1 | cut -d/ -f1)
for i in $(seq 1 20); do
  adb -s SERIAL shell dumpsys window | grep mCurrentFocus | grep -q "$HOME_PKG" && break
  adb -s SERIAL shell input keyevent KEYCODE_BACK; sleep 0.5
done
```

## Кадры и дерево

```bash
adb -s SERIAL exec-out screencap -p > shot.png
adb -s SERIAL exec-out sh -c 'uiautomator dump /sdcard/d.xml >/dev/null; cat /sdcard/d.xml' > d.xml
adb -s SERIAL shell screenrecord --time-limit 5 /sdcard/r.mp4 && adb -s SERIAL pull /sdcard/r.mp4
```

Кадр и XML не читай в контекст. Для дерева есть `adbm ui`, для кадра — `adbm look`.

## Логи

```bash
adb -s SERIAL logcat -b crash -d -t 50
adb -s SERIAL logcat --pid=$(adb -s SERIAL shell pidof <package>) -d -t 100
adb -s SERIAL logcat -s "TAG:*" -d -t 30
```

## Настройки экрана

```bash
adb -s SERIAL shell cmd uimode night yes|no|auto
adb -s SERIAL shell settings put system font_scale 1.3     # 0.85, 1.0, 1.15, 1.3, можно 2.0
adb -s SERIAL shell settings put global animator_duration_scale 0   # и window_, transition_
adb -s SERIAL shell cmd overlay enable-exclusive --category com.android.internal.systemui.navbar.gestural   # API 29+
adb -s SERIAL shell settings put secure high_text_contrast_enabled 1
adb -s SERIAL shell settings put secure accessibility_display_inversion_enabled 1
adb -s SERIAL shell settings put secure enabled_accessibility_services \
  com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService
```

## Сбои adb

| Сбой | Что делать |
|---|---|
| `device unauthorized` | подтвердить диалог на устройстве, затем `adb kill-server && adb start-server` |
| `device offline` | `adb reconnect`, переподключить кабель |
| `more than one device` | добавить `-s SERIAL` |
| `uiautomator dump` пишет `could not get idle state` | на экране идёт анимация: `adbm prep`, затем повтор |
| команда висит | `timeout 10 adb …` |
