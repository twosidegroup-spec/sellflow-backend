import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/logo_placeholder.dart';
import 'auth_controller.dart';
import 'login_screen.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});
  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _business = TextEditingController();
  final _email = TextEditingController();
  final _passcode = TextEditingController();
  final _confirmPasscode = TextEditingController();
  final _providerNumber = TextEditingController();
  
  bool _obscurePasscode = true;
  bool _obscureConfirm = true;
  String? _selectedProvider;
  
  final Map<String, String> _providerLogos = {
    'bKash': 'assets/images/bkash.png',
    'Nagad': 'assets/images/nagad.png',
    'Rocket': 'assets/images/rocket.png',
    'Upay': 'assets/images/upay.png',
  };

  @override
  void dispose() {
    _name.dispose(); _business.dispose(); _email.dispose();
    _passcode.dispose(); _confirmPasscode.dispose(); _providerNumber.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    if (_passcode.text != _confirmPasscode.text) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Passcodes do not match')));
      return;
    }
    
    final success = await ref.read(authControllerProvider.notifier).register(
      fullName: _name.text.trim(),
      businessName: _business.text.trim(),
      email: _email.text.trim(),
      phone: '', 
      passcode: _passcode.text.trim(),
      length: 4,
    );
    
    if (success && mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  Widget _buildField(String label, TextEditingController c, {TextInputType? type, bool obscure = false, VoidCallback? onToggleObscure}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.gray, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          TextField(
            controller: c,
            keyboardType: type,
            obscureText: obscure,
            maxLength: type == TextInputType.number ? 4 : null,
            textInputAction: TextInputAction.next,
            style: const TextStyle(color: AppTheme.black, fontSize: 14),
            decoration: InputDecoration(
              isDense: true,
              counterText: '',
              suffixIcon: onToggleObscure != null
                  ? IconButton(
                      icon: Icon(obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined, size: 18, color: AppTheme.gray),
                      onPressed: onToggleObscure,
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    )
                  : null,
              border: const UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.border)),
              enabledBorder: const UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.border)),
              focusedBorder: const UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.black, width: 1.5)),
              errorBorder: const UnderlineInputBorder(borderSide: BorderSide(color: AppTheme.error, width: 1)),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authControllerProvider);
    final busy = state.status == AuthStatus.working;

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
              const Text('Create account', style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600, color: AppTheme.black, letterSpacing: -0.5)),
              const SizedBox(height: 8),
              const Text('Set up your business on SellFlow.', style: TextStyle(fontSize: 13, color: AppTheme.gray)),
              const SizedBox(height: 40),
              Form(
                key: _form,
                child: Column(
                  children: [
                    _buildField('FULL NAME', _name),
                    _buildField('BUSINESS NAME', _business),
                    _buildField('EMAIL ADDRESS', _email, type: TextInputType.emailAddress),
                    _buildField('PASSCODE', _passcode, type: TextInputType.number, obscure: _obscurePasscode, onToggleObscure: () => setState(() => _obscurePasscode = !_obscurePasscode)),
                    _buildField('CONFIRM PASSCODE', _confirmPasscode, type: TextInputType.number, obscure: _obscureConfirm, onToggleObscure: () => setState(() => _obscureConfirm = !_obscureConfirm)),
                    
                    const SizedBox(height: 8),
                    const Text('PAYMENT PROVIDER (OPTIONAL)', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.gray, letterSpacing: 0.5)),
                    const SizedBox(height: 16),
                    
                    // FIXED: Using Wrap instead of Row to prevent overflow on small screens
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      alignment: WrapAlignment.center,
                      children: _providerLogos.entries.map((entry) {
                        final isSelected = _selectedProvider == entry.key;
                        return GestureDetector(
                          onTap: () => setState(() => _selectedProvider = isSelected ? null : entry.key),
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 200),
                            width: 64,
                            height: 64,
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              border: Border.all(color: isSelected ? AppTheme.black : AppTheme.border, width: isSelected ? 2 : 1),
                              borderRadius: BorderRadius.circular(8),
                              color: AppTheme.white,
                            ),
                            child: Image.asset(
                              entry.value,
                              fit: BoxFit.contain,
                              errorBuilder: (context, error, stackTrace) {
                                return Center(child: Text(entry.key, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600)));
                              },
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                    
                    if (_selectedProvider != null) ...[
                      const SizedBox(height: 24),
                      _buildField('$_selectedProvider NUMBER (OPTIONAL)', _providerNumber, type: TextInputType.phone),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (state.error != null && !busy)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Text(state.error!, style: const TextStyle(color: AppTheme.error, fontSize: 13, fontWeight: FontWeight.w500)),
                ),
              ElevatedButton(
                onPressed: busy ? null : _submit,
                child: busy
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: AppTheme.white, strokeWidth: 2))
                    : const Text('Create Account'),
              ),
              const SizedBox(height: 32),
              TextButton(
                onPressed: () => Navigator.of(context).pushAndRemoveUntil(MaterialPageRoute(builder: (_) => const LoginScreen()), (route) => false),
                child: const Text.rich(TextSpan(text: 'Already have an account? ', style: TextStyle(color: AppTheme.gray), children: [TextSpan(text: 'Log in', style: TextStyle(color: AppTheme.black, decoration: TextDecoration.underline))])),
              ),
              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
