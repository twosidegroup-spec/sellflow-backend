import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/format.dart';
import '../../theme/app_theme.dart';
import 'create_order_screen.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  String _selectedFilter = 'All';
  final _searchController = TextEditingController();
  final List<String> _filters = [
    'All',
    'Created',
    'Confirmed',
    'Packed',
    'Shipped',
    'Delivered',
    'Cancelled',
  ];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _filteredOrders {
    final api = context.read<ApiService>();
    var orders = api.orders.map((o) {
      return {
        'id': o.id,
        'status': o.status,
        'amount': o.totalAmount,
        'date': o.createdAt,
      };
    }).toList();

    if (_selectedFilter != 'All') {
      orders = orders
          .where((o) =>
              (o['status'] as String).toLowerCase() ==
              _selectedFilter.toLowerCase())
          .toList();
    }

    if (_searchController.text.isNotEmpty) {
      orders = orders.where((o) =>
          o['id'].toString().contains(_searchController.text) ||
          (o['status'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase())).toList();
    }

    return orders;
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
                  'Orders',
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
                    hintText: 'Search orders...',
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

          // Orders List
          Expanded(
            child: Consumer<ApiService>(
              builder: (context, api, _) {
                if (api.isLoading && api.orders.isEmpty) {
                  return Center(
                    child: CircularProgressIndicator(color: c.primary),
                  );
                }

                if (_filteredOrders.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(LucideIcons.receipt,
                            color: c.textSecondary, size: 64),
                        const SizedBox(height: 16),
                        Text(
                          'No orders found',
                          style: TextStyle(color: c.textSecondary, fontSize: 16),
                        ),
                        const SizedBox(height: 8),
                        TextButton.icon(
                          onPressed: () => Navigator.push(
                            context,
                            MaterialPageRoute(
                                builder: (_) => const CreateOrderScreen()),
                          ),
                          icon: const Icon(LucideIcons.plus),
                          label: const Text('Create Order'),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => api.fetchOrders(),
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    itemCount: _filteredOrders.length,
                    itemBuilder: (context, index) {
                      return _OrderCard(
                        order: _filteredOrders[index],
                        onTap: () => _showOrderDetails(
                            context, c, _filteredOrders[index]),
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
        heroTag: 'orders_fab',
        onPressed: () => Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => const CreateOrderScreen()),
        ),
        child: const Icon(LucideIcons.plus),
      ),
    );
  }

  void _showOrderDetails(
      BuildContext context, AppColors c, Map<String, dynamic> order) {
    final statusColor = _statusColor(c, order['status']);

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
            Text(
              'Order #${order['id']}',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: c.textPrimary,
              ),
            ),
            const SizedBox(height: 16),
            _detailRow(c, 'Status', order['status'] as String,
                valueColor: statusColor),
            _detailRow(c, 'Amount',
                money(order['amount'] as double)),
            _detailRow(c, 'Placed', _formatDate(order['date'] as DateTime)),
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

  Color _statusColor(AppColors c, String status) {
    switch (status.toLowerCase()) {
      case 'delivered':
        return c.success;
      case 'confirmed':
        return const Color(0xFF3B82F6);
      case 'packed':
        return const Color(0xFF8B5CF6);
      case 'shipped':
        return const Color(0xFF0EA5E9);
      case 'cancelled':
        return c.danger;
      default:
        return c.warning;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}

class _OrderCard extends StatelessWidget {
  final Map<String, dynamic> order;
  final VoidCallback onTap;

  const _OrderCard({required this.order, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final statusColor = _statusColor(c, order['status']);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Order #${order['id']}',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: c.textPrimary,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      order['status'],
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: statusColor,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    money(order['amount'] as double),
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: c.textPrimary,
                    ),
                  ),
                  Text(
                    _formatDate(order['date']),
                    style: TextStyle(
                      fontSize: 12,
                      color: c.textSecondary,
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

  Color _statusColor(AppColors c, String status) {
    switch (status.toLowerCase()) {
      case 'delivered':
        return c.success;
      case 'confirmed':
        return const Color(0xFF3B82F6);
      case 'packed':
        return const Color(0xFF8B5CF6);
      case 'shipped':
        return const Color(0xFF0EA5E9);
      case 'cancelled':
        return c.danger;
      default:
        return c.warning;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }
}
