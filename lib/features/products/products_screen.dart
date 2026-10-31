import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../shared/format.dart';
import '../../theme/app_theme.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  String _selectedFilter = 'All';
  final _searchController = TextEditingController();
  final List<String> _filters = [
    'All',
    'In Stock',
    'Low Stock',
    'Out of Stock'
  ];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, dynamic>> get _filteredProducts {
    final api = context.read<ApiService>();
    var products = api.products.map((p) {
      return {
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'stock': p.stockQuantity,
        'price': p.sellingPrice,
      };
    }).toList();

    if (_selectedFilter != 'All') {
      if (_selectedFilter == 'In Stock') {
        products = products.where((p) => (p['stock'] as int) > 0).toList();
      } else if (_selectedFilter == 'Low Stock') {
        products = products
            .where((p) => (p['stock'] as int) > 0 && (p['stock'] as int) < 10)
            .toList();
      } else if (_selectedFilter == 'Out of Stock') {
        products = products.where((p) => (p['stock'] as int) == 0).toList();
      }
    }

    if (_searchController.text.isNotEmpty) {
      products = products.where((p) =>
          (p['name'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase()) ||
          (p['sku'] as String)
              .toLowerCase()
              .contains(_searchController.text.toLowerCase())).toList();
    }

    return products;
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
                  'Products',
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
                    hintText: 'Search products...',
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

          // Products Grid
          Expanded(
            child: Consumer<ApiService>(
              builder: (context, api, _) {
                if (api.isLoading && api.products.isEmpty) {
                  return Center(
                    child: CircularProgressIndicator(color: c.primary),
                  );
                }

                if (_filteredProducts.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(LucideIcons.package,
                            color: c.textSecondary, size: 64),
                        const SizedBox(height: 16),
                        Text(
                          'No products found',
                          style: TextStyle(color: c.textSecondary, fontSize: 16),
                        ),
                        const SizedBox(height: 8),
                        TextButton.icon(
                          onPressed: () => _showCreateProductDialog(api),
                          icon: const Icon(LucideIcons.plus),
                          label: const Text('Add Product'),
                        ),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: () => api.fetchProducts(),
                  child: GridView.builder(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 88),
                    gridDelegate:
                        const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 0.78,
                    ),
                    itemCount: _filteredProducts.length,
                    itemBuilder: (context, index) {
                      final product = _filteredProducts[index];
                      return _ProductCard(
                        product: product,
                        onTap: () =>
                            _showProductDetails(context, c, api, product),
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
        heroTag: 'products_fab',
        onPressed: () => _showCreateProductDialog(context.read<ApiService>()),
        child: const Icon(LucideIcons.plus),
      ),
    );
  }

  void _showProductDetails(BuildContext context, AppColors c, ApiService api,
      Map<String, dynamic> product) {
    final stock = product['stock'] as int;
    final stockColor =
        stock == 0 ? c.danger : (stock < 10 ? c.warning : c.success);
    final stockController = TextEditingController(text: '$stock');

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: c.surfaceCard,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.fromLTRB(
            24,
            20,
            24,
            24 +
                MediaQuery.of(sheetContext).viewInsets.bottom +
                MediaQuery.of(sheetContext).padding.bottom),
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
              product['name'],
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: c.textPrimary,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'SKU: ${product['sku']}',
              style: TextStyle(color: c.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  money(product['price'] as double),
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: c.primary,
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: stockColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    stock == 0 ? 'Out of stock' : 'Stock: $stock',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: stockColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text(
              'Update stock',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: c.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: stockController,
                    keyboardType: TextInputType.number,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(6),
                    ],
                    style: TextStyle(color: c.textPrimary),
                    decoration: _fieldDecoration(c, hint: 'Quantity'),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  height: 48,
                  child: FilledButton(
                    onPressed: () async {
                      final quantity = int.tryParse(stockController.text);
                      if (quantity == null) return;
                      final ok = await api.updateProductStock(
                          product['id'] as int, quantity);
                      if (sheetContext.mounted) Navigator.pop(sheetContext);
                      _toast(ok ? 'Stock updated' : 'Could not update stock');
                    },
                    child: const Text('Save'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showCreateProductDialog(ApiService api) async {
    final c = AppColors.of(context);
    final nameController = TextEditingController();
    final skuController = TextEditingController();
    final costController = TextEditingController();
    final priceController = TextEditingController();
    final stockController = TextEditingController();

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Add Product'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                autofocus: true,
                style: TextStyle(color: c.textPrimary),
                decoration: _fieldDecoration(c, hint: 'Product name'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: skuController,
                style: TextStyle(color: c.textPrimary),
                decoration: _fieldDecoration(c, hint: 'SKU / code'),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: costController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                            RegExp(r'^\d*\.?\d{0,2}')),
                      ],
                      style: TextStyle(color: c.textPrimary),
                      decoration: _fieldDecoration(c, hint: 'Cost ৳'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: priceController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      inputFormatters: [
                        FilteringTextInputFormatter.allow(
                            RegExp(r'^\d*\.?\d{0,2}')),
                      ],
                      style: TextStyle(color: c.textPrimary),
                      decoration: _fieldDecoration(c, hint: 'Sell ৳'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: stockController,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
                style: TextStyle(color: c.textPrimary),
                decoration: _fieldDecoration(c, hint: 'Stock quantity'),
              ),
            ],
          ),
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
    final sku = skuController.text.trim();
    final cost = double.tryParse(costController.text) ?? 0;
    final price = double.tryParse(priceController.text) ?? 0;
    final stock = int.tryParse(stockController.text) ?? 0;

    if (name.isEmpty || sku.isEmpty) {
      _toast('Please enter a name and SKU');
      return;
    }
    if (price <= 0) {
      _toast('Please enter a selling price');
      return;
    }

    final ok = await api.createProduct(
      name: name,
      sku: sku,
      costPrice: cost,
      sellingPrice: price,
      stockQuantity: stock,
    );
    _toast(ok ? 'Product added' : 'Could not add product');
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

class _ProductCard extends StatelessWidget {
  final Map<String, dynamic> product;
  final VoidCallback onTap;

  const _ProductCard({required this.product, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);
    final stock = product['stock'] as int;
    final stockColor =
        stock == 0 ? c.danger : (stock < 10 ? c.warning : c.success);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Placeholder image
            Expanded(
              child: Container(
                width: double.infinity,
                color: c.surfaceElevated,
                child: Icon(
                  LucideIcons.package,
                  color: c.textSecondary,
                  size: 40,
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product['name'],
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: c.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    money(product['price'] as double),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: c.primary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(
                        LucideIcons.package,
                        color: stockColor,
                        size: 16,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Stock: $stock',
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
          ],
        ),
      ),
    );
  }
}
