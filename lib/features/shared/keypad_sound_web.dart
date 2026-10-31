import 'package:web/web.dart' as web;

/// Web: play the bundled WAV key ticks through preloaded HTML audio
/// elements so there is no latency between taps.
final Map<String, web.HTMLAudioElement> _players = {};
bool _ready = false;

void prime() {
  if (_ready) return;
  _ready = true;
  try {
    for (final name in const ['key_tap', 'key_delete', 'key_success']) {
      final element =
          web.document.createElement('audio') as web.HTMLAudioElement;
      element.src = 'assets/assets/sounds/$name.wav';
      element.preload = 'auto';
      element.volume = name == 'key_success' ? 0.4 : 0.32;
      element.load();
      _players[name] = element;
    }
  } catch (_) {}
}

void _play(String name) {
  prime();
  final element = _players[name];
  if (element == null) return;
  try {
    element.currentTime = 0;
    element.play();
  } catch (_) {}
}

void tap() => _play('key_tap');

void delete() => _play('key_delete');

void success() => _play('key_success');
