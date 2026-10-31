import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/keypad_sound.dart';
import '../../theme/app_theme.dart';
import 'widgets/iphone_frame.dart';
import 'widgets/passcode_widgets.dart';

const _ink = Color(0xFF12203A);
const _muted = Color(0xFF64748B);
const _blue = Color(0xFF2563EB);
const _line = Color(0xFFD8E7F8);

const _cardBorder = Color(0xFFE3EDF9);
const _iconCircle = Color(0xFFEAF3FE);

class _Provider {
  final String id;
  final String label;
  const _Provider(this.id, this.label);
}

const _providers = [
  _Provider('bkash', 'bKash'),
  _Provider('nagad', 'Nagad'),
  _Provider('paypal', 'PayPal'),
  _Provider('cashapp', 'Cash App'),
  _Provider('stripe', 'Stripe'),
];

class RegistrationScreen extends StatefulWidget {
  const RegistrationScreen({super.key});

  @override
  State<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  final _nameController = TextEditingController();
  final _businessController = TextEditingController();
  final _emailController = TextEditingController();
  final _receivingController = TextEditingController();
  String _selectedMethod = 'bkash';
  String? _errorMessage;

  @override
  void dispose() {
    _nameController.dispose();
    _businessController.dispose();
    _emailController.dispose();
    _receivingController.dispose();
    super.dispose();
  }

  bool get _isPhoneProvider =>
      _selectedMethod == 'bkash' || _selectedMethod == 'nagad';

  bool get _isEmailProvider =>
      _selectedMethod == 'paypal' || _selectedMethod == 'stripe';

  String get _numberLabel {
    switch (_selectedMethod) {
      case 'bkash':
        return 'bKash Number';
      case 'nagad':
        return 'Nagad Number';
      case 'paypal':
        return 'PayPal Email';
      case 'cashapp':
        return 'Cash App Cashtag';
      default:
        return 'Stripe Account Email';
    }
  }

  String get _numberHint {
    switch (_selectedMethod) {
      case 'bkash':
      case 'nagad':
        return '01XXXXXXXXX';
      case 'cashapp':
        return '\$yourtag';
      default:
        return 'you@example.com';
    }
  }

  IconData get _numberIcon {
    if (_isPhoneProvider) return LucideIcons.phone;
    if (_selectedMethod == 'cashapp') return LucideIcons.atSign;
    return LucideIcons.mail;
  }

  String? _validateNumber(String value) {
    if (value.isEmpty) return 'Please enter your $_numberLabel';
    if (_isPhoneProvider && !RegExp(r'^01\d{9}$').hasMatch(value)) {
      return 'Enter a valid 11-digit number (e.g. 01712345678)';
    }
    if (_isEmailProvider && !value.contains('@')) {
      return 'Enter a valid email address';
    }
    if (_selectedMethod == 'cashapp' && value.length < 2) {
      return 'Enter a valid Cash App cashtag';
    }
    return null;
  }

