# Maestro flows для adbm

Maestro — открытый инструмент UI-тестов. Сценарий — YAML-файл с шагами.
Maestro ищет элементы по дереву доступности и сам ждёт их появления.
Во время прогона LLM не участвует, поэтому прогон одинаков на всех API.

Документация команд: https://docs.maestro.dev/api-reference/commands

## Где лежат

`<проект>/.adbm/flows/<slug>.yaml` — в git проекта. Прогоны (`build/adbm/`) в git не идут.

## Порядок

1. Разведай экран: `adbm ui --api 35`, `adbm ui --find "<текст>"`.
2. Напиши flow по правилам ниже.
3. Прогони на одном API: `adbm run .adbm/flows/<slug>.yaml --api 35`.
4. Если сбой — прочитай строку причины и `logs/ui-fail-*.txt`, исправь flow, повтори.
5. Прогони на всех выбранных API: `adbm run … --api 28,33,35 --matrix "nav=…" "theme=…"`.

## Правила

- **Селекторы** берутся из `adbm ui`: `text`, `id`, `accessibilityText`.
  Текст в `tapOn` — регулярное выражение: `"(Display|Экран).*"` покрывает две локали.
  Точки, скобки и `+` в тексте экранируй: `"Цена \\(руб\\.\\)"`.
- **Координаты** — только в процентах и с комментарием, почему без селектора:
  ```yaml
  # у кнопки нет текста и id, её рисует Canvas
  - tapOn:
      point: "50%,90%"
  ```
- **Ожидания** — `extendedWaitUntil` или `assertVisible`, без `sleep`.
  Перед каждым `takeScreenshot` ставь `waitForAnimationToEnd`.
- **Состояние** — flow начинается с `launchApp: {clearState: true}`. Исключение — системные
  приложения вроде «Настроек»: их данные не чистим, поэтому `stopApp` + `launchApp`.
  Тему, навигацию, шрифт и demo mode во flow не ставь: их ставит `adbm prep` по `--matrix`.
- **Имена кадров** — `takeScreenshot: "<N>-<состояние>"`, например `"3-sheet-expanded"`.
  API, «до/после» и ячейку матрицы в имя не пиши: `adbm` раскладывает кадры по папкам сам.
- **Один flow — одна проверка.** Темы и навигация задаются флагом `--matrix`, не копией файла.
- **Прокрутка к элементу** — `scrollUntilVisible`, затем `tapOn`.
- **Кириллица в поле** — `inputText: "Привет"`. `adbm type` кириллицу не умеет.

## Шаблон

```yaml
appId: com.example.app
---
- launchApp:
    clearState: true
- extendedWaitUntil:
    visible: "Каталог"
    timeout: 10000
- tapOn: "Каталог"
- scrollUntilVisible:
    element:
      id: "item_42"
    direction: DOWN
- tapOn:
    id: "item_42"
- waitForAnimationToEnd
- takeScreenshot: "1-item-details"
- tapOn: "Открыть штору"
- waitForAnimationToEnd
- takeScreenshot: "2-sheet-peek"
```

Переменные: `adbm run flow.yaml -e USER=test` → во flow `${USER}`.

## Из ручной сессии

Каждое `adbm launch`, `tap`, `type`, `key`, `swipe`, `shot` пишется в `build/adbm/session.jsonl`.
`adbm save-flow <slug> --api 35` собирает flow от последнего `launch`:
- `launch --clear` превращается в `clearState: true`, без `--clear` — в `false`;
- текст селектора экранируется как регулярное выражение;
- `tap --scroll N` превращается в `scrollUntilVisible` + `tapOn`;
- тап по координатам — в `point` в процентах с пометкой `TODO`.

После `save-flow` прогони flow один раз и поправь селекторы.

## Сбой

`adbm run` печатает одну строку на ячейку: причину из Maestro и путь к логу.
Рядом лежат `logs/ui-fail-<ячейка>.txt` — дерево экрана в момент сбоя,
и `logs/crash-<ячейка>.txt`, если приложение упало (`logcat -b crash`).
Чини flow по этим файлам. Скриншот сбоя не открывай, если дерево отвечает на вопрос.

## Защита от скриншотов

Если окно приложения с `FLAG_SECURE`, Maestro на одних API падает с `Screenshot returned null`,
а на других молча отдаёт чёрный кадр. `adbm run` отбрасывает пустые кадры, а ячейку
с чёрными кадрами помечает сбоем с подсказкой. Лечение — выключить защиту первыми шагами flow:

```yaml
# приложение по умолчанию ставит FLAG_SECURE
- tapOn: "Настройки"
- tapOn: "Безопасность"
- tapOn: "Защита скриншотов"
- back
- back
```

Переключатели Compose идут в дереве без текста. `adbm ui` показывает их с подписью строки:
`[22] View near="Запрет на скриншоты…" @958,1616 click,check`. Тапай по тексту строки.

## Параллель

`adbm run --api 28,33,35` запускает отдельный процесс `maestro --device <serial> test`
на каждое устройство. Проверено 15.10.2026: три эмулятора идут ~18 с, по отдельности было бы ~49 с (13 + 20 + 16),
кадры не путаются. `maestro --shard-all` не используем: на одном устройстве он упал,
а папки называет `flow-shard-N` без привязки к устройству.
