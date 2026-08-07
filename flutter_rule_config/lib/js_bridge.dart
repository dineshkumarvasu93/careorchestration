import 'dart:js_interop';

/// Interop bridge that hands the composed ruleset back to the host HTML page.
///
/// The Flutter drag-and-drop UI runs inside an `<iframe>` embedded in the
/// static HTML dashboard. Whenever the ruleset changes we post a message to the
/// parent window; the HTML page listens for it and uses the values when it
/// builds the publish payload. Nothing is sent to the backend from here — the
/// HTML page owns all API calls.

extension type _Window(JSObject _) implements JSObject {
  external _Window get parent;
  external void postMessage(JSAny message, JSString targetOrigin);
}

@JS('window')
external _Window get _window;

/// Post the current ruleset to the host page.
///
/// Message shape: `{ type: 'ruleset', known_gap_ids: [...], include_high_risk_plan: bool }`.
void postRuleset(List<String> knownGapIds, bool includeHighRiskPlan) {
  final Map<String, Object?> message = <String, Object?>{
    'type': 'ruleset',
    'known_gap_ids': knownGapIds,
    'include_high_risk_plan': includeHighRiskPlan,
  };

  final JSAny? jsMessage = message.jsify();
  if (jsMessage == null) {
    return;
  }

  try {
    // '*' target origin is fine for local development. Tighten to the exact
    // dashboard origin if this is ever deployed somewhere real.
    _window.parent.postMessage(jsMessage, '*'.toJS);
  } catch (_) {
    // No parent window (e.g. running standalone via `flutter run`). Ignore.
  }
}
