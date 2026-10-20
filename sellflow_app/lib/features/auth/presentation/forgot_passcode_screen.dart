import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/logo_placeholder.dart';
import 'login_screen.dart';

class ForgotPasscodeScreen extends ConsumerStatefulWidget {
  const ForgotPasscodeScreen({super.key});

  @override
  ConsumerState<ForgotPasscodeScreen> createState() => _ForgotPasscodeScreenState();
}

class _ForgotPasscodeScreenState extends ConsumerState<ForgotPasscodeScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  bool _isLoading = false;
  bool _isSuccess = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() { _isLoading = true; _error = null; });
    
    // TODO: Connect to actual backend forgot password endpoint
    await Future.delayed(const Duration(seconds: 2)); // Simulated network delay
    
    setState(() { 
      _isLoading = false; 
      _isSuccess = true; 
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: IconButton(icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 16), onPressed: () => Navigator.of(context).maybePop())),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const LogoPlaceholder(height: 40),
              const SizedBox(height: 40),
              const Text('Forgot passcode?', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600, color: AppTheme.black, letterSpacing: -0.5)),
              const SizedBox(height: 8),
              const Text('Enter your email address and we will send you instructions to reset your passcode.', style: TextStyle(fontSize: 13, color: AppTheme.gray)),
              const SizedBox(height: 40),
              if (!_isSuccess) ...[
                Form(
                  key: _form,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('EMAIL ADDRESS', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.gray, letterSpacing: 0.5)),
                      const SizedBox(height: 8),
                      TextFormField(
                        controller: _email,
                        keyboardType: TextInputType.emailAddress,
                        textInputAction: TextInputAction.done,
                        style: const TextStyle(color: AppTheme.black, fontSize: 14),
                        validator: (value) {
                          if (value == null || value.isEmpty || !value.contains('@')) return 'Please enter a valid email';
                          return null;
                        },
                        decoration: const InputDecoration(
                          isDense: true,
                          border: UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.border)),
                          enabledBorder: UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.border)),
                          focusedBorder: UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.black, width: 1.5)),
                          errorBorder: UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.error, width: 1)),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 32),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(_error!, style: const TextStyle(color: AppTheme.error, fontSize: 13, fontWeight: FontWeight.w500)),
                  ),
                ElevatedButton(
                  onPressed: _isLoading ? null : _submit,
                  child: _isLoading
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: AppTheme.white, strokeWidth: 2))
                      : const Text('Send Reset Instructions'),
                ),
              ] else ...[
                const Icon(Icons.check_circle_outline, size: 48, color: AppTheme.accent),
                const SizedBox(height: 24),
                const Text('Check your email', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppTheme.black)),
                const SizedBox(height: 8),
                Text('We have sent reset instructions to ${_email.text}', style: const TextStyle(fontSize: 13, color: AppTheme.gray), textAlign: TextAlign.center),
                const SizedBox(height: 32),
                ElevatedButton(
                  onPressed: () => Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (route) => false),
                  child: const Text('Return to Login'),
                ),
              ],
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
