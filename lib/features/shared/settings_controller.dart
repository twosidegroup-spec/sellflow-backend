import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'keypad_sound.dart';

/// Persisted app preferences shared across screens
/// (notifications, keypad sounds and automatic payment detection).
class SettingsController extends ChangeNotifier {
  bool _notificationsEnabled = true;
  bool _paymentDetectionEnabled = false;
  bool _soundEnabled = true;

  bool get notificationsEnabled => _notificationsEnabled;
  bool get paymentDetectionEnabled => _paymentDetectionEnabled;
  bool get soundEnabled => _soundEnabled;

  Future<void> initialize() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _notificationsEnabled = prefs.getBool('settings_notifications') ?? true;
      _paymentDetectionEnabled =
          prefs.getBool('settings_payment_detection') ?? false;
      _soundEnabled = prefs.getBool('settings_sound') ?? true;
      KeypadSound.enabled = _soundEnabled;
      if (_soundEnabled) {
        KeypadSound.prime();
      }
      notifyListeners();
    } catch (_) {
      // Preferences unavailable (e.g. in tests) - keep defaults
    }
  }

  Future<void> setSound(bool value) async {
    if (_soundEnabled == value) return;
    _soundEnabled = value;
    KeypadSound.enabled = value;
    if (value) KeypadSound.prime();
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('settings_sound', value);
    } catch (_) {}
  }

  Future<void> setNotifications(bool value) async {
    if (_notificationsEnabled == value) return;
    _notificationsEnabled = value;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('settings_notifications', value);
    } catch (_) {}
  }

  Future<void> setPaymentDetection(bool value) async {
    if (_paymentDetectionEnabled == value) return;
    _paymentDetectionEnabled = value;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('settings_payment_detection', value);
    } catch (_) {}
  }
}