  void _handleNext() {
    final name = _nameController.text.trim();
    final business = _businessController.text.trim();
    final email = _emailController.text.trim();
    final receiving = _receivingController.text.trim();

    if (name.isEmpty || business.isEmpty) {
      setState(() => _errorMessage = 'Please enter your name and business name');
      return;
    }
    if (!email.contains('@') || email.length < 5) {
      setState(() => _errorMessage = 'Please enter a valid email address');
      return;
    }
    final numberError = _validateNumber(receiving);
    if (numberError != null) {
      setState(() => _errorMessage = numberError);
      return;
    }

    setState(() => _errorMessage = null);
    Navigator.push(
      context,
      FadeSlideRoute(
        builder: (context) => PasscodeCreationScreen(
          name: name,
          businessName: business,
          email: email,
          paymentMethod: _selectedMethod,
          receivingNumber: receiving,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return IPhoneFrame(child: _buildScreen());
  }

  Widget _buildScreen() {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/register_bg.png',
            fit: BoxFit.cover,
            alignment: Alignment.topCenter,
          ),
          SafeArea(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 480),
                child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(22, 6, 22, 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Back
                  Align(
                    alignment: Alignment.centerLeft,
                    child: IconButton(
                      onPressed: () => Navigator.pop(context),
                      padding: EdgeInsets.zero,
                      icon: const Icon(LucideIcons.arrowLeft,
                          size: 20, color: _ink),
                    ),
                  ),
                  const SizedBox(height: 4),

                  // Brand
                  const Center(
                    child: Column(
                      children: [
                        Text(
                          'SELLFLOW',
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 2.4,
                            color: _ink,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Your Business. In Flow.',
                          style: TextStyle(fontSize: 12, color: _muted),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 22),

                  // 2-step indicator (Account -> Passcode)
                  Row(
                    children: [
                      _StepNode(
                        step: 1,
                        label: 'Account',
                        active: true,
                        done: false,
                      ),
                      Expanded(
                        child: Container(
                          height: 2,
                          margin: const EdgeInsets.only(top: 13, bottom: 18),
                          color: _line,
                        ),
                      ),
                      _StepNode(
                        step: 2,
                        label: 'Passcode',
                        active: false,
                        done: false,
                      ),
                    ],
                  ),
                  const SizedBox(height: 26),

                  const Text(
                    'STEP 1 OF 2',
                    style: TextStyle(
                      fontSize: AppText.label,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.4,
                      color: _blue,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Create Your Account',
                    style: TextStyle(
                      fontSize: AppText.pageHeading,
                      fontWeight: FontWeight.w700,
                      color: _ink,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Tell us a bit about yourself and your business.\n'
                    'It only takes a minute.',
                    style: TextStyle(fontSize: AppText.body, fontWeight: FontWeight.w400, color: _muted, height: 1.5),
                  ),
                  const SizedBox(height: 22),

                  if (_errorMessage != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFEBEE),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xFFEF9A9A)),
                      ),
                      child: Text(
                        _errorMessage!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            color: Color(0xFFC62828), fontSize: 12.5),
                      ),
                    ),

                  _FieldCard(
                    controller: _nameController,
                    icon: LucideIcons.user,
                    label: 'Full Name',
                    hint: 'Enter your full name',
                  ),
                  const SizedBox(height: 12),
                  _FieldCard(
                    controller: _businessController,
                    icon: LucideIcons.briefcase,
                    label: 'Business Name',
                    hint: 'Enter your business name',
                  ),
                  const SizedBox(height: 12),
                  _FieldCard(
                    controller: _emailController,
                    icon: LucideIcons.mail,
                    label: 'Email Address',
                    hint: 'you@domain.com',
                    keyboardType: TextInputType.emailAddress,
                  ),
                  const SizedBox(height: 24),

                  const Text(
                    'Choose Your Payment Provider',
                    style: TextStyle(
                      fontSize: AppText.cardHeading,
                      fontWeight: FontWeight.w600,
                      color: _ink,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Select your preferred payment method.',
                    style: TextStyle(fontSize: 12, color: _muted),
                  ),
                  const SizedBox(height: 14),

                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (var i = 0; i < _providers.length; i++) ...[
                        if (i > 0) const SizedBox(width: 8),
                        Expanded(child: _buildProviderTile(_providers[i])),
                      ],
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Provider-specific number / account, asked right after selection
                  _FieldCard(
                    controller: _receivingController,
                    icon: _numberIcon,
                    label: _numberLabel,
                    hint: _numberHint,
                    keyboardType: _isPhoneProvider
                        ? TextInputType.phone
                        : (_isEmailProvider
                            ? TextInputType.emailAddress
                            : TextInputType.text),
                    inputFormatters: _isPhoneProvider
                        ? [
                            FilteringTextInputFormatter.digitsOnly,
                            LengthLimitingTextInputFormatter(11),
                          ]
                        : null,
                  ),
                  const SizedBox(height: 18),

                  // Secure info box
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F2FE).withOpacity(0.85),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 38,
                          height: 38,
                          decoration: const BoxDecoration(
                            color: _iconCircle,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(LucideIcons.shieldCheck,
                              size: 19, color: _blue),
                        ),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Your information is secure',
                                style: TextStyle(
                                  fontSize: AppText.label,
                                  fontWeight: FontWeight.w600,
                                  color: _ink,
                                ),
                              ),
                              SizedBox(height: 3),
                              Text(
                                'We use industry-standard encryption to keep '
                                'your data safe and private.',
                                style: TextStyle(
                                    fontSize: AppText.label,
                                    fontWeight: FontWeight.w400,
                                    color: _muted,
                                    height: 1.4),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Next
                  Container(
                    height: 54,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF4D9BF5), Color(0xFF2563EB)],
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                      ),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: [
                        BoxShadow(
                          color: _blue.withOpacity(0.35),
                          blurRadius: 16,
                          offset: const Offset(0, 6),
                        ),
                      ],
                    ),
                    child: Material(
                      color: Colors.transparent,
                      borderRadius: BorderRadius.circular(16),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(16),
                        onTap: _handleNext,
                        child: const Center(
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                'Next',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              SizedBox(width: 10),
                              Icon(LucideIcons.arrowRight,
                                  color: Colors.white, size: 20),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),

                  // Log in
                  Center(
                    child: GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: RichText(
                        text: const TextSpan(
                          text: 'Already have an account? ',
                          style: TextStyle(
                            fontSize: AppText.label,
                            fontWeight: FontWeight.w400,
                            color: _muted,
                          ),
                          children: [
                            TextSpan(
                              text: 'Log in',
                              style: TextStyle(
                                fontSize: AppText.label,
                                color: _blue,
                                fontWeight: FontWeight.w700,
                                decoration: TextDecoration.underline,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProviderTile(_Provider provider) {
    final selected = _selectedMethod == provider.id;

    return GestureDetector(
      onTap: () => setState(() {
        _selectedMethod = provider.id;
        _receivingController.clear();
        _errorMessage = null;
      }),
      child: Column(
        children: [
          Stack(
            clipBehavior: Clip.none,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(15),
                  border: Border.all(
                    color: selected ? _blue : _cardBorder,
                    width: selected ? 2 : 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFF7FB0DE).withOpacity(0.20),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Center(child: _ProviderLogo(id: provider.id)),
              ),
              if (selected)
                Positioned(
                  right: -4,
                  top: -4,
                  child: Container(
                    key: ValueKey('payment-selected-${provider.id}'),
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      color: _blue,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: const Icon(LucideIcons.check,
                        size: 11, color: Colors.white),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            provider.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: AppText.label,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
              color: selected ? _blue : _muted,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProviderLogo extends StatelessWidget {
  final String id;

  const _ProviderLogo({required this.id});

  @override
  Widget build(BuildContext context) {
    switch (id) {
      case 'bkash':
        return _svg('assets/images/bkash.svg', 'bKash', 30, 30);
      case 'nagad':
        return _svg('assets/images/nagad.svg', 'Nagad', 30, 34);
      case 'paypal':
        return _svg('assets/images/paypal.svg', 'PayPal', 30, 30);
      case 'cashapp':
        return _svg('assets/images/cashapp.svg', 'Cash App', 30, 30);
      case 'stripe':
        return _svg('assets/images/stripe.svg', 'Stripe', 30, 30);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _svg(String asset, String label, double width, double height) {
    return SvgPicture.asset(
      asset,
      width: width,
      height: height,
      fit: BoxFit.contain,
      semanticsLabel: label,
    );
  }
}

class _FieldCard extends StatelessWidget {
  final TextEditingController controller;
  final IconData icon;
  final String label;
  final String hint;
  final TextInputType? keyboardType;
  final List<TextInputFormatter>? inputFormatters;

  const _FieldCard({
    required this.controller,
    required this.icon,
    required this.label,
    required this.hint,
    this.keyboardType,
    this.inputFormatters,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _cardBorder),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF7FB0DE).withOpacity(0.16),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: const BoxDecoration(
              color: _iconCircle,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 20, color: _blue),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: _ink,
                  ),
                ),
                const SizedBox(height: 2),
                TextField(
                  controller: controller,
                  keyboardType: keyboardType,
                  inputFormatters: inputFormatters,
                  style: const TextStyle(fontSize: 13.5, color: _ink),
                  decoration: InputDecoration(
                    isCollapsed: true,
                    filled: false,
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    hintText: hint,
                    hintStyle: const TextStyle(
                      fontSize: AppText.body,
                      fontWeight: FontWeight.w400,
                      color: Color(0xFF94A3B8),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StepNode extends StatelessWidget {
  final int step;
  final String label;
  final bool active;
  final bool done;

  const _StepNode({
    required this.step,
    required this.label,
    required this.active,
    required this.done,
  });

  @override
  Widget build(BuildContext context) {
    final highlighted = active || done;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: highlighted ? _blue : Colors.white,
            border: Border.all(
              color: highlighted ? _blue : _line,
              width: 1.6,
            ),
          ),
          child: Center(
            child: done
                ? const Icon(LucideIcons.check, size: 14, color: Colors.white)
                : Text(
                    '$step',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: highlighted ? Colors.white : const Color(0xFF94A3B8),
                    ),
                  ),
          ),
        ),
        const SizedBox(height: 5),
        Text(
          label,
          style: TextStyle(
            fontSize: AppText.label,
            fontWeight: highlighted ? FontWeight.w600 : FontWeight.w500,
            color: highlighted ? _blue : const Color(0xFF94A3B8),
          ),
        ),
      ],
    );
  }
}

/// Step 2: create (and confirm) the 4-digit passcode with the same
/// circles + circular keypad used on the login screen.
class PasscodeCreationScreen extends StatefulWidget {
  final String name;
  final String businessName;
  final String email;
  final String paymentMethod;
  final String receivingNumber;

  const PasscodeCreationScreen({
    super.key,
    required this.name,
    required this.businessName,
    required this.email,
    required this.paymentMethod,
    required this.receivingNumber,
  });

  @override
  State<PasscodeCreationScreen> createState() => _PasscodeCreationScreenState();
}

class _PasscodeCreationScreenState extends State<PasscodeCreationScreen>
    with SingleTickerProviderStateMixin {
  String _pin = '';
  String _confirmPin = '';
  bool _isConfirming = false;
  bool _isLoading = false;
  bool _isSuccess = false;
  String? _errorMessage;
  late AnimationController _shakeController;
  late Animation<double> _shakeAnimation;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      duration: const Duration(milliseconds: 500),
      vsync: this,
    );
    _shakeAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _shakeController, curve: Curves.elasticIn),
    );
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  void _shake() {
    _shakeController.forward().then((_) => _shakeController.reverse());
  }

  void _handleDigit(String digit) {
    if (_isLoading || _isSuccess) return;

    setState(() {
      if (_isConfirming) {
        if (_confirmPin.length < 4) {
          _confirmPin += digit;
          _errorMessage = null;
        }
      } else {
        if (_pin.length < 4) {
          _pin += digit;
          _errorMessage = null;
        }
      }
    });

    if (!_isConfirming && _pin.length == 4) {
      Future.delayed(const Duration(milliseconds: 200), () {
        if (mounted) setState(() => _isConfirming = true);
      });
    } else if (_isConfirming && _confirmPin.length == 4) {
      Future.delayed(const Duration(milliseconds: 200), _submit);
    }
  }

  void _handleBackspace() {
    if (_isLoading || _isSuccess) return;
    setState(() {
      if (_isConfirming) {
        if (_confirmPin.isNotEmpty) {
          _confirmPin =
              _confirmPin.substring(0, _confirmPin.length - 1);
        } else {
          _isConfirming = false;
        }
      } else if (_pin.isNotEmpty) {
        _pin = _pin.substring(0, _pin.length - 1);
      }
      _errorMessage = null;
    });
  }

  Future<void> _submit() async {
    if (_pin != _confirmPin) {
      _shake();
      setState(() {
        _errorMessage = 'Passcodes do not match. Try again.';
        _pin = '';
        _confirmPin = '';
        _isConfirming = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final api = context.read<ApiService>();
    final success = await api.register(
      widget.email,
      _pin,
      widget.name,
      businessName: widget.businessName,
      paymentProvider: widget.paymentMethod,
      receivingNumber: widget.receivingNumber,
    );

    if (!mounted) return;
    setState(() => _isLoading = false);

    if (success) {
      KeypadSound.success();
      setState(() => _isSuccess = true);
      await Future.delayed(const Duration(milliseconds: 400));
      if (!mounted) return;
      Navigator.popUntil(context, (route) => route.isFirst);
    } else {
      _shake();
      setState(() {
        _errorMessage = api.error ?? 'Registration failed';
        _pin = '';
        _confirmPin = '';
        _isConfirming = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return IPhoneFrame(child: _buildScreen());
  }

  Widget _buildScreen() {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/register_bg.png',
            fit: BoxFit.cover,
            alignment: Alignment.topCenter,
          ),
          SafeArea(
            child: LayoutBuilder(
              builder: (context, constraints) => SingleChildScrollView(
                child: ConstrainedBox(
                  constraints:
                      BoxConstraints(minHeight: constraints.maxHeight),
                  child: IntrinsicHeight(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 22),
                      child: Column(
                        children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: IconButton(
                      onPressed: () => Navigator.pop(context),
                      padding: EdgeInsets.zero,
                      icon: const Icon(LucideIcons.arrowLeft,
                          size: 20, color: _ink),
                    ),
                  ),
                  const SizedBox(height: 2),

                  const Center(
                    child: Text(
                      'SELLFLOW',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 2,
                        color: _ink,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),

                  Text(
                    _isConfirming ? 'Confirm Your Passcode' : 'Create Your Passcode',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w700,
                      color: _ink,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _isConfirming
                        ? 'Re-enter your 4-digit PIN to confirm'
                        : 'Choose a 4-digit PIN to secure your account',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: AppText.body,
                      fontWeight: FontWeight.w400,
                      color: _muted,
                    ),
                  ),
                  const SizedBox(height: 20),

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
                      filled: _isConfirming ? _confirmPin.length : _pin.length,
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
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: Color(0xFFEF4444),
                              fontSize: 12.5,
                            ),
                          )
                        : null,
                  ),
                  const SizedBox(height: 8),

                  PasscodeKeypad(
                    dark: false,
                    enabled: !(_isLoading || _isSuccess),
                    onDigit: _handleDigit,
                    onBackspace: _handleBackspace,
                  ),

                  if (_isLoading) ...[
                    const SizedBox(height: 10),
                    const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ],

                  const Spacer(),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Icon(LucideIcons.lock,
                          size: 13, color: _muted),
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
                  const SizedBox(height: 26),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
