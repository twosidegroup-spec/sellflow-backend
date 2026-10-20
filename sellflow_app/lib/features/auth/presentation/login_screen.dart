import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/logo_placeholder.dart';
import 'auth_controller.dart';
import 'passcode_pad.dart';
import 'register_screen.dart';
import 'forgot_passcode_screen.dart';

class LoginScreen extends ConsumerWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(authControllerProvider);
    final busy = state.status == AuthStatus.working;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView( // CHANGED: Now scrollable to prevent overflow
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            children: [
              const SizedBox(height: 60),
              const LogoPlaceholder(height: 40),
              const SizedBox(height: 40),
              const Text('Welcome back', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600, color: AppTheme.black, letterSpacing: -0.5)),
              const SizedBox(height: 8),
              Text(
                state.email ?? 'Enter your 4-digit passcode',
                style: const TextStyle(fontSize: 13, color: AppTheme.gray),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              PasscodePad(
                length: 4,
                subtitle: null,
                errorText: busy ? null : state.error,
                isLoading: busy,
                onComplete: (code) {
                  if (!busy) ref.read(authControllerProvider.notifier).unlock(code);
                },
              ),
              const SizedBox(height: 40), // Replaced Spacer with fixed height
              TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ForgotPasscodeScreen())),
                child: const Text('Forgot passcode?'),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const RegisterScreen())),
                child: const Text.rich(
                  TextSpan(
                    text: 'New to SellFlow? ',
                    style: TextStyle(color: AppTheme.gray, fontWeight: FontWeight.w400),
                    children: [TextSpan(text: 'Create account', style: TextStyle(color: AppTheme.black, fontWeight: FontWeight.w600, decoration: TextDecoration.underline))],
                  ),
                ),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
