import 'package:flutter/material.dart';

/// SELLFLOW brand lockup used on the app screens.
class SFMLogo extends StatelessWidget {
  final double markSize;
  final bool dark;
  final bool showTagline;
  final bool horizontal;
  final String tagline;

  const SFMLogo({
    super.key,
    this.markSize = 52,
    this.dark = true,
    this.showTagline = true,
    this.horizontal = false,
    this.tagline = 'Manage · Grow · Succeed',
  });

  Widget _mark() {
    return Container(
      width: markSize,
      height: markSize,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF7DD3FC), Color(0xFF2563EB)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(markSize * 0.3),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF2563EB).withOpacity(0.35),
            blurRadius: 18,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Center(
        child: Text(
          'S',
          style: TextStyle(
            color: Colors.white,
            fontSize: markSize * 0.5,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }

  Widget _wordmark() {
    return Text(
      'SELLFLOW',
      style: TextStyle(
        fontSize: horizontal ? markSize * 0.60 : markSize * 0.42,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.2,
        color: dark ? Colors.white : const Color(0xFF12203A),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (horizontal) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _mark(),
          SizedBox(width: markSize * 0.28),
          _wordmark(),
        ],
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        _mark(),
        SizedBox(height: markSize * 0.22),
        _wordmark(),
        if (showTagline) ...[
          const SizedBox(height: 6),
          Text(
            tagline,
            style: TextStyle(
              fontSize: 11,
              letterSpacing: 2.2,
              fontWeight: FontWeight.w500,
              color: dark ? Colors.white54 : const Color(0xFF64748B),
            ),
          ),
        ],
      ],
    );
  }
}
