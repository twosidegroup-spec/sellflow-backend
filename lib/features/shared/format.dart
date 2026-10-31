/// ৳1,234.56 style money formatting with thousands separators,
/// shared across the feature screens so figures match everywhere.
String money(double value) {
  final negative = value < 0;
  final abs = value.abs();
  final raw = abs >= 100000 ? abs.toStringAsFixed(0) : abs.toStringAsFixed(2);
  final parts = raw.split('.');
  final intPart = parts[0];
  final buffer = StringBuffer();
  for (var i = 0; i < intPart.length; i++) {
    if (i > 0 && (intPart.length - i) % 3 == 0) buffer.write(',');
    buffer.write(intPart[i]);
  }
  final formatted =
      parts.length > 1 ? '${buffer.toString()}.${parts[1]}' : buffer.toString();
  return '${negative ? '-' : ''}৳$formatted';
}
