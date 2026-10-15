# Похожие инструменты

[English](alternatives.md) · [README](../README.ru.md)

Ниже — инструменты, которые закрывают часть задач ADBM. Сравнение по состоянию на октябрь 2026 года,
по README и документации проектов.

## Агент управляет устройством

Эти инструменты дают агенту нажатия, ввод, дерево UI, скриншоты и логи. Здесь ADBM дублирует готовое.

- [mobile-mcp](https://github.com/mobile-next/mobile-mcp) — MCP-сервер для Android и iOS, ~9,5 тыс. звёзд.
  Работает в первую очередь через дерево доступности, к скриншотам переходит, только когда без них нельзя.
  Параллельной работы с несколькими устройствами и сравнения кадров в README нет.
- [Maestro MCP](https://docs.maestro.dev/get-started/maestro-mcp) встроен в CLI Maestro: устройства, экран,
  запуск flow, скриншоты. Работает с Claude Code, Codex, Cursor и другими агентами.
- [Android CLI](https://developer.android.com/tools/agents/android-cli) от Google, версия 1.0 с мая 2026 года.
  Бинарник закрытый, телеметрия включена по умолчанию. ADBM использует его только для `annotate`.
- Скиллы и MCP поменьше: [android-adb-skill](https://github.com/amit-nayar/android-adb-skill),
  [claude-adb-skill](https://github.com/pengdev/claude-adb-skill),
  [android-testing-skills](https://github.com/skydoves/android-testing-skills),
  [DroidMind](https://archestra.ai/mcp-catalog/hyperb1iss__droidmind),
  [android-mcp](https://github.com/remymazmanian/android-mcp).

Своё у ADBM здесь только в мелочах: `tap` печатает, что изменилось на экране, а `ui` сжимает дерево.

## Тест на естественном языке

Человек описывает сценарий словами, модель сама решает, куда нажать.

- [Journeys](https://developer.android.com/tools/agents/android-cli/journeys) в Android CLI.
- [App Testing agent](https://firebase.google.com/docs/app-distribution/android/app-testing-agent) в Firebase, на Gemini.
- [android-qa-agent](https://github.com/tobrun/android-qa-agent) записывает действия Claude и воспроизводит их,
  но работает с одним устройством.

Модель проходит такой сценарий заново при каждом прогоне, поэтому шаги могут отличаться. У ADBM сценарий
задаёт Maestro flow: он одинаковый во всех ячейках матрицы, поэтому кадры можно сравнивать по пикселям.

## Визуальная регрессия

- [Maestro `assertScreenshot`](https://docs.maestro.dev/reference/commands-available/assertscreenshot)
  (CLI 2.2.0, март 2026 года) сравнивает экран с эталонной картинкой по порогу, по умолчанию 95%.
  Это самый близкий инструмент. Эталоны нужно снимать и хранить.
- [Emerge / Sentry Snapshots](https://docs.emergetools.com/docs/android-snapshots-v1) сравнивают снимки
  сборки PR со снимками базовой сборки. Снимки строятся из `@Preview`, а не с живого приложения. Сервис облачный.
- Roborazzi, Paparazzi, Shot требуют код тестов и эталоны в git.
- Percy и Applitools облачные и платные.

## Чем отличается ADBM

Целиком такую связку мы не нашли ни у одного инструмента:

- **Две сборки на одном сценарии.** Эталоны, тесты и `@Preview` не нужны.
- **Матрица** API × тема × навигация × шрифт параллельно на эмуляторах. `prep` выключает анимации и включает demo mode.
- **Дифф без модели.** Статус-бар сравнивается отдельно, `≈ apiN` отмечает то же изменение на другом API.
- **Дешёвый вердикт.** Субагент пишет вердикт по чек-листу задачи, главный агент получает текст без картинок.
- **Замер токенов:** `stats.json`, `tools/measure-session.py` и хук-ограждение.

## Чем ADBM слабее

- Только Android. mobile-mcp и Maestro работают и с iOS.
- Субагент и хук работают только в Claude Code. Maestro MCP и Android CLI подходят любому агенту.
- Нет CI-режима и облака устройств, только локальные эмуляторы.
- Проверен на macOS и на небольшом числе приложений.
