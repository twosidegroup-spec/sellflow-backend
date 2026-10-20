import 'package:flutter/material.dart';

class LogoPlaceholder extends StatelessWidget {
  final double height;
  const LogoPlaceholder({super.key, this.height = 40});

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/images/logo_full.png',
      height: height,
      fit: BoxFit.contain,
      errorBuilder: (context, error, stackTrace) {
        // Fallback: If the image isn't found, show a clean text fallback
        return Container(
          height: height,
          width: height * 2.2,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300, width: 1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Center(
            child: Text(
              'SELLFLOW',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: Colors.black, letterSpacing: 1.5),
            ),
          ),
        );
      },
    );
  }
}
