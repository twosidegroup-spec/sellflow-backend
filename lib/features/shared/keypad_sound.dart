import 'keypad_sound_stub.dart'
    if (dart.library.js_interop) 'keypad_sound_web.dart' as impl;

/// Professional keypad feedback sounds.
///
/// - Web: plays the bundled WAV ticks through HTML audio.
/// - Android / iOS: uses the native keyboard click (system "tap" sound).
///
/// All calls are fire-and-forget and never throw, so tapping the keypad
/// can't break the auth flow on any platform.
class KeypadSound {
  KeypadSound._();

  static bool enabled = true;

  /// Preloads the sounds so the first tap is instant.
  static void prime() {
    try {
      impl.prime();
    } catch (_) {}
  }

  /// Digit key tap.
  static void tap() {
    if (!enabled) return;
    try {
      impl.tap();
    } catch (_) {}
  }

  /// Backspace / delete key.
  static void delete() {
    if (!enabled) return;
    try {
      impl.delete();
    } catch (_) {}
  }

  /// PIN accepted.
  static void success() {
    if (!enabled) return;
    try {
      impl.success();
    } catch (_) {}
  }
}
