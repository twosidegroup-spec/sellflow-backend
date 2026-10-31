import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:provider/provider.dart';

import '../shared/api_service.dart';
import '../../theme/app_theme.dart';
import '../customers/customers_screen.dart';
import '../orders/orders_screen.dart';
import '../payments/payments_screen.dart';
import '../settings/settings_screen.dart';
import '../auth/widgets/brand_logo.dart';

const _ink = Color(0xFF12203A);
const _muted = Color(0xFF64748B);
const _blue = Color(0xFF2563EB);
const _green = Color(0xFF16A34A);
const _orange = Color(0xFFF59E0B);
const _cardBorder = Color(0xFFE3EDF9);
const _iconCircle = Color(0xFFEAF3FE);

const _monthLabels = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

const _weekdayNames = [
  'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday',
];

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

String _axisMoney(double value) {
  if (value >= 1000000) return '${(value / 1000000).toStringAsFixed(1)}M';
  if (value >= 1000) return '${(value / 1000).toStringAsFixed(1)}K';
  return value.toStringAsFixed(0);
}

String _relativeDateTime(DateTime dt) {
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final day = DateTime(dt.year, dt.month, dt.day);
  final diff = today.difference(day).inDays;
  final hour = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
  final minute = dt.minute.toString().padLeft(2, '0');
  final ampm = dt.hour < 12 ? 'AM' : 'PM';
  final time = '$hour:$minute $ampm';
  if (diff == 0) return 'Today, $time';
  if (diff == 1) return 'Yesterday, $time';
  return '${_monthLabels[dt.month - 1]} ${dt.day}, $time';
}

double? _growthOf(List<double> values) {
  if (values.length < 4) return null;
  final mid = values.length ~/ 2;
  final prev = values.take(mid).fold<double>(0, (a, b) => a + b);
  final curr = values.skip(mid).fold<double>(0, (a, b) => a + b);
  if (prev <= 0) return curr > 0 ? 100 : null;
  return (curr - prev) / prev * 100;
}

String _initials(String name) {
  final parts = name.trim().split(RegExp(r'\s+'));
  if (parts.isEmpty || parts.first.isEmpty) return 'SF';
  if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
  return (parts.first.substring(0, 1) + parts.last.substring(0, 1))
      .toUpperCase();
}

const _avatarColors = [
  Color(0xFF3B82F6),
  Color(0xFF60A5FA),
  Color(0xFF8B5CF6),
  Color(0xFF34D399),
  Color(0xFFF59E0B),
  Color(0xFF14B8A6),
];

Color _avatarColor(String seed) {
  var hash = 0;
  for (final code in seed.codeUnits) {
    hash = (hash * 31 + code) & 0x7fffffff;
  }
  return _avatarColors[hash % _avatarColors.length];
}

class _MethodMeta {
  final String label;
  final String? asset;
  const _MethodMeta(this.label, [this.asset]);
}

const _methods = <String, _MethodMeta>{
  'bkash': _MethodMeta('bKash', 'assets/images/bkash.svg'),
  'nagad': _MethodMeta('Nagad', 'assets/images/nagad.svg'),
  'paypal': _MethodMeta('PayPal', 'assets/images/paypal.svg'),
  'cashapp': _MethodMeta('Cash App', 'assets/images/cashapp.svg'),
  'stripe': _MethodMeta('Stripe', 'assets/images/stripe.svg'),
  'rocket': _MethodMeta('Rocket'),
  'upay': _MethodMeta('Upay'),
  'wise': _MethodMeta('Wise'),
  'cash': _MethodMeta('Cash'),
};

class OverviewScreen extends StatefulWidget {
  const OverviewScreen({super.key});

  @override
  State<OverviewScreen> createState() => _OverviewScreenState();
}

