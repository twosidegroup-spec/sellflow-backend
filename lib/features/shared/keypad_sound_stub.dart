import 'package:flutter/services.dart';

/// Native platforms (Android / iOS): use the OS keyboard click, which is
/// the exact sound users expect from a system PIN pad.
void prime() {}

void tap() {
  SystemSound.play(SystemSoundType.click).catchError((_) {});
}

void delete() {
  SystemSound.play(SystemSoundType.click).catchError((_) {});
}

void success() {
  SystemSound.play(SystemSoundType.click).catchError((_) {});
  HapticFeedback.mediumImpact().catchError((_) {});
}
