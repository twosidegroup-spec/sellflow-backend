import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../shared/keypad_sound.dart';

/// Small circular PIN progress indicators shown above the keypad.
class PasscodeIndicators extends StatelessWidget {
  final int filled;
  final int length;
  final bool isSuccess;
  final bool isError;
  final bool dark;

  const PasscodeIndicators({
    super.key,
    required this.filled,
    this.length = 4,
    this.isSuccess = false,
    this.isError = false,
    this.dark = true,
  });

  @override
  Widget build(BuildContext context) {
    final activeColor = isSuccess
        ? const Color(0xFF10B981)
        : isError
            ? const Color(0xFFEF4444)
            : (dark ? Colors.white : const Color(0xFF3B82F6));
    final idleColor =
        dark ? Colors.white24 : const Color(0xFFC6D8EC);

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(length, (index) {
        final isFilled = index < filled;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          width: 12,
          height: 12,
          margin: const EdgeInsets.symmetric(horizontal: 9),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isFilled ? activeColor : Colors.transparent,
            border: Border.all(
              color: isFilled ? activeColor : idleColor,
              width: 1.6,
            ),
            boxShadow: isFilled && !isError && !isSuccess
                ? [
                    BoxShadow(
                      color: activeColor.withOpacity(0.35),
                      blurRadius: 8,
                    ),
                  ]
                : null,
          ),
        );
      }),
    );
  }
}

/// Rounded-square passcode keypad shared by the auth screens.
class PasscodeKeypad extends StatelessWidget {
  final ValueChanged<String> onDigit;
  final VoidCallback onBackspace;
  final bool enabled;
  final bool dark;

  const PasscodeKeypad({
    super.key,
    required this.onDigit,
    required this.onBackspace,
    this.enabled = true,
    this.dark = true,
  });

  static const List<List<String>> _rows = [
    ['1', '2', '3'],
    ['4', '5', '6'],
    ['7', '8', '9'],
    ['', '0', 'back'],
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      children: _rows.map((row) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: row.map((label) {
              // Keep the empty slot exactly as wide as a key cell so all
              // three columns line up perfectly.
              if (label.isEmpty) {
                return const SizedBox(width: 80, height: 64);
              }
              final isBack = label == 'back';
              final digitColor = dark
                  ? (enabled ? Colors.white : Colors.white24)
                  : (enabled
                      ? const Color(0xFF1E293B)
                      : const Color(0xFFB0C0D4));
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: _KeyButton(
                  dark: dark,
                  enabled: enabled,
                  onTap: () {
                    if (isBack) {
                      KeypadSound.delete();
                      onBackspace();
                    } else {
                      KeypadSound.tap();
                      onDigit(label);
                    }
                  },
                  child: isBack
                      ? Icon(
                          LucideIcons.delete,
                          size: 20,
                          color: digitColor,
                        )
                      : Text(
                          label,
                          style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w600,
                            color: digitColor,
                          ),
                        ),
                ),
              );
            }).toList(),
          ),
        );
      }).toList(),
    );
  }
}

class _KeyButton extends StatelessWidget {
  final bool dark;
  final bool enabled;
  final VoidCallback onTap;
  final Widget child;

  const _KeyButton({
    required this.dark,
    required this.enabled,
    required this.onTap,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 64,
      height: 64,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: dark
            ? Colors.white.withOpacity(enabled ? 0.07 : 0.03)
            : Colors.white.withOpacity(enabled ? 1 : 0.6),
        border: dark
            ? null
            : Border.all(color: const Color(0xFFE2EBF5), width: 1),
        boxShadow: dark
            ? null
            : [
                BoxShadow(
                  color: const Color(0xFF7FB0DE).withOpacity(0.22),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
      ),
      child: Material(
        color: Colors.transparent,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: enabled ? onTap : null,
          child: Center(child: child),
        ),
      ),
    );
  }
}

/// Smooth fade + slide-up transition used between the auth screens.
class FadeSlideRoute<T> extends PageRouteBuilder<T> {
  FadeSlideRoute({required WidgetBuilder builder})
      : super(
          transitionDuration: const Duration(milliseconds: 300),
          reverseTransitionDuration: const Duration(milliseconds: 240),
          pageBuilder: (context, animation, secondaryAnimation) =>
              builder(context),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            final curved = CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutCubic,
            );
            return FadeTransition(
              opacity: curved,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.04),
                  end: Offset.zero,
                ).animate(curved),
                child: child,
              ),
            );
          },
        );
}
