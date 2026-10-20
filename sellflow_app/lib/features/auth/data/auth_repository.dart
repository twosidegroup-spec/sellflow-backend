import 'package:dio/dio.dart';
import '../../../core/network/api_client.dart';

class AuthRepository {
  final ApiClient _client;
  AuthRepository(this._client);

  Future<void> register({
    required String email,
    required String fullName,
    required String phone,
    required String businessName,
    required String passcode,
  }) async {
    await _client.dio.post('/auth/register', data: {
      'email': email,
      'full_name': fullName,
      'phone': phone.isEmpty ? null : phone,
      'business_name': businessName.isEmpty ? null : businessName,
      'password': passcode,
    });
  }

  Future<void> login({required String email, required String passcode}) async {
    final res = await _client.dio.post('/auth/login', data: {
      'email': email,
      'password': passcode,
    });
    final token = (res.data as Map<String, dynamic>)['access_token'] as String;
    _client.dio.options.headers['Authorization'] = 'Bearer $token';
  }

  Future<Map<String, dynamic>> me() async {
    final res = await _client.dio.get('/auth/me');
    return res.data as Map<String, dynamic>;
  }
}
