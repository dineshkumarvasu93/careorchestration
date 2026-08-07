# Rule Modules — Flutter drag-and-drop island

A small Flutter (Web) module that renders **only** the drag-and-drop ruleset
builder. It is embedded into the static HTML dashboard
([../frontend/us017/rule-config-dashboard.html](../frontend/us017/rule-config-dashboard.html))
as an `<iframe>`. The rest of the page — version/description/threshold fields,
Publish, Activate, and the versions list — stays plain HTML/JS.

## How it fits together

- The HTML page owns all backend calls. This Flutter island never talks to the
  API.
- On every drag change (and once on load) the island posts its state to the
  host page with `window.parent.postMessage`:

  ```json
  { "type": "ruleset", "known_gap_ids": ["..."], "include_high_risk_plan": true }
  ```

- The HTML page listens for that message and uses the values when it builds the
  publish payload.

Interop lives in [lib/js_bridge.dart](lib/js_bridge.dart) (uses `dart:js_interop`).

## Prerequisites

- Flutter SDK (stable), Dart 3.2+ — https://docs.flutter.dev/get-started/install
  Verify with `flutter --version` and `flutter doctor`.

## Build + embed (the normal path)

From the repository root:

```powershell
./scripts/build-flutter-dnd.ps1
```

That runs `flutter build web --base-href /us017/flutter/` and copies the output
into `frontend/us017/flutter/`, where the dashboard's iframe loads it. Then open
the dashboard (served by the Docker `frontend` service or `npx http-server
frontend`).

## Standalone dev (just the island)

To iterate on the widget by itself:

```bash
flutter create . --platforms=web   # one-time: fills in web/ scaffolding
flutter pub get
flutter run -d chrome
```

Running standalone, there is no parent window, so the `postMessage` calls are
simply ignored.

## Layout

- `lib/main.dart` — app entry / theme (renders the builder full-bleed)
- `lib/models.dart` — `RuleModule` + default module catalog
- `lib/dnd_builder.dart` — the `Draggable`/`DragTarget` builder
- `lib/js_bridge.dart` — posts the ruleset to the host page
