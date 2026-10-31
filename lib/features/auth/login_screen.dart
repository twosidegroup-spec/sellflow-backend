import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/keypad_sound.dart';
import '../../theme/app_theme.dart';
import 'registration_screen.dart';
import 'widgets/iphone_frame.dart';
import 'widgets/passcode_widgets.dart';

const _ink = Color(0xFF0F172A);
const _muted = Color(0xFF64748B);
const _blue = Color(0xFF3B82F6);

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  String _pin = '';
  String? _errorMessage;
  bool _isLoading = false;
  bool _isSuccess = false;
  late AnimationController _shakeController;
  late Animation<double> _shakeAnimation;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _shakeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _shakeController, curve: Curves.elasticIn),
    );
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  Future<void> _handleAuth(String pin) async {
    if (pin.length < 4) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _isSuccess = false;
    });

    final api = context.read<ApiService>();
    final email = api.lastEmail ?? '';
    if (email.isEmpty) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'No account found. Please register first.';
        _pin = '';
      });
      return;
    }

    final success = await api.login(email, pin);

    if (!mounted) return;

    setState(() => _isLoading = false);

    if (success) {
      KeypadSound.success();
      setState(() => _isSuccess = true);
      await Future.delayed(const Duration(milliseconds: 500));
    } else {
      _shakeController.forward().then((_) {
        _shakeController.reverse();
        if (!mounted) return;
        setState(() {
          _errorMessage = 'Wrong PIN. Please try again.';
          _pin = '';
        });
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) setState(() => _errorMessage = null);
        });
      });
    }
  }

  void _handleDigit(String digit) {
    if (_isLoading || _isSuccess) return;
    setState(() {
      if (_pin.length < 4) {
        _pin += digit;
        _errorMessage = null;
      }
    });
    if (_pin.length == 4) {
      Future.delayed(const Duration(milliseconds: 150), () {
        if (mounted) _handleAuth(_pin);
      });
    }
  }

  void _handleBackspace() {
    if (_isLoading || _isSuccess) return;
    setState(() {
      if (_pin.isNotEmpty) {
        _pin = _pin.substring(0, _pin.length - 1);
      }
      _errorMessage = null;
    });
  }

  void _showForgotPin() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: Colors.white,
        title: const Text(
          'Forgot PIN?',
          style: TextStyle(color: _ink, fontSize: 16),
        ),
        content: const Text(
          'For security, PIN resets are handled by support. '
          'Please contact support@sellflow.app to recover your account.',
          style: TextStyle(color: _muted, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IPhoneFrame(
      child: Scaffold(
        backgroundColor: Colors.white,
        body: Stack(
          fit: StackFit.expand,
          children: [
            // Light blue artwork background
            Positioned.fill(
              child: Image.asset(
                'assets/images/login_bg.png',
                fit: BoxFit.cover,
                alignment: Alignment.topCenter,
              ),
            ),
            SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  children: [
                    const Spacer(flex: 3),

                    // Welcome Back
                    Text.rich(
                      TextSpan(
                        text: 'Welcome ',
                        style: const TextStyle(
                          fontSize: AppText.pageHeading,
                          fontWeight: FontWeight.w700,
                          color: _ink,
                        ),
                        children: const [
                          TextSpan(
                            text: 'Back',
                            style: TextStyle(color: _blue),
                          ),
                        ],
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Enter your 4-digit PIN to continue',
                      style: TextStyle(
                        fontSize: AppText.body,
                        fontWeight: FontWeight.w400,
                        color: _muted,
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Small PIN circles
                    AnimatedBuilder(
                      animation: _shakeAnimation,
                      builder: (context, child) {
                        double offset = _shakeAnimation.value * 12;
                        if (_shakeAnimation.value > 0.5) {
                          offset = (1 - _shakeAnimation.value) * 12;
                        }
                        return Transform.translate(
                          offset: Offset(offset, 0),
                          child: child,
                        );
                      },
                      child: PasscodeIndicators(
                        filled: _pin.length,
                        isSuccess: _isSuccess,
                        isError: _errorMessage != null,
                        dark: false,
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      height: 18,
                      child: _errorMessage != null
                          ? Text(
                              _errorMessage!,
                              style: const TextStyle(
                                color: Color(0xFFEF4444),
                                fontSize: 12.5,
                              ),
                            )
                          : null,
                    ),
                    const SizedBox(height: 8),

                    // Rounded-square keypad
                    PasscodeKeypad(
                      dark: false,
                      enabled: !(_isLoading || _isSuccess),
                      onDigit: _handleDigit,
                      onBackspace: _handleBackspace,
                    ),
                    const SizedBox(height: 6),
                    TextButton(
                      onPressed: _showForgotPin,
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            'Forget PIN?',
                            style: TextStyle(
                              color: _blue,
                              fontSize: AppText.body,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          SizedBox(width: 2),
                          Icon(LucideIcons.chevronRight,
                              size: 17, color: _blue),
                        ],
                      ),
                    ),

                    const Spacer(flex: 2),

                    // Register
                    GestureDetector(
                      onTap: () {
                        Navigator.push(
                          context,
                          FadeSlideRoute(
                            builder: (context) => const RegistrationScreen(),
                          ),
                        );
                      },
                      child: RichText(
                        text: const TextSpan(
                          text: "Don't have an account? ",
                          style: TextStyle(
                            color: _muted,
                            fontSize: AppText.label,
                            fontWeight: FontWeight.w400,
                          ),
                          children: [
                            TextSpan(
                              text: 'Register',
                              style: TextStyle(
                                color: _blue,
                                fontSize: AppText.label,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        Icon(LucideIcons.lock, size: 13, color: _muted),
                        SizedBox(width: 6),
                        Text(
                          'Your information is secure',
                          style: TextStyle(
                            color: _muted,
                            fontSize: AppText.label,
                            fontWeight: FontWeight.w400,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Powered by TSGI',
                      style: TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 10,
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 26),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
