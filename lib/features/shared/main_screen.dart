import 'package:flutter/material.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';
import '../shared/api_service.dart';
import '../../theme/app_theme.dart';
import '../overview/overview_screen.dart';
import '../orders/orders_screen.dart';
import '../customers/customers_screen.dart';
import '../products/products_screen.dart';
import '../settings/settings_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const OverviewScreen(),
    const ProductsScreen(),
    const OrdersScreen(),
    const CustomersScreen(),
    const SettingsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    // Fetch initial data
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final api = context.read<ApiService>();
      api.fetchSummary();
      api.fetchProducts();
      api.fetchOrders();
      api.fetchCustomers();
      api.fetchPayments();
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = AppColors.of(context);

    return Scaffold(
      backgroundColor: c.surface,
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: c.surfaceCard,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 8,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          type: BottomNavigationBarType.fixed,
          backgroundColor: Colors.transparent,
          selectedItemColor: c.primary,
          unselectedItemColor: c.textSecondary,
          selectedFontSize: AppText.nav - 1,
          unselectedFontSize: AppText.nav - 1,
          selectedLabelStyle: const TextStyle(
            fontSize: AppText.nav - 1,
            fontWeight: FontWeight.w500,
          ),
          unselectedLabelStyle: const TextStyle(
            fontSize: AppText.nav - 1,
            fontWeight: FontWeight.w500,
          ),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.home),
              activeIcon: Icon(LucideIcons.home),
              label: 'Overview',
            ),
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.package),
              activeIcon: Icon(LucideIcons.package),
              label: 'Products',
            ),
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.receipt),
              activeIcon: Icon(LucideIcons.receipt),
              label: 'Orders',
            ),
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.users),
              activeIcon: Icon(LucideIcons.users),
              label: 'Customers',
            ),
            BottomNavigationBarItem(
              icon: Icon(LucideIcons.settings),
              activeIcon: Icon(LucideIcons.settings),
              label: 'Settings',
            ),
          ],
        ),
      ),
    );
  }
}
