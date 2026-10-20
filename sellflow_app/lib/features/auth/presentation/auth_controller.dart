import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/network/api_client.dart';
import '../../../core/config/env.dart';
import '../data/auth_repository.dart';

enum AuthStatus { loading, locked, working, authenticated }

class AuthState {
  final AuthStatus status;
  final String? email;
  final String? fullName;
  final int passcodeLength;
  final String? error;

  const AuthState({
    this.status = AuthStatus.locked,
    this.email,
    this.fullName,
    this.passcodeLength = 4,
    this.error,
  });

  AuthState copyWith({
    AuthStatus? status,
    String? email,
    String? fullName,
    int? passcodeLength,
    String? error,
    bool clearError = false,
  }) => AuthState(
        status: status ?? this.status,
        email: email ?? this.email,
        fullName: fullName ?? this.fullName,
        passcodeLength: passcodeLength ?? this.passcodeLength,
        error: clearError ? null : (error ?? this.error),
      );
}

final authRepositoryProvider = Provider((ref) => AuthRepository(ApiClient()));

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) => AuthController(ref.watch(authRepositoryProvider)),
);

class AuthController extends StateNotifier<AuthState> {
  final AuthRepository _repo;
  AuthController(this._repo) : super(const AuthState()) {
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    final prefs = await SharedPreferences.getInstance();
    final savedEmail = prefs.getString('auth_email');
    print('--- BOOTSTRAP: Saved email is "$savedEmail" ---');
    state = state.copyWith(
      status: AuthStatus.locked,
      email: savedEmail,
      passcodeLength: prefs.getInt('passcode_length') ?? 4,
    );
  }

  String _msg(DioException e) {
    print('--- DIO ERROR: ${e.type} | ${e.message} ---');
    print('--- DIO RESPONSE: ${e.response?.data} ---');
    final data = e.response?.data;
    if (data is Map && data['detail'] != null) return data['detail'].toString();
    if (data is String) return data;
    return 'Connection error. Check backend URL';
  }

  Future<bool> unlock(String passcode) async {
    final email = state.email;
    print('--- UNLOCK ATTEMPT: Email is "$email", Passcode is "$passcode" ---');
    
    if (email == null) {
      print('--- ERROR: Email is null! Cannot login. ---');
      state = state.copyWith(status: AuthStatus.locked, error: 'Session expired. Please register again.');
      return false;
    }
    
    state = state.copyWith(status: AuthStatus.working, clearError: true);
    try {
      print('--- SENDING LOGIN REQUEST TO BACKEND ---');
      await _repo.login(email: email, passcode: passcode);
      print('--- LOGIN SUCCESSFUL, FETCHING USER DATA ---');
      final me = await _repo.me();
      state = state.copyWith(status: AuthStatus.authenticated, fullName: me['full_name'] as String?);
      print('--- AUTHENTICATION COMPLETE ---');
      return true;
    } on DioException catch (e) {
      print('--- LOGIN FAILED ---');
      state = state.copyWith(status: AuthStatus.locked, error: _msg(e));
      return false;
    } catch (e) {
      print('--- UNEXPECTED ERROR: $e ---');
      state = state.copyWith(status: AuthStatus.locked, error: 'An unexpected error occurred.');
      return false;
    }
  }

  Future<bool> register({
    required String fullName,
    required String businessName,
    required String email,
    required String phone,
    required String passcode,
    required int length,
  }) async {
    state = state.copyWith(status: AuthStatus.working, clearError: true);
    try {
      print('--- SENDING REGISTER REQUEST ---');
      await _repo.register(
        email: email,
        fullName: fullName,
        phone: phone,
        businessName: businessName,
        passcode: passcode,
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_email', email);
      await prefs.setInt('passcode_length', length);
      print('--- REGISTRATION SUCCESSFUL, SAVED EMAIL: $email ---');
      state = state.copyWith(
        status: AuthStatus.locked,
        email: email,
        passcodeLength: length,
        clearError: true,
      );
      return true;
    } on DioException catch (e) {
      print('--- REGISTRATION FAILED ---');
      state = state.copyWith(status: AuthStatus.locked, error: _msg(e));
      return false;
    }
  }

  Future<void> useDifferentAccount() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_email');
    state = state.copyWith(status: AuthStatus.locked, email: null, clearError: true);
  }

  Future<void> logout() async {
    state = state.copyWith(status: AuthStatus.locked, fullName: null, clearError: true);
  }
}
