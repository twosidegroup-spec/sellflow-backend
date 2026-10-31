import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sfm/features/auth/login_screen.dart';
import 'package:sfm/features/auth/registration_screen.dart';
import 'package:sfm/features/orders/orders_screen.dart';
import 'package:sfm/features/overview/overview_screen.dart';
import 'package:sfm/features/settings/settings_screen.dart';
import 'package:sfm/features/shared/api_service.dart';
import 'package:sfm/features/shared/settings_controller.dart';
import 'package:sfm/theme/app_theme.dart';
import 'package:sfm/theme/theme_controller.dart';

void main() {
  test('Registering with an existing email signs in when passcode matches',
      () async {
    SharedPreferences.setMockInitialValues({});
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/auth/register')) {
        return http.Response(
            jsonEncode({'detail': 'Email already registered'}), 400);
      }
      if (path.endsWith('/auth/login')) {
        return http.Response(
            jsonEncode({'access_token': 'tok123', 'token_type': 'bearer'}),
            200);
      }
      if (path.endsWith('/auth/me')) {
        return http.Response(
            jsonEncode({
              'id': 1,
              'email': 'sajid@example.com',
              'full_name': 'Sajid',
            }),
            200);
      }
      return http.Response('{}', 404);
    });

    final api = ApiService(client);
    final ok = await api.register('sajid@example.com', '1234', 'Sajid');

    expect(ok, isTrue);
    expect(api.isAuthenticated, isTrue);
    expect(api.error, isNull);
  });

  test('Registering with an existing email and wrong passcode explains clearly',
      () async {
    SharedPreferences.setMockInitialValues({});
    final client = MockClient((request) async {
      final path = request.url.path;
      if (path.endsWith('/auth/register')) {
        return http.Response(
            jsonEncode({'detail': 'Email already registered'}), 400);
      }
      if (path.endsWith('/auth/login')) {
        return http.Response(jsonEncode({'detail': 'Incorrect passcode'}), 401);
      }
      return http.Response('{}', 404);
    });

    final api = ApiService(client);
    final ok = await api.register('sajid@example.com', '9999', 'Sajid');

    expect(ok, isFalse);
    expect(api.error, contains('already registered'));
  });

  testWidgets('Orders FAB opens the New Order screen', (tester) async {
    tester.view.physicalSize = const Size(430, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ChangeNotifierProvider<ApiService>.value(
        value: ApiService(),
        child: const MaterialApp(home: OrdersScreen()),
      ),
    );
    await tester.pump();

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(find.text('New Order'), findsOneWidget);
    expect(find.text('Create Order'), findsOneWidget);
  });

  testWidgets('Reconciliation is gone - settings has auto detection toggle',
      (tester) async {
    tester.view.physicalSize = const Size(430, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ApiService>.value(value: ApiService()),
          ChangeNotifierProvider<ThemeController>.value(
              value: ThemeController()),
          ChangeNotifierProvider<SettingsController>.value(
              value: SettingsController()),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const SettingsScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Auto Payment Detection'), findsOneWidget);
    expect(find.text('Payment Reconciliation'), findsNothing);
  });

  testWidgets('Overview hides Live Payments even when auto detection is on',
      (tester) async {
    tester.view.physicalSize = const Size(430, 1400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    SharedPreferences.setMockInitialValues(
        {'settings_payment_detection': true});
    final settings = SettingsController();
    await settings.initialize();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ApiService>.value(value: ApiService()),
          ChangeNotifierProvider<SettingsController>.value(value: settings),
        ],
        child: const MaterialApp(home: OverviewScreen()),
      ),
    );
    await tester.pump();

    expect(find.text('Live Payments'), findsNothing);
    expect(find.text('Listening'), findsNothing);

    await settings.setPaymentDetection(false);
    await tester.pump();
  });

  test('API models parse Decimal-as-string values from the backend', () {
    final summary = DashboardSummary.fromJson({
      'today_revenue': '800.00',
      'today_profit': '240.00',
      'today_orders': 2,
      'total_revenue': '1200.50',
      'total_profit': '300.25',
      'total_orders': 5,
      'pending_deliveries': 1,
      'daily': [
        {
          'date': '2026-10-23',
          'revenue': '800.00',
          'profit': '240.00',
          'orders': 2,
        },
      ],
    });
    expect(summary.todayRevenue, 800.0);
    expect(summary.totalRevenue, 1200.5);
    expect(summary.totalProfit, 300.25);
    expect(summary.daily.single.revenue, 800.0);

    final order = Order.fromJson({
      'id': 1,
      'status': 'created',
      'total_amount': '450.00',
      'created_at': '2026-10-23T10:00:00Z',
    });
    expect(order.totalAmount, 450.0);

    final product = Product.fromJson({
      'id': 1,
      'name': 'Rice',
      'sku': 'R1',
      'selling_price': '75.50',
      'stock_quantity': 10,
    });
    expect(product.sellingPrice, 75.5);

    final payment = Payment.fromJson({
      'id': 1,
      'method': 'bkash',
      'amount': '500.00',
      'status': 'completed',
      'created_at': '2026-10-23T10:00:00Z',
    });
    expect(payment.amount, 500.0);
  });

  testWidgets('Settings offers Light, Dark and System theme modes',
      (tester) async {
    tester.view.physicalSize = const Size(430, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ApiService>.value(value: ApiService()),
          ChangeNotifierProvider<ThemeController>.value(
              value: ThemeController()),
          ChangeNotifierProvider<SettingsController>.value(
              value: SettingsController()),
        ],
        child: MaterialApp(
          theme: AppTheme.lightTheme,
          home: const SettingsScreen(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Appearance'), findsOneWidget);
    expect(find.text('Light'), findsOneWidget);
    expect(find.text('Dark'), findsOneWidget);
    expect(find.text('System'), findsOneWidget);
  });

  testWidgets('Overview screen renders revenue, KPI grid and transactions',
      (tester) async {
    tester.view.physicalSize = const Size(430, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ApiService>.value(value: ApiService()),
          ChangeNotifierProvider<SettingsController>.value(
              value: SettingsController()),
        ],
        child: const MaterialApp(home: OverviewScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Total Revenue'), findsOneWidget);
    expect(find.text('Total Orders'), findsOneWidget);
    expect(find.text('Available Balance'), findsOneWidget);
    expect(find.text('Recent Transactions'), findsOneWidget);
  });

  testWidgets('Overview range selector switches the analytics window',
      (tester) async {
    tester.view.physicalSize = const Size(430, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ApiService>.value(value: ApiService()),
          ChangeNotifierProvider<SettingsController>.value(
              value: SettingsController()),
        ],
        child: const MaterialApp(home: OverviewScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Last 7 days'), findsOneWidget);

    await tester.tap(find.text('Last 7 days'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Last 30 days').last);
    await tester.pumpAndSettle();

    expect(find.text('Last 30 days'), findsOneWidget);
  });

  testWidgets('Login screen fully fits a short browser viewport',
      (tester) async {
    // Simulate a browser window SHORTER than the 812px phone frame
    tester.view.physicalSize = const Size(430, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ChangeNotifierProvider<ApiService>.value(
        value: ApiService(),
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    // The "Register" link must be inside the viewport (not clipped off-screen)
    final registerFinder = find.byWidgetPredicate(
      (w) => w is RichText && w.text.toPlainText().contains('Register'),
    );
    expect(registerFinder, findsOneWidget);
    final registerRect = tester.getRect(registerFinder);
    expect(
      registerRect.bottom,
      lessThanOrEqualTo(700),
      reason: 'The Register link must be visible, not clipped below the window',
    );

    // Footer credit must be visible too
    final creditRect = tester.getRect(find.text('Powered by TSGI'));
    expect(creditRect.bottom, lessThanOrEqualTo(700));
  });

  testWidgets('Registration step 1 renders account, PIN and payment options',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(home: RegistrationScreen()));

    expect(find.text('SELLFLOW'), findsOneWidget);
    expect(find.text('Create Your Account'), findsOneWidget);
    expect(find.text('Full Name'), findsOneWidget);
    expect(find.text('Business Name'), findsOneWidget);
    expect(find.text('Email Address'), findsOneWidget);
    expect(find.text('Choose Your Payment Provider'), findsOneWidget);
    expect(find.text('bKash'), findsOneWidget);
    expect(find.text('Nagad'), findsOneWidget);
    expect(find.text('PayPal'), findsOneWidget);
    expect(find.text('Cash App'), findsOneWidget);
    expect(find.text('Stripe'), findsOneWidget);
    expect(find.text('Next'), findsOneWidget);
    expect(find.text('bKash Number'), findsOneWidget);

    // Background image + five SVG provider logos render
    expect(find.byType(Image), findsNWidgets(1));
    expect(find.byType(SvgPicture), findsNWidgets(5));
    final svgAssets = tester
        .widgetList<SvgPicture>(find.byType(SvgPicture))
        .map((w) => w.bytesLoader)
        .whereType<SvgAssetLoader>()
        .map((l) => l.assetName)
        .toSet();
    expect(svgAssets, contains('assets/images/bkash.svg'));
    expect(svgAssets, contains('assets/images/nagad.svg'));
    expect(svgAssets, contains('assets/images/paypal.svg'));
    expect(svgAssets, contains('assets/images/cashapp.svg'));
    expect(svgAssets, contains('assets/images/stripe.svg'));
  });

  testWidgets('Selecting a payment method asks for the matching number',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(home: RegistrationScreen()));

    expect(
        find.byKey(const ValueKey('payment-selected-bkash')), findsOneWidget);
    expect(find.byKey(const ValueKey('payment-selected-nagad')), findsNothing);
    expect(find.text('bKash Number'), findsOneWidget);

    await tester.ensureVisible(find.text('Nagad'));
    await tester.tap(find.text('Nagad'));
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey('payment-selected-nagad')), findsOneWidget);
    expect(find.byKey(const ValueKey('payment-selected-bkash')), findsNothing);
    expect(find.text('Nagad Number'), findsOneWidget);

    await tester.ensureVisible(find.text('PayPal'));
    await tester.tap(find.text('PayPal'));
    await tester.pumpAndSettle();

    expect(find.text('PayPal Email'), findsOneWidget);
    expect(find.text('Nagad Number'), findsNothing);
  });

  testWidgets('Registration continues to the passcode creation step',
      (tester) async {
    await tester.pumpWidget(const MaterialApp(home: RegistrationScreen()));

    await tester.enterText(find.byType(TextField).at(0), 'Sajid Ahmed');
    await tester.enterText(find.byType(TextField).at(1), 'SFM Store');
    await tester.enterText(
        find.byType(TextField).at(2), 'sajid@example.com');
    await tester.enterText(find.byType(TextField).at(3), '01712345678');

    await tester.ensureVisible(find.text('Next'));
    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Create Your Passcode'), findsOneWidget);
    expect(find.text('Choose a 4-digit PIN to secure your account'),
        findsOneWidget);
    // Circular keypad is present
    expect(find.text('5'), findsOneWidget);
    expect(find.text('0'), findsOneWidget);
  });
}
