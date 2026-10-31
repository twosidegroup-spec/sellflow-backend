import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/format.dart';
import '../../theme/app_theme.dart';

class PaymentsScreen extends StatefulWidget {
  const PaymentsScreen({super.key});

  @override
  State<PaymentsScreen> createState() => _PaymentsScreenState();
}

class _PaymentsScreenState extends State<PaymentsScreen> {
  String _selectedFilter = 'All';
  final _searchController = TextEditingController();
  final List<String> _filters = ['All', 'Completed', 'Pending', 'Failed'];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _filteredPayments {
    final api = context.read<ApiService>();
    var payments = api.payments.map((p) {
      return {
        'id': p.id,
        'method': p.method,
        'amount': p.amount,
        'status': p.status,
        'date': p.createdAt,
      };
    }).toList();

    if (_selectedFilter != 'All') {
      payments = payments
          .where((p) =>
              (p['status'] as String).toLowerCase() ==
              _selectedFilter.toLowerCase())
          .toList();
    }

    if (_searchController.text.isNotEmpty) {
      payments = payments.where((p) =>
          (p['method'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase()) ||
          (p['status'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase())).toList();
    }

    return payments;
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);

    return Scaffold(
      backgroundColor: c.surface,
      appBar: AppBar(
        title: const Text('Payments'),
        backgroundColor: c.surface,
        foregroundColor: c.textPrimary,
      ),
      body: Column(
        children: [
          // Search
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 0),
            child: TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              style: TextStyle(color: c.textPrimary),
              decoration: InputDecoration(
                hintText: 'Search payments...',
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
          ),

          // Filters
          Padding(
            padding: const EdgeInsets.only(top: 14),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Row(
                children: _filters.map((filter) {
                  final isSelected = filter == _selectedFilter;
                  return Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: FilterChip(
                      label: Text(filter),
                      selected: isSelected,
                      onSelected: (_) {
                        setState(() => _selectedFilter = filter);
                      },
                      backgroundColor: c.surfaceCard,
                      selectedColor: c.primary,
                      side: BorderSide(color: c.border),
                      labelStyle: TextStyle(
                        color: isSelected ? Colors.white : c.textPrimary,
                        fontWeight: FontWeight.w500,
                      ),
                      checkmarkColor: Colors.white,
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Payments List
          Expanded(
            child: Consumer<ApiService>(
              builder: (context, api, _) {
                if (api.isLoading && api.payments.isEmpty) {
                  return Center(
                    child: CircularProgressIndicator(color: c.primary),
                  );
                }

                if (_filteredPayments.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(LucideIcons.wallet,
                            color: c.textSecondary, size: 64),
                        const SizedBox(height: 16),
                        Text(
                          'No payments found',
                          style:
                              TextStyle(color: c.textSecondary, fontSize: 16),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => api.fetchPayments(),
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    itemCount: _filteredPayments.length,
                    itemBuilder: (context, index) {
                      final payment = _filteredPayments[index];
                      return _PaymentCard(
                        payment: payment,
                        onTap: () =>
                            _showPaymentDetails(context, c, payment),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showPaymentDetails(
      BuildContext context, AppColors c, Map<String, dynamic> payment) {
    final statusColor = _getStatusColor(c, payment['status']);

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
                  backgroundColor: statusColor.withOpacity(0.12),
                  child: Icon(
                    _getMethodIcon(payment['method']),
                    color: statusColor,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    'Payment #${payment['id']}',
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
            _detailRow(c, 'Method', payment['method'] as String),
            _detailRow(c, 'Amount',
                money(payment['amount'] as double)),
            _detailRow(c, 'Status', payment['status'] as String,
                valueColor: statusColor),
            _detailRow(c, 'Date', _formatDate(payment['date'] as DateTime)),
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

  Widget _detailRow(AppColors c, String label, String value,
      {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: c.textSecondary, fontSize: 13)),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? c.textPrimary,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(AppColors c, String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return c.success;
      case 'pending':
        return c.warning;
      case 'failed':
        return c.danger;
      default:
        return c.textSecondary;
    }
  }

  IconData _getMethodIcon(String method) {
    switch (method.toLowerCase()) {
      case 'bkash':
      case 'nagad':
      case 'rocket':
      case 'upay':
        return LucideIcons.wallet;
      default:
        return LucideIcons.creditCard;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }
}

class _PaymentCard extends StatelessWidget {
  final Map<String, dynamic> payment;
  final VoidCallback onTap;

  const _PaymentCard({required this.payment, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final statusColor = _getStatusColor(c, payment['status']);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: statusColor.withOpacity(0.12),
                child: Icon(
                  _getMethodIcon(payment['method']),
                  color: statusColor,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      payment['method'],
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: c.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatDate(payment['date']),
                      style: TextStyle(
                        fontSize: 12,
                        color: c.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    money(payment['amount'] as double),
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: c.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    payment['status'],
                    style: TextStyle(
                      fontSize: 12,
                      color: statusColor,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _getStatusColor(AppColors c, String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return c.success;
      case 'pending':
        return c.warning;
      case 'failed':
        return c.danger;
      default:
        return c.textSecondary;
    }
  }

  IconData _getMethodIcon(String method) {
    switch (method.toLowerCase()) {
      case 'bkash':
      case 'nagad':
      case 'rocket':
      case 'upay':
        return LucideIcons.wallet;
      default:
        return LucideIcons.creditCard;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }
}
