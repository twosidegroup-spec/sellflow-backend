import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'features/shared/api_service.dart';
import 'features/shared/keypad_sound.dart';
import 'features/shared/settings_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/widgets/iphone_frame.dart';
import 'features/shared/main_screen.dart';
import 'theme/app_theme.dart';
import 'theme/theme_controller.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Mobile-first: portrait only, edge-to-edge with light chrome to match
  // the app's white / ice-blue surfaces.
  SystemChrome.setPreferredOrientations(const [
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      systemNavigationBarColor: Colors.transparent,
      systemNavigationBarIconBrightness: Brightness.dark,
      systemNavigationBarDividerColor: Colors.transparent,
    ),
  );

  // Preload keypad sounds so the first tap is instant.
  KeypadSound.prime();

  runApp(const SellflowApp());
}

class SellflowApp extends StatelessWidget {
  const SellflowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<ApiService>(
          create: (_) => ApiService()..initialize(),
        ),
        ChangeNotifierProvider<ThemeController>(
          create: (_) => ThemeController()..initialize(),
        ),
        ChangeNotifierProvider<SettingsController>(
          create: (_) => SettingsController()..initialize(),
        ),
      ],
      child: Consumer<ThemeController>(
        builder: (context, themeController, _) {
          return MaterialApp(
            title: 'SELLFLOW',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            themeMode: themeController.mode,
            // Wrap every page (not just auth) in the phone mockup on web.
            builder: (context, child) =>
                IPhoneFrame(child: child ?? const SizedBox.shrink()),
            home: const AuthWrapper(),
          );
        },
      ),
    );
  }
}

class AuthWrapper extends StatefulWidget {
  const AuthWrapper({super.key});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final api = context.read<ApiService>();
      if (api.isAuthenticated) {
        api.fetchCurrentUser();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final api = context.watch<ApiService>();

    if (api.isConnecting) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (api.isAuthenticated && api.currentUser != null) {
      return const MainScreen();
    }

    return const LoginScreen();
  }
}
