import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../core/theme/app_theme.dart';

class PasscodePad extends StatefulWidget {
  final int length;
  final String? subtitle;
  final String? errorText;
  final void Function(String code) onComplete;
  final bool isLoading;

  const PasscodePad({
    super.key,
    required this.length,
    this.subtitle,
    this.errorText,
    required this.onComplete,
    this.isLoading = false,
  });

  @override
  State<PasscodePad> createState() => _PasscodePadState();
}

class _PasscodePadState extends State<PasscodePad> with SingleTickerProviderStateMixin {
  String _entered = '';
  late final AnimationController _shakeCtrl;
  late final Animation<double> _shake;

  @override
  void initState() {
    super.initState();
    _shakeCtrl = AnimationController(vsync: this, duration: const Duration(milliseconds: 400));
    _shake = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 10.0), weight: 1),
      TweenSequenceItem(tween: Tween(begin: 10.0, end: -10.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: -10.0, end: 5.0), weight: 2),
      TweenSequenceItem(tween: Tween(begin: 5.0, end: 0.0), weight: 1),
    ]).animate(CurvedAnimation(parent: _shakeCtrl, curve: Curves.easeInOut));
  }

  @override
  void didUpdateWidget(covariant PasscodePad old) {
    super.didUpdateWidget(old);
    if (widget.errorText != null && old.errorText == null) {
      _shakeCtrl.forward(from: 0);
      HapticFeedback.heavyImpact();
      Future.delayed(const Duration(milliseconds: 400), () {
        if (mounted) setState(() => _entered = '');
      });
    }
  }

  void _tap(String d) {
    if (_entered.length >= widget.length || widget.isLoading) return;
    HapticFeedback.selectionClick();
    setState(() => _entered += d);
    if (_entered.length == widget.length) {
      widget.onComplete(_entered);
    }
  }

  void _delete() {
    if (_entered.isEmpty || widget.isLoading) return;
    HapticFeedback.lightImpact();
    setState(() => _entered = _entered.substring(0, _entered.length - 1));
  }

  Widget _buildKey(String label, {VoidCallback? onTap, bool isIcon = false}) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 76,
        height: 76,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AppTheme.white,
          border: Border.all(color: AppTheme.border, width: 1),
        ),
        child: Center(
          child: isIcon
              ? const Icon(Icons.backspace_outlined, color: AppTheme.black, size: 26)
              : Text(
                  label,
                  style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w500, color: AppTheme.black, fontFamily: 'monospace'),
                ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool hasError = widget.errorText != null;
    final Color dotColor = hasError ? AppTheme.error : AppTheme.accent;
    final Color emptyDotBorder = hasError ? AppTheme.error : AppTheme.border;

    return Column(
      children: [
        if (widget.subtitle != null) ...[
          Text(widget.subtitle!, style: const TextStyle(fontSize: 13, color: AppTheme.gray)),
          const SizedBox(height: 40),
        ],
        AnimatedBuilder(
          animation: _shake,
          builder: (context, child) => Transform.translate(offset: Offset(_shake.value, 0), child: child),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(widget.length, (i) {
              final filled = i < _entered.length;
              return AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.symmetric(horizontal: 12),
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: filled ? dotColor : Colors.transparent,
                  border: Border.all(color: filled ? dotColor : emptyDotBorder, width: 2),
                ),
              );
            }),
          ),
        ),
        const SizedBox(height: 24),
        
        // NEW: Show a loading spinner while waiting for the backend!
        SizedBox(
          height: 24,
          child: widget.isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.accent),
                )
              : AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: widget.errorText != null
                      ? Text(
                          widget.errorText!,
                          key: const ValueKey('error'),
                          style: const TextStyle(color: AppTheme.error, fontSize: 14, fontWeight: FontWeight.w600),
                        )
                      : const SizedBox.shrink(),
                ),
        ),
        
        const SizedBox(height: 32),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _buildKey('1', onTap: () => _tap('1')), const SizedBox(width: 24),
          _buildKey('2', onTap: () => _tap('2')), const SizedBox(width: 24),
          _buildKey('3', onTap: () => _tap('3')),
        ]),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _buildKey('4', onTap: () => _tap('4')), const SizedBox(width: 24),
          _buildKey('5', onTap: () => _tap('5')), const SizedBox(width: 24),
          _buildKey('6', onTap: () => _tap('6')),
        ]),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _buildKey('7', onTap: () => _tap('7')), const SizedBox(width: 24),
          _buildKey('8', onTap: () => _tap('8')), const SizedBox(width: 24),
          _buildKey('9', onTap: () => _tap('9')),
        ]),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          const SizedBox(width: 76), const SizedBox(width: 24),
          _buildKey('0', onTap: () => _tap('0')), const SizedBox(width: 24),
          _buildKey('', onTap: _delete, isIcon: true),
        ]),
      ],
    );
  }
}
