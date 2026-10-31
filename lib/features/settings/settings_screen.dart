import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/settings_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/theme_controller.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final api = context.watch<ApiService>();
    final theme = context.watch<ThemeController>();
    final settings = context.watch<SettingsController>();

    return Scaffold(
      backgroundColor: c.surface,
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: c.surface,
        foregroundColor: c.textPrimary,
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Appearance
            _sectionHeader(c, 'Appearance'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: _buildThemeSelector(c, theme),
            ),
            const SizedBox(height: 8),

            // Account
            _sectionHeader(c, 'Account'),
            _tile(
              c,
              icon: LucideIcons.user,
              label: 'Profile',
              subtitle: api.currentUser?.email ?? 'Edit your profile',
              onTap: () => _showProfileDialog(api),
            ),
            _tile(
              c,
              icon: LucideIcons.lock,
              label: 'Passcode',
              subtitle: 'Change your passcode',
              onTap: () => _showPasscodeDialog(api),
            ),

            // Connection
            _sectionHeader(c, 'Connection'),
            _tile(
              c,
              icon: LucideIcons.cloud,
              label: 'Server URL',
              subtitle: api.baseUrl,
              onTap: () => _showServerDialog(api),
            ),

            // Business
            _sectionHeader(c, 'Business'),
            _tile(
              c,
              icon: LucideIcons.store,
              label: 'Business Profile',
              subtitle: api.currentBusiness?.name ?? 'Update business information',
              onTap: () => _showBusinessDialog(api),
            ),
            _tile(
              c,
              icon: LucideIcons.wallet,
              label: 'Payment Methods',
              subtitle: _paymentSubtitle(api),
              onTap: () => _showPaymentMethodsDialog(api),
            ),

            // Preferences
            _sectionHeader(c, 'Preferences'),
            _switchTile(
              c,
              icon: LucideIcons.bell,
              label: 'Notifications',
              subtitle: 'Enable push notifications',
              value: settings.notificationsEnabled,
              onChanged: (value) => settings.setNotifications(value),
            ),
            _switchTile(
              c,
              icon: LucideIcons.creditCard,
              label: 'Auto Payment Detection',
              subtitle: 'Auto-collect incoming bKash / Nagad payments',
              value: settings.paymentDetectionEnabled,
              onChanged: (value) => settings.setPaymentDetection(value),
            ),
            _switchTile(
              c,
              icon: LucideIcons.zap,
              label: 'Keypad Sounds',
              subtitle: 'Play a tone when tapping PIN keys',
              value: settings.soundEnabled,
              onChanged: (value) => settings.setSound(value),
            ),
            if (settings.paymentDetectionEnabled)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton.icon(
                    onPressed: () => _showTestPaymentDialog(api),
                    icon: const Icon(LucideIcons.zap, size: 18),
                    label: const Text('Send test payment'),
                  ),
                ),
              ),

            // Support
            _sectionHeader(c, 'Support'),
            _tile(
              c,
              icon: LucideIcons.helpCircle,
              label: 'Help Center',
              subtitle: 'Get help and support',
              onTap: _showHelpDialog,
            ),
            _tile(
              c,
              icon: LucideIcons.messageSquare,
              label: 'Send Feedback',
              subtitle: 'Report issues or suggest features',
              onTap: _showFeedbackDialog,
            ),
            _tile(
              c,
              icon: LucideIcons.info,
              label: 'About SELLFLOW',
              subtitle: 'App version 1.0.0',
              onTap: _showAboutDialog,
            ),

            const SizedBox(height: 24),

            // Logout
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () async {
                    final confirmed = await showDialog<bool>(
                      context: context,
                      builder: (dialogContext) => AlertDialog(
                        title: const Text('Logout'),
                        content:
                            const Text('Are you sure you want to logout?'),
                        actions: [
                          TextButton(
                            onPressed: () =>
                                Navigator.pop(dialogContext, false),
                            child: const Text('Cancel'),
                          ),
                          TextButton(
                            onPressed: () =>
                                Navigator.pop(dialogContext, true),
                            child: Text(
                              'Logout',
                              style: TextStyle(color: c.danger),
                            ),
                          ),
                        ],
                      ),
                    );

                    if (confirmed == true && mounted) {
                      await api.logout();
                    }
                  },
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: c.danger),
                    foregroundColor: c.danger,
                  ),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      'Logout',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ),
            ),

            const SizedBox(height: 44),
          ],
        ),
      ),
    );
  }

  String _paymentSubtitle(ApiService api) {
    final provider = api.currentUser?.paymentProvider;
    final number = api.currentUser?.receivingNumber;
    if (provider == null) return 'Configure receiving numbers';
    final label = provider == 'bkash' ? 'bKash' : 'Nagad';
    return number == null ? label : '$label • $number';
  }

  Widget _sectionHeader(AppColors c, String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      child: Text(
        title,
        style: TextStyle(
          color: c.textSecondary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _tile(
    AppColors c, {
    required IconData icon,
    required String label,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: c.textPrimary),
      title: Text(label, style: TextStyle(color: c.textPrimary)),
      subtitle: Text(
        subtitle,
        style: TextStyle(color: c.textSecondary, fontSize: 12),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: Icon(LucideIcons.chevronRight, color: c.textSecondary),
      onTap: onTap,
    );
  }

  Widget _switchTile(
    AppColors c, {
    required IconData icon,
    required String label,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return SwitchListTile(
      secondary: Icon(icon, color: c.textPrimary),
      title: Text(label, style: TextStyle(color: c.textPrimary)),
      subtitle: Text(
        subtitle,
        style: TextStyle(color: c.textSecondary, fontSize: 12),
      ),
      value: value,
      onChanged: onChanged,
      activeColor: c.primary,
    );
  }

  Widget _buildThemeSelector(AppColors c, ThemeController theme) {
    final options = [
      (ThemeMode.light, 'Light', LucideIcons.sun),
      (ThemeMode.dark, 'Dark', LucideIcons.moon),
      (ThemeMode.system, 'System', LucideIcons.sunMoon),
    ];

    return Row(
      children: options.map((option) {
        final (mode, label, icon) = option;
        final selected = theme.mode == mode;
        return Expanded(
          child: Padding(
            padding: EdgeInsets.only(right: mode == ThemeMode.system ? 0 : 12),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () => theme.setMode(mode),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  color: selected
                      ? c.primary.withOpacity(0.12)
                      : c.surfaceCard,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: selected ? c.primary : c.border,
                    width: selected ? 2 : 1,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(icon, size: 22, color: selected ? c.primary : c.textSecondary),
                    const SizedBox(height: 6),
                    Text(
                      label,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        color: selected ? c.primary : c.textPrimary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }

  // ---------------------------------------------------------------- dialogs

  InputDecoration _fieldDecoration(AppColors c, {required String hint}) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: c.textSecondary.withOpacity(0.7)),
      filled: true,
      fillColor: c.surfaceElevated,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: c.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: c.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: c.primary, width: 2),
      ),
    );
  }

  Future<void> _showProfileDialog(ApiService api) async {
    final c = AppColors.of(context);
    final nameController =
        TextEditingController(text: api.currentUser?.fullName ?? '');
    final phoneController =
        TextEditingController(text: api.currentUser?.phone ?? '');

    final saved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Profile'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              style: TextStyle(color: c.textPrimary),
              decoration: _fieldDecoration(c, hint: 'Full name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: phoneController,
              keyboardType: TextInputType.phone,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(11),
              ],
              style: TextStyle(color: c.textPrimary),
              decoration: _fieldDecoration(c, hint: 'Phone number'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (saved == true) {
      final ok = await api.updateMe(
        fullName: nameController.text.trim(),
        phone: phoneController.text.trim(),
      );
      _toast(ok ? 'Profile updated' : 'Could not update profile');
    }
  }

  Future<void> _showPasscodeDialog(ApiService api) async {
    final c = AppColors.of(context);
    final currentController = TextEditingController();
    final newController = TextEditingController();
    final confirmController = TextEditingController();
    String? error;

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Change passcode'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _passcodeField(c, currentController, 'Current passcode'),
              const SizedBox(height: 12),
              _passcodeField(c, newController, 'New passcode'),
              const SizedBox(height: 12),
              _passcodeField(c, confirmController, 'Confirm new passcode'),
              if (error != null) ...[
                const SizedBox(height: 12),
                Text(
                  error!,
                  style: TextStyle(color: c.danger, fontSize: 12),
                ),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (newController.text.length < 4) {
                  setDialogState(() => error = 'New passcode must be 4 digits');
                  return;
                }
                if (newController.text != confirmController.text) {
                  setDialogState(() => error = 'New passcodes do not match');
                  return;
                }
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );

    if (save == true) {
      final result =
          await api.changePasscode(currentController.text, newController.text);
      _toast(result ?? 'Passcode updated');
    }
  }

  Widget _passcodeField(
      AppColors c, TextEditingController controller, String hint) {
    return TextField(
      controller: controller,
      obscureText: true,
      keyboardType: TextInputType.number,
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(4),
      ],
      style: TextStyle(color: c.textPrimary),
      decoration: _fieldDecoration(c, hint: hint),
    );
  }

  Future<void> _showBusinessDialog(ApiService api) async {
    final c = AppColors.of(context);
    final controller =
        TextEditingController(text: api.currentBusiness?.name ?? '');

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Business Profile'),
        content: TextField(
          controller: controller,
          style: TextStyle(color: c.textPrimary),
          decoration: _fieldDecoration(c, hint: 'Business name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (save == true && controller.text.trim().isNotEmpty) {
      final ok = await api.updateBusiness(controller.text.trim());
      _toast(ok ? 'Business updated' : 'Could not update business');
    }
  }

  Future<void> _showPaymentMethodsDialog(ApiService api) async {
    final c = AppColors.of(context);
    String provider = api.currentUser?.paymentProvider ?? 'bkash';
    final numberController =
        TextEditingController(text: api.currentUser?.receivingNumber ?? '');

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Payment Methods'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  _providerChip(c, 'bKash', provider == 'bkash',
                      () => setDialogState(() => provider = 'bkash')),
                  const SizedBox(width: 10),
                  _providerChip(c, 'Nagad', provider == 'nagad',
                      () => setDialogState(() => provider = 'nagad')),
                ],
              ),
              const SizedBox(height: 14),
              TextField(
                controller: numberController,
                keyboardType: TextInputType.phone,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(11),
                ],
                style: TextStyle(color: c.textPrimary),
                decoration:
                    _fieldDecoration(c, hint: 'Receiving number (01XXXXXXXXX)'),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );

    if (save == true) {
      final ok = await api.updateMe(
        paymentProvider: provider,
        receivingNumber: numberController.text.trim(),
      );
      _toast(ok ? 'Payment method updated' : 'Could not update payment method');
    }
  }

  Widget _providerChip(AppColors c, String label, bool selected, VoidCallback onTap) {
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(vertical: 10),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? c.primary.withOpacity(0.12) : c.surfaceElevated,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: selected ? c.primary : c.border,
              width: selected ? 2 : 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              color: selected ? c.primary : c.textPrimary,
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _showTestPaymentDialog(ApiService api) async {
    final c = AppColors.of(context);
    String method = 'bkash';
    final amountController = TextEditingController();
    String? error;

    final submit = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Test incoming payment'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Simulates a payment arriving on your receiving number. '
                'Orders with the exact amount are matched automatically.',
                style: TextStyle(color: c.textSecondary, fontSize: 12),
              ),
              const SizedBox(height: 14),
              Row(
                children: ['bkash', 'nagad', 'rocket', 'upay'].map((m) {
                  final selected = method == m;
                  final label = m == 'bkash'
                      ? 'bKash'
                      : m[0].toUpperCase() + m.substring(1);
                  return Expanded(
                    child: Padding(
                      padding: EdgeInsets.only(right: m == 'upay' ? 0 : 8),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(10),
                        onTap: () => setDialogState(() => method = m),
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 9),
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: selected
                                ? c.primary.withOpacity(0.12)
                                : c.surfaceElevated,
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: selected ? c.primary : c.border,
                              width: selected ? 2 : 1,
                            ),
                          ),
                          child: Text(
                            label,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: selected ? c.primary : c.textPrimary,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 14),
              TextField(
                controller: amountController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
                ],
                style: TextStyle(color: c.textPrimary),
                decoration: _fieldDecoration(c, hint: 'Amount ৳'),
              ),
              if (error != null) ...[
                const SizedBox(height: 10),
                Text(error!, style: TextStyle(color: c.danger, fontSize: 12)),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final amount = double.tryParse(amountController.text);
                if (amount == null || amount <= 0) {
                  setDialogState(() => error = 'Enter a valid amount');
                  return;
                }
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Send'),
            ),
          ],
        ),
      ),
    );

    if (submit != true) return;

    final result = await api.simulateIncomingPayment(
      amount: double.parse(amountController.text),
      method: method,
    );

    if (!mounted) return;

    if (result == null) {
      _toast('Connection failed. Please check your network.');
    } else if (result['error'] == 'no_number') {
      _toast('Set your receiving number first (Payment Methods)');
    } else if (result['error'] == 'not_connected') {
      _toast('This receiving number is not connected to any business');
    } else if (result['matched'] == true) {
      _toast(
          'Payment received • matched to Order #${result['order_id']} — added to Payments');
    } else {
      _toast('Payment received • no matching order yet — see it on Overview');
    }
  }

  void _showHelpDialog() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Help Center'),
        content: const Text(
          'Need a hand?\n\n'
          '• Register → set your passcode → login with your passcode\n'
          '• Add products and customers from their tabs\n'
          '• Track daily revenue and profit on the Overview\n\n'
          'Contact support: support@tsgi.com',
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  void _showFeedbackDialog() {
    final c = AppColors.of(context);
    final controller = TextEditingController();

    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Send Feedback'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              maxLines: 4,
              style: TextStyle(color: c.textPrimary),
              decoration: _fieldDecoration(c, hint: 'Tell us what you think...'),
            ),
            const SizedBox(height: 10),
            Text(
              'Your feedback is copied so you can send it to us.',
              style: TextStyle(color: c.textSecondary, fontSize: 11),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              final text = controller.text.trim();
              if (text.isEmpty) return;
              await Clipboard.setData(ClipboardData(text: text));
              if (dialogContext.mounted) Navigator.pop(dialogContext);
              _toast('Feedback copied — send it to support@tsgi.com');
            },
            child: const Text('Copy feedback'),
          ),
        ],
      ),
    );
  }

  Future<void> _showServerDialog(ApiService api) async {
    final controller = TextEditingController(text: api.baseUrl);
    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Server URL'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'Backend URL',
            hintText: 'http://192.168.0.219:8000',
          ),
          keyboardType: TextInputType.url,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (save == true) {
      final url = controller.text.trim();
      if (url.isNotEmpty) {
        await api.setBaseUrl(url);
        _toast('Server URL updated');
      }
    }
  }

  void _showAboutDialog() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('About SELLFLOW'),
        content: const Text(
          'SELLFLOW v1.0.0\n\n'
          'E-commerce management for your business.\n\n'
          'Powered by TSGI',
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }
}
