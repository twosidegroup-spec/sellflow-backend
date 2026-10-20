import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/presentation/auth_controller.dart';
import 'features/auth/presentation/login_screen.dart';
import 'features/auth/presentation/register_screen.dart';
import 'features/dashboard/presentation/dashboard_screen.dart';

void main() => runApp(const ProviderScope(child: SellflowApp()));

class SellflowApp extends ConsumerWidget {
  const SellflowApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(authControllerProvider);

    Widget home;
    switch (state.status) {
      case AuthStatus.loading:
        home = const Scaffold(body: Center(child: CircularProgressIndicator(color: AppTheme.black)));
      case AuthStatus.authenticated:
        home = const DashboardScreen();
      case AuthStatus.locked:
      case AuthStatus.working:
        home = state.email == null ? const RegisterScreen() : const LoginScreen();
    }

    // Wrap in iPhone frame for desktop viewing
    final isDesktop = MediaQuery.of(context).size.width > 450;
    
    Widget appWidget = MaterialApp(
      title: 'SellFlow',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: home,
    );

    if (isDesktop) {
      appWidget = Center(
        child: iPhoneFrame(
          child: appWidget,
        ),
      );
    }

    return appWidget;
  }
}

class iPhoneFrame extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;

  const iPhoneFrame({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(5),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      // iPhone 14 Pro dimensions (393x852) + frame
      width: 403,
      height: 862,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(40),
        border: Border.all(color: Colors.black, width: 6),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 30,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(34),
        child: Container(
          color: AppTheme.background,
          child: child,
        ),
      ),
    );
  }
}

