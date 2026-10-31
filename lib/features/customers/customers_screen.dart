import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../../theme/app_theme.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _filteredCustomers {
    final api = context.read<ApiService>();
    var customers = api.customers.map((c) {
      return {
        'id': c.id,
        'name': c.name,
        'email': c.email,
        'phone': c.phone,
      };
    }).toList();

    if (_searchController.text.isNotEmpty) {
      customers = customers.where((c) =>
          (c['name'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase()) ||
          (c['email'] != null &&
              (c['email'] as String)
                  .toLowerCase()
                  .contains(_searchController.text.toLowerCase())) ||
          (c['phone'] != null &&
              (c['phone'] as String)
                  .toLowerCase()
                  .contains(_searchController.text.toLowerCase()))).toList();
    }

    return customers;
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);

    return Scaffold(
      backgroundColor: c.surface,
      body: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Customers',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: c.textPrimary,
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  style: TextStyle(color: c.textPrimary),
                  decoration: InputDecoration(
                    hintText: 'Search customers...',
                    hintStyle: TextStyle(color: c.textSecondary),
                    prefixIcon: Icon(LucideIcons.search, color: c.textSecondary),
                    filled: true,
                    fillColor: c.surfaceCard,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Customers List
          Expanded(
            child: Consumer<ApiService>(
              builder: (context, api, _) {
                if (api.isLoading && api.customers.isEmpty) {
                  return Center(
                    child: CircularProgressIndicator(color: c.primary),
                  );
                }

                if (_filteredCustomers.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(LucideIcons.users,
                            color: c.textSecondary, size: 64),
                        const SizedBox(height: 16),
                        Text(
                          'No customers found',
                          style: TextStyle(color: c.textSecondary, fontSize: 16),
                        ),
                        const SizedBox(height: 8),
                        TextButton.icon(
                          onPressed: () => _showCreateCustomerDialog(api),
                          icon: const Icon(LucideIcons.plus),
                          label: const Text('Add Customer'),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => api.fetchCustomers(),
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 88),
                    itemCount: _filteredCustomers.length,
                    itemBuilder: (context, index) {
                      final customer = _filteredCustomers[index];
                      return _CustomerCard(
                        customer: customer,
                        onTap: () =>
                            _showCustomerDetails(context, c, customer),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        heroTag: 'customers_fab',
        onPressed: () => _showCreateCustomerDialog(context.read<ApiService>()),
        child: const Icon(LucideIcons.plus),
      ),
    );
  }

  void _showCustomerDetails(
      BuildContext context, AppColors c, Map<String, dynamic> customer) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: c.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.fromLTRB(
            24, 20, 24, 32 + MediaQuery.of(sheetContext).padding.bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: c.divider,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                CircleAvatar(
                  radius: 22,
                  backgroundColor: c.primary.withOpacity(0.12),
                  child: Text(
                    (customer['name'] as String)[0].toUpperCase(),
                    style: TextStyle(
                      color: c.primary,
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    customer['name'],
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: c.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            if (customer['phone'] != null)
              _detailRow(c, LucideIcons.phone, customer['phone']),
            if (customer['email'] != null)
              _detailRow(c, LucideIcons.mail, customer['email']),
            if (customer['phone'] == null && customer['email'] == null)
              Text(
                'No contact details on file',
                style: TextStyle(color: c.textSecondary, fontSize: 13),
              ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => Navigator.pop(sheetContext),
                child: const Text('Close'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _detailRow(AppColors c, IconData icon, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Icon(icon, size: 18, color: c.textSecondary),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              value,
              style: TextStyle(color: c.textPrimary, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showCreateCustomerDialog(ApiService api) async {
    final c = AppColors.of(context);
    final nameController = TextEditingController();
    final phoneController = TextEditingController();
    final emailController = TextEditingController();

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Add Customer'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              autofocus: true,
              style: TextStyle(color: c.textPrimary),
              decoration: _fieldDecoration(c, hint: 'Customer name'),
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
              decoration: _fieldDecoration(c, hint: 'Phone (optional)'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: emailController,
              keyboardType: TextInputType.emailAddress,
              style: TextStyle(color: c.textPrimary),
              decoration: _fieldDecoration(c, hint: 'Email (optional)'),
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

    if (save != true) return;

    final name = nameController.text.trim();
    if (name.isEmpty) {
      _toast('Please enter a customer name');
      return;
    }

    final ok = await api.createCustomer(
      name: name,
      phone: phoneController.text.trim(),
      email: emailController.text.trim(),
    );
    _toast(ok ? 'Customer added' : 'Could not add customer');
  }

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

  void _toast(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}

class _CustomerCard extends StatelessWidget {
  final Map<String, dynamic> customer;
  final VoidCallback onTap;

  const _CustomerCard({required this.customer, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        onTap: onTap,
        leading: CircleAvatar(
          backgroundColor: c.primary.withOpacity(0.12),
          child: Text(
            (customer['name'] as String)[0].toUpperCase(),
            style: TextStyle(
                color: c.primary, fontWeight: FontWeight.w600),
          ),
        ),
        title: Text(
          customer['name'],
          style: TextStyle(color: c.textPrimary),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (customer['email'] != null)
              Text(
                customer['email'],
                style: TextStyle(color: c.textSecondary, fontSize: 12),
              ),
            if (customer['phone'] != null)
              Text(
                customer['phone'],
                style: TextStyle(color: c.textSecondary, fontSize: 12),
              ),
          ],
        ),
        trailing: Icon(LucideIcons.chevronRight, color: c.textSecondary),
      ),
    );
  }
}
