import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../../theme/app_theme.dart';

class _ItemEntry {
  Product? product;
  int quantity = 1;
}

class CreateOrderScreen extends StatefulWidget {
  const CreateOrderScreen({super.key});

  @override
  State<CreateOrderScreen> createState() => _CreateOrderScreenState();
}

class _CreateOrderScreenState extends State<CreateOrderScreen> {
  int? _customerId;
  final List<_ItemEntry> _items = [_ItemEntry()];
  final _deliveryController = TextEditingController();
  final _discountController = TextEditingController();
  final _notesController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _deliveryController.dispose();
    _discountController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  double get _subtotal => _items.fold(
      0, (sum, item) => sum + (item.product?.sellingPrice ?? 0) * item.quantity);
  double get _delivery => double.tryParse(_deliveryController.text) ?? 0;
  double get _discount => double.tryParse(_discountController.text) ?? 0;
  double get _total => _subtotal + _delivery - _discount;

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final api = context.watch<ApiService>();
    final products =
        api.products.where((p) => p.stockQuantity > 0).toList();

    return Scaffold(
      backgroundColor: c.surface,
      appBar: AppBar(
        title: const Text('New Order'),
        backgroundColor: c.surface,
        foregroundColor: c.textPrimary,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
        children: [
          // Customer
          Text(
            'Customer',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: c.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<int?>(
            initialValue: _customerId,
            dropdownColor: c.surfaceCard,
            style: TextStyle(color: c.textPrimary, fontSize: 14),
            decoration: _fieldDecoration(c, hint: 'Walk-in customer'),
            items: [
              DropdownMenuItem<int?>(
                value: null,
                child: Text(
                  'Walk-in customer',
                  style: TextStyle(color: c.textPrimary),
                ),
              ),
              ...api.customers.map(
                (customer) => DropdownMenuItem<int?>(
                  value: customer.id,
                  child: Text(
                    customer.name,
                    style: TextStyle(color: c.textPrimary),
                  ),
                ),
              ),
            ],
            onChanged: (value) => setState(() => _customerId = value),
          ),
          const SizedBox(height: 20),

          // Items
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Items',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: c.textPrimary,
                ),
              ),
              TextButton.icon(
                onPressed: () => setState(() => _items.add(_ItemEntry())),
                icon: const Icon(LucideIcons.plus, size: 18),
                label: const Text('Add item'),
              ),
            ],
          ),
          if (products.isEmpty)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: c.surfaceCard,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: c.border),
              ),
              child: Row(
                children: [
                  Icon(LucideIcons.package,
                      color: c.textSecondary, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'No products in stock. Add products first.',
                      style: TextStyle(color: c.textSecondary, fontSize: 13),
                    ),
                  ),
                ],
              ),
            )
          else
            ..._items.asMap().entries.map((entry) =>
                _buildItemRow(c, entry.key, entry.value, products)),
          const SizedBox(height: 20),

          // Fees
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _deliveryController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                        RegExp(r'^\d*\.?\d{0,2}')),
                  ],
                  onChanged: (_) => setState(() {}),
                  style: TextStyle(color: c.textPrimary),
                  decoration: _fieldDecoration(c, hint: 'Delivery fee ৳'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _discountController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                        RegExp(r'^\d*\.?\d{0,2}')),
                  ],
                  onChanged: (_) => setState(() {}),
                  style: TextStyle(color: c.textPrimary),
                  decoration: _fieldDecoration(c, hint: 'Discount ৳'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            maxLines: 2,
            style: TextStyle(color: c.textPrimary),
            decoration: _fieldDecoration(c, hint: 'Notes (optional)'),
          ),
          const SizedBox(height: 20),

          // Summary
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: c.surfaceCard,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: c.border),
            ),
            child: Column(
              children: [
                _summaryRow(c, 'Subtotal', _money(_subtotal)),
                _summaryRow(c, 'Delivery fee', _money(_delivery)),
                _summaryRow(c, 'Discount', '-${_money(_discount)}'),
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Container(height: 1, color: c.divider),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Total',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: c.textPrimary,
                      ),
                    ),
                    Text(
                      _money(_total),
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: c.primary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          SizedBox(
            height: 52,
            child: FilledButton(
              onPressed: _submitting ? null : () => _submit(api, products),
              child: _submitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Text('Create Order'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildItemRow(
      AppColors c, int index, _ItemEntry entry, List<Product> products) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: c.surfaceCard,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: c.border),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: DropdownButtonHideUnderline(
                  child: DropdownButton<Product>(
                    value: entry.product,
                    isExpanded: true,
                    dropdownColor: c.surfaceCard,
                    hint: Text(
                      'Select product',
                      style: TextStyle(color: c.textSecondary, fontSize: 14),
                    ),
                    style: TextStyle(color: c.textPrimary, fontSize: 14),
                    items: products
                        .map(
                          (p) => DropdownMenuItem<Product>(
                            value: p,
                            child: Text(
                              '${p.name} — ${_money(p.sellingPrice)} (${p.stockQuantity} left)',
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                  color: c.textPrimary, fontSize: 13),
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        setState(() => entry.product = value),
                  ),
                ),
              ),
              if (_items.length > 1)
                IconButton(
                  icon: Icon(LucideIcons.x, size: 18, color: c.textSecondary),
                  onPressed: () => setState(() => _items.removeAt(index)),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  IconButton(
                    icon: Icon(LucideIcons.circleMinus,
                        size: 22, color: c.primary),
                    onPressed: entry.quantity > 1
                        ? () => setState(() => entry.quantity--)
                        : null,
                  ),
                  Text(
                    '${entry.quantity}',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: c.textPrimary,
                    ),
                  ),
                  IconButton(
                    icon: Icon(LucideIcons.circlePlus,
                        size: 22, color: c.primary),
                    onPressed: entry.product != null &&
                            entry.quantity < entry.product!.stockQuantity
                        ? () => setState(() => entry.quantity++)
                        : null,
                  ),
                ],
              ),
              Text(
                _money((entry.product?.sellingPrice ?? 0) * entry.quantity),
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: c.textPrimary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _summaryRow(AppColors c, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label,
              style: TextStyle(fontSize: 13, color: c.textSecondary)),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: c.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submit(ApiService api, List<Product> products) async {
    final selected = _items.where((i) => i.product != null).toList();

    if (selected.isEmpty) {
      _toast('Add at least one product');
      return;
    }
    for (final entry in selected) {
      if (entry.quantity < 1) {
        _toast('Quantity must be at least 1');
        return;
      }
    }

    setState(() => _submitting = true);

    final ok = await api.createOrder(
      customerId: _customerId,
      items: selected
          .map((entry) => {
                'product_id': entry.product!.id,
                'product_name': entry.product!.name,
                'quantity': entry.quantity,
                'unit_price': entry.product!.sellingPrice,
                'unit_cost': entry.product!.costPrice,
              })
          .toList(),
      deliveryFee: _delivery,
      discount: _discount,
      notes: _notesController.text.trim(),
    );

    if (!mounted) return;

    setState(() => _submitting = false);

    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Order created')),
      );
      Navigator.pop(context);
    } else {
      _toast('Could not create order');
    }
  }

  void _toast(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
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

  String _money(double value) {
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
}