class _OverviewScreenState extends State<OverviewScreen> {
  int _rangeDays = 7;
  int? _selectedDay;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _refresh();
    });
  }

  Future<void> _refresh() async {
    final api = context.read<ApiService>();
    await Future.wait([
      api.fetchSummary(),
      api.fetchOrders(),
      api.fetchProducts(),
      api.fetchCustomers(),
      api.fetchPayments(),
    ]);
  }

  static String _dayKey(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  /// Builds a daily revenue/orders series for the selected range from orders,
  /// falling back to the server's 7-day series when orders aren't loaded yet.
  List<DailyPoint> _series(ApiService api) {
    final orders = api.orders;
    final fallback = api.summary?.daily ?? const <DailyPoint>[];
    if (orders.isEmpty && fallback.isNotEmpty) return fallback;

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = today.subtract(Duration(days: _rangeDays - 1));
    final revenue = List<double>.filled(_rangeDays, 0);
    final counts = List<int>.filled(_rangeDays, 0);

    for (final order in orders) {
      final d = DateTime(
          order.createdAt.year, order.createdAt.month, order.createdAt.day);
      final idx = d.difference(start).inDays;
      if (idx >= 0 && idx < _rangeDays) {
        revenue[idx] += order.totalAmount;
        counts[idx] += 1;
      }
    }

    return [
      for (var i = 0; i < _rangeDays; i++)
        DailyPoint(
          date: _dayKey(start.add(Duration(days: i))),
          revenue: revenue[i],
          profit: 0,
          orders: counts[i],
        ),
    ];
  }

  /// Growth of a filtered order count vs the previous period.
  double? _countGrowth(ApiService api, bool Function(Order order) match) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = today.subtract(Duration(days: _rangeDays - 1));
    final prevStart = start.subtract(Duration(days: _rangeDays));
    var current = 0;
    var previous = 0;
    for (final order in api.orders) {
      if (!match(order)) continue;
      final d = DateTime(
          order.createdAt.year, order.createdAt.month, order.createdAt.day);
      if (!d.isBefore(start)) {
        current++;
      } else if (!d.isBefore(prevStart)) {
        previous++;
      }
    }
    if (previous <= 0) return current > 0 ? 100 : null;
    return (current - previous) / previous * 100;
  }

  /// Growth vs the previous period of the same length.
  double? _rangeGrowth(ApiService api) {
    final orders = api.orders;
    if (orders.isEmpty) {
      return _growthOf(
          _series(api).map((p) => p.revenue).toList(growable: false));
    }

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final start = today.subtract(Duration(days: _rangeDays - 1));
    final prevStart = start.subtract(Duration(days: _rangeDays));
    double current = 0;
    double previous = 0;
    for (final order in orders) {
      final d = DateTime(
          order.createdAt.year, order.createdAt.month, order.createdAt.day);
      if (!d.isBefore(start)) {
        current += order.totalAmount;
      } else if (!d.isBefore(prevStart)) {
        previous += order.totalAmount;
      }
    }
    if (previous <= 0) return current > 0 ? 100 : null;
    return (current - previous) / previous * 100;
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<ApiService>();

    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(
            'assets/images/overview_bg.png',
            fit: BoxFit.cover,
            alignment: Alignment.topCenter,
          ),
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              onRefresh: _refresh,
              color: _blue,
              backgroundColor: Colors.white,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(14, 8, 14, 28),
                children: [
                  _buildTopBar(context, api),
                  const SizedBox(height: 18),
                  _buildGreeting(context, api),
                  const SizedBox(height: 18),
                  _buildRevenueCard(context, api),
                  const SizedBox(height: 14),
                  _buildKpiGrid(context, api),
                  const SizedBox(height: 16),
                  _buildRecentTransactions(context, api),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, ApiService api) {
    final openOrders = api.orders.where((o) {
      final status = o.status.toLowerCase();
      return status != 'delivered' && status != 'cancelled';
    }).length;

    return Row(
      children: [
        const SFMLogo(markSize: 30, dark: false, horizontal: true),
        const Spacer(),
        Stack(
          clipBehavior: Clip.none,
          children: [
            InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: () => _showNotifications(context, api),
              child: const Padding(
                padding: EdgeInsets.all(5),
                child: Icon(LucideIcons.bell, size: 22, color: _ink),
              ),
            ),
            if (openOrders > 0)
              Positioned(
                right: 0,
                top: -1,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    openOrders > 99 ? '99+' : '$openOrders',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(width: 12),
        InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SettingsScreen()),
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 17,
                backgroundColor: _iconCircle,
                child: const Icon(LucideIcons.user, size: 18, color: _blue),
              ),
              const Icon(LucideIcons.chevronDown, size: 16, color: _muted),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildGreeting(BuildContext context, ApiService api) {
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Good morning,'
        : (hour < 17 ? 'Good afternoon,' : 'Good evening,');
    final name = api.currentUser?.fullName ?? 'Welcome';
    final now = DateTime.now();
    final dateLabel =
        '${_weekdayNames[now.weekday - 1]}, ${_monthLabels[now.month - 1]} ${now.day}, ${now.year}';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                greeting,
                style: const TextStyle(
                  fontSize: AppText.body,
                  fontWeight: FontWeight.w400,
                  color: _muted,
                ),
              ),
              const SizedBox(height: 2),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  '$name 👋',
                  maxLines: 1,
                  style: const TextStyle(
                    fontSize: AppText.greeting,
                    fontWeight: FontWeight.w600,
                    color: _ink,
                  ),
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                "Here's what's happening with your business today.",
                style: TextStyle(
                  fontSize: AppText.label,
                  fontWeight: FontWeight.w400,
                  color: _muted,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(LucideIcons.calendar, size: 13, color: _muted),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      dateLabel,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: AppText.label,
                        fontWeight: FontWeight.w500,
                        color: _muted,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(width: 10),
        GestureDetector(
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const SettingsScreen()),
          ),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.75),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: _cardBorder),
            ),
            child: const Row(
              children: [
                Icon(LucideIcons.badgeCheck, size: 15, color: _blue),
                SizedBox(width: 6),
                Text(
                  'Owner',
                  style: TextStyle(
                    fontSize: AppText.label,
                    fontWeight: FontWeight.w600,
                    color: _blue,
                  ),
                ),
                SizedBox(width: 2),
                Icon(LucideIcons.chevronRight, size: 15, color: _blue),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildRevenueCard(BuildContext context, ApiService api) {
    final series = _series(api);
    final growth = _rangeGrowth(api);
    final total = series.fold<double>(0, (sum, p) => sum + p.revenue);
    final selected = _selectedDay == null
        ? (series.isEmpty ? 0 : series.length - 1)
        : _selectedDay!.clamp(0, series.length - 1);

    return _Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: const BoxDecoration(
                  color: _iconCircle,
                  shape: BoxShape.circle,
                ),
                child: const Icon(LucideIcons.trendingUp,
                    size: 18, color: _blue),
              ),
              const SizedBox(width: 10),
              const Flexible(
                child: Text(
                  'Total Revenue',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: AppText.cardHeading,
                    fontWeight: FontWeight.w600,
                    color: _ink,
                  ),
                ),
              ),
              const SizedBox(width: 5),
              const Icon(LucideIcons.info, size: 14, color: _muted),
              const SizedBox(width: 6),
              PopupMenuButton<int>(
                initialValue: _rangeDays,
                tooltip: 'Select range',
                onSelected: (value) => setState(() {
                  _rangeDays = value;
                  _selectedDay = null;
                }),
                itemBuilder: (menuContext) => const [
                  PopupMenuItem(value: 7, child: Text('Last 7 days')),
                  PopupMenuItem(value: 14, child: Text('Last 14 days')),
                  PopupMenuItem(value: 30, child: Text('Last 30 days')),
                ],
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF4F8FD),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: _cardBorder),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Last $_rangeDays days',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w500,
                          color: _ink,
                        ),
                      ),
                      const SizedBox(width: 3),
                      const Icon(LucideIcons.chevronDown,
                          size: 13, color: _muted),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            _money(total),
            style: const TextStyle(
              fontSize: AppText.revenue,
              fontWeight: FontWeight.w700,
              color: _ink,
              fontFeatures: tabularFigures,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              if (growth != null) ...[
                const Icon(LucideIcons.arrowUp, size: 14, color: _green),
                const SizedBox(width: 3),
                Text(
                  '${growth.toStringAsFixed(1)}%',
                  style: const TextStyle(
                    fontSize: AppText.label,
                    fontWeight: FontWeight.w600,
                    color: _green,
                    fontFeatures: tabularFigures,
                  ),
                ),
                const SizedBox(width: 12),
              ],
              Text(
                'vs. previous $_rangeDays days',
                style: const TextStyle(
                  fontSize: AppText.label,
                  fontWeight: FontWeight.w400,
                  color: _muted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (series.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 46),
              child: Center(
                child: Text(
                  'No sales in the selected period',
                  style: TextStyle(fontSize: AppText.body, color: _muted),
                ),
              ),
            )
          else
            LayoutBuilder(
              builder: (context, constraints) {
                return GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onTapDown: (details) {
                    const left = 40.0, right = 6.0;
                    final plotW =
                        (constraints.maxWidth - left - right).clamp(1.0, double.infinity);
                    final n = series.length;
                    final idx = (((details.localPosition.dx - left) / plotW) *
                            (n - 1))
                        .round()
                        .clamp(0, n - 1);
                    setState(() => _selectedDay = idx);
                  },
                  child: SizedBox(
                    height: 176,
                    width: double.infinity,
                    child: CustomPaint(
                      painter: _RevenueChartPainter(
                        points: series,
                        selectedIndex: selected,
                      ),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  void _openOrders(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const OrdersScreen()),
    );
  }

  /// Bottom sheet with open orders (the bell badge source).
  void _showNotifications(BuildContext context, ApiService api) {
    final open = api.orders.where((o) {
      final s = o.status.toLowerCase();
      return s != 'delivered' && s != 'cancelled';
    }).take(8).toList();

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.fromLTRB(
          20, 16, 20, 24 + MediaQuery.of(sheetContext).padding.bottom),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Notifications',
              style: TextStyle(
                fontSize: AppText.cardHeading,
                fontWeight: FontWeight.w600,
                color: _ink,
              ),
            ),
            const SizedBox(height: 10),
            if (open.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 18),
                child: Row(
                  children: [
                    Icon(LucideIcons.check, size: 18, color: _green),
                    SizedBox(width: 10),
                    Text(
                      'All caught up — no open orders',
                      style: TextStyle(fontSize: AppText.body, color: _muted),
                    ),
                  ],
                ),
              )
            else
              for (final order in open)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xFFEAF3FE),
                    child: Icon(LucideIcons.receipt, size: 17, color: _blue),
                  ),
                  title: Text(
                    'Order #${order.id} is ${order.status}',
                    style: const TextStyle(
                      fontSize: AppText.body,
                      fontWeight: FontWeight.w500,
                      color: _ink,
                    ),
                  ),
                  subtitle: Text(
                    '${order.status} · ${_money(order.totalAmount)}',
                    style:
                        const TextStyle(fontSize: AppText.label, color: _muted),
                  ),
                  trailing: const Icon(LucideIcons.chevronRight,
                      size: 16, color: _muted),
                  onTap: () {
                    Navigator.pop(sheetContext);
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const OrdersScreen()),
                    );
                  },
                ),
          ],
        ),
      ),
    );
  }

  Widget _buildKpiGrid(BuildContext context, ApiService api) {
    final summary = api.summary;
    final daily = summary?.daily ?? const <DailyPoint>[];
    final orders = api.orders;
    final orderGrowth = _growthOf(
        daily.map((d) => d.orders.toDouble()).toList(growable: false));

    final paid = orders.where((o) {
      final s = o.status.toLowerCase();
      return s == 'paid' || s == 'delivered';
    }).length;
    final pending = orders.where((o) {
      final s = o.status.toLowerCase();
      return s != 'delivered' && s != 'cancelled';
    }).length;
    final deliveries =
        orders.where((o) => o.status.toLowerCase() == 'delivered').length;

    return Column(
      children: [
        SizedBox(
          height: 164,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.shoppingCart,
                  accent: _blue,
                  label: 'Total Orders',
                  value: '${summary?.totalOrders ?? orders.length}',
                  growth: orderGrowth,
                  onTap: () => _openOrders(context),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.circleDollarSign,
                  accent: _blue,
                  label: 'Paid Orders',
                  value: '$paid',
                  growth: _countGrowth(api, (o) {
                    final s = o.status.toLowerCase();
                    return s == 'paid' || s == 'delivered';
                  }),
                  onTap: () => _openOrders(context),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.clock,
                  accent: _orange,
                  label: 'Pending Orders',
                  value: '$pending',
                  onTap: () => _openOrders(context),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          height: 164,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.users,
                  accent: const Color(0xFF8B5CF6),
                  label: 'Total Customers',
                  value: '${api.customers.length}',
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) => const CustomersScreen()),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.truck,
                  accent: const Color(0xFF8B5CF6),
                  label: 'Deliveries',
                  value: '$deliveries',
                  onTap: () => _openOrders(context),
                ),
              ),
              Expanded(
                child: _KpiCard(
                  icon: LucideIcons.wallet,
                  accent: _blue,
                  label: 'Available Balance',
                  value: _money(summary?.totalProfit ?? 0),
                  actionLabel: 'View Details',
                  onAction: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const PaymentsScreen()),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRecentTransactions(BuildContext context, ApiService api) {
    final payments = api.payments.take(5).toList();

    return _Card(
      padding: const EdgeInsets.fromLTRB(14, 14, 8, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: Row(
              children: [
                const Expanded(
                  child: Text(
                    'Recent Transactions',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: AppText.cardHeading,
                      fontWeight: FontWeight.w600,
                      color: _ink,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                GestureDetector(
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const OrdersScreen()),
                  ),
                  child: const Row(
                    children: [
                      Text(
                        'View All',
                        style: TextStyle(
                          fontSize: AppText.label,
                          fontWeight: FontWeight.w500,
                          color: _blue,
                        ),
                      ),
                      Icon(LucideIcons.chevronRight, size: 15, color: _blue),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          if (payments.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 28),
              child: Center(
                child: Text(
                  'No transactions yet',
                  style: TextStyle(fontSize: AppText.label, color: _muted),
                ),
              ),
            )
          else
            ...payments.map((p) => _transactionRow(context, api, p)),
        ],
      ),
    );
  }

  ({String name, String email}) _customerFor(
      ApiService api, Payment payment) {
    for (final order in api.orders) {
      if (order.id == payment.orderId) {
        final id = order.customerId;
        if (id != null) {
          for (final customer in api.customers) {
            if (customer.id == id) {
              return (
                name: customer.name,
                email: customer.email?.isNotEmpty == true
                    ? customer.email!
                    : 'Customer #$id',
              );
            }
          }
        }
        return (name: 'Order #${order.id}', email: 'Order payment');
      }
    }
    return (name: 'Payment #${payment.id}', email: 'Received payment');
  }

  Widget _transactionRow(
      BuildContext context, ApiService api, Payment payment) {
    final customer = _customerFor(api, payment);
    final meta = _methods[payment.method.toLowerCase()] ??
        _MethodMeta(payment.method.toUpperCase());
    final when = payment.paidAt ?? payment.createdAt;

    return InkWell(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const OrdersScreen()),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 9, horizontal: 2),
        child: Row(
          children: [
            CircleAvatar(
              radius: 18,
              backgroundColor: _avatarColor(customer.name),
              child: Text(
                _initials(customer.name),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    customer.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: AppText.body,
                      fontWeight: FontWeight.w500,
                      color: _ink,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    customer.email,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: AppText.label,
                      fontWeight: FontWeight.w400,
                      color: _muted,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: const Color(0xFFF6F9FE),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: _cardBorder),
              ),
              child: Row(
                children: [
                  _MethodIcon(meta: meta),
                  if (meta.asset != null) const SizedBox(width: 5),
                  Text(
                    meta.label,
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: _ink,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '+ ${_money(payment.amount)}',
                  style: const TextStyle(
                    fontSize: AppText.label,
                    fontWeight: FontWeight.w600,
                    color: _green,
                    fontFeatures: tabularFigures,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _relativeDateTime(when),
                  style: const TextStyle(
                    fontSize: AppText.label,
                    fontWeight: FontWeight.w400,
                    color: _muted,
                  ),
                ),
              ],
            ),
            const Icon(LucideIcons.chevronRight, size: 16, color: _muted),
          ],
        ),
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final Widget child;
  final EdgeInsets padding;

  const _Card({
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.92),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: _cardBorder),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF7FB0DE).withOpacity(0.16),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _MethodIcon extends StatelessWidget {
  final _MethodMeta meta;

  const _MethodIcon({required this.meta});

  @override
  Widget build(BuildContext context) {
    if (meta.asset == null) {
      return const Icon(LucideIcons.creditCard, size: 13, color: _blue);
    }
    return SvgProviderIcon(asset: meta.asset!, label: meta.label);
  }
}

class _KpiCard extends StatelessWidget {
  final IconData icon;
  final Color accent;
  final String label;
  final String value;
  final double? growth;
  final String? actionLabel;
  final VoidCallback? onAction;
  final VoidCallback? onTap;

  const _KpiCard({
    required this.icon,
    required this.accent,
    required this.label,
    required this.value,
    this.growth,
    this.actionLabel,
    this.onAction,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Colors.white, Color(0xFFF6FAFF)],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _cardBorder),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF7FB0DE).withOpacity(0.16),
              blurRadius: 14,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: accent.withOpacity(0.13),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 18, color: accent),
            ),
            const SizedBox(height: 9),
            // One-line label that shrinks instead of wrapping or clipping.
            SizedBox(
              height: 15,
              child: FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  label,
                  maxLines: 1,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: _muted,
                    height: 1.1,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 3),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                value,
                maxLines: 1,
                style: const TextStyle(
                  fontSize: AppText.kpiValue,
                  fontWeight: FontWeight.w700,
                  color: _ink,
                  fontFeatures: tabularFigures,
                ),
              ),
            ),
            const SizedBox(height: 8),
            if (actionLabel != null)
              GestureDetector(
                onTap: onAction,
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0F6FE),
                    borderRadius: BorderRadius.circular(9),
                    border: Border.all(color: _cardBorder),
                  ),
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          actionLabel!,
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w500,
                            color: _blue,
                          ),
                        ),
                        const Icon(LucideIcons.chevronRight,
                            size: 14, color: _blue),
                      ],
                    ),
                  ),
                ),
              )
            else ...[
              SizedBox(
                height: 15,
                child: growth == null
                    ? null
                    : Row(
                        children: [
                          Icon(
                            growth! >= 0
                                ? LucideIcons.arrowUp
                                : LucideIcons.arrowUp,
                            size: 13,
                            color: growth! > 0 ? _green : _orange,
                          ),
                          const SizedBox(width: 3),
                          Flexible(
                            child: FittedBox(
                              fit: BoxFit.scaleDown,
                              alignment: Alignment.centerLeft,
                              child: Text(
                                '${growth!.toStringAsFixed(1)}%',
                                maxLines: 1,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: growth! > 0 ? _green : _orange,
                                  fontFeatures: tabularFigures,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
              ),
              const SizedBox(height: 2),
              const Text(
                'vs. last 7 days',
                maxLines: 1,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w400,
                  color: _muted,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

double _niceCeil(double v) {
  const steps = [
    1000.0, 2000.0, 5000.0, 10000.0, 20000.0, 50000.0,
    100000.0, 200000.0, 500000.0, 1000000.0,
  ];
  for (final s in steps) {
    if (v <= s) return s;
  }
  return (v / 1000000).ceil() * 1000000;
}

void _drawText(
  Canvas canvas,
  String text,
  Offset position,
  TextStyle style, {
  TextAlign align = TextAlign.left,
}) {
  final tp = TextPainter(
    text: TextSpan(text: text, style: style),
    textDirection: TextDirection.ltr,
    textAlign: align,
    maxLines: 1,
  )..layout();
  var dx = position.dx;
  if (align == TextAlign.center) dx -= tp.width / 2;
  if (align == TextAlign.right) dx -= tp.width;
  tp.paint(canvas, Offset(dx, position.dy));
}

class _RevenueChartPainter extends CustomPainter {
  final List<DailyPoint> points;
  final int selectedIndex;

  _RevenueChartPainter({required this.points, this.selectedIndex = -1});

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;

    const left = 40.0, right = 6.0, top = 26.0, bottom = 24.0;
    final plotW = (size.width - left - right).clamp(1.0, double.infinity);
    final plotH = (size.height - top - bottom).clamp(1.0, double.infinity);

    final maxRev =
        points.map((p) => p.revenue).fold<double>(0, (a, b) => a > b ? a : b);
    final niceMax = _niceCeil(maxRev);

    final gridPaint = Paint()
      ..color = const Color(0xFFE3EDF9)
      ..strokeWidth = 1;
    const labelStyle = TextStyle(
      fontFamily: AppText.family,
      fontSize: 10,
      fontWeight: FontWeight.w400,
      color: Color(0xFF94A3B8),
      fontFeatures: tabularFigures,
    );
    for (var i = 0; i <= 3; i++) {
      final y = top + plotH * i / 3;
      canvas.drawLine(
          Offset(left, y), Offset(size.width - right, y), gridPaint);
      _drawText(
        canvas,
        _axisMoney(niceMax * (3 - i) / 3),
        Offset(left - 8, y - 6),
        labelStyle,
        align: TextAlign.right,
      );
    }

    double xAt(int i) => points.length == 1
        ? left + plotW / 2
        : left + plotW * i / (points.length - 1);
    double yRev(double v) => top +
        plotH -
        (niceMax <= 0 ? 0 : (v / niceMax).clamp(0.0, 1.0) * plotH);

    final pts = [
      for (var i = 0; i < points.length; i++)
        Offset(xAt(i), yRev(points[i].revenue)),
    ];

    final linePath = Path()..moveTo(pts.first.dx, pts.first.dy);
    for (var i = 0; i < pts.length - 1; i++) {
      final p1 = pts[i];
      final p2 = pts[i + 1];
      final midX = (p1.dx + p2.dx) / 2;
      linePath.cubicTo(midX, p1.dy, midX, p2.dy, p2.dx, p2.dy);
    }

    final areaPath = Path.from(linePath)
      ..lineTo(pts.last.dx, top + plotH)
      ..lineTo(pts.first.dx, top + plotH)
      ..close();
    canvas.drawPath(
      areaPath,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0x552563EB), Color(0x0A2563EB)],
        ).createShader(Rect.fromLTWH(left, top, plotW, plotH)),
    );

    canvas.drawPath(
      linePath,
      Paint()
        ..color = _blue
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );

    // Skip labels that would collide when the chart is narrow.
    final slot = points.length <= 1 ? plotW : plotW / (points.length - 1);
    final step = (44 / slot).ceil().clamp(1, points.length);
    for (var i = 0; i < points.length; i++) {
      if (i % step != 0 && i != points.length - 1) continue;
      final d = DateTime.tryParse(points[i].date);
      if (d == null) continue;
      _drawText(
        canvas,
        '${_monthLabels[d.month - 1]} ${d.day}',
        Offset(xAt(i), size.height - 16),
        labelStyle,
        align: TextAlign.center,
      );
    }

    final sel = (selectedIndex < 0 || selectedIndex >= points.length)
        ? points.length - 1
        : selectedIndex;
    final marker = pts[sel];
    canvas.drawCircle(marker, 5, Paint()..color = Colors.white);
    canvas.drawCircle(
      marker,
      5,
      Paint()
        ..color = _blue
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.4,
    );

    final tooltipText = _money(points[sel].revenue);
    final tp = TextPainter(
      text: TextSpan(
        text: tooltipText,
        style: const TextStyle(
          fontFamily: AppText.family,
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: _ink,
          fontFeatures: tabularFigures,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    const padH = 8.0, padV = 6.0;
    final boxW = tp.width + padH * 2;
    final boxH = tp.height + padV * 2;
    final bx = (marker.dx - boxW / 2)
        .clamp(left, size.width - right - boxW)
        .toDouble();
    final by =
        (marker.dy - boxH - 12).clamp(0.0, size.height - boxH).toDouble();
    final rect = Rect.fromLTWH(bx, by, boxW, boxH);
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(8)),
      Paint()..color = Colors.white,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(8)),
      Paint()
        ..color = const Color(0xFFD5E6F8)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );
    tp.paint(canvas, Offset(bx + padH, by + padV));
  }

  @override
  bool shouldRepaint(covariant _RevenueChartPainter old) =>
      old.points != points || old.selectedIndex != selectedIndex;
}

/// Small inline renderer for provider logos in the transaction chips.
class SvgProviderIcon extends StatelessWidget {
  final String asset;
  final String label;

  const SvgProviderIcon({
    super.key,
    required this.asset,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 14,
      height: 14,
      child: SvgPicture.asset(
        asset,
        fit: BoxFit.contain,
        semanticsLabel: label,
      ),
    );
  }
}
