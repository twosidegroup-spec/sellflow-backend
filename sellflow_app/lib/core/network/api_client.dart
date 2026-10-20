import 'package:dio/dio.dart';
import 'dart:convert';

import '../config/env.dart';

class ApiClient {
  late final Dio dio;

  ApiClient() {
    dio = Dio(BaseOptions(
      baseUrl: Env.baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      sendTimeout: const Duration(seconds: 30),
      validateStatus: (status) => status != null && status < 500,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) {
        return handler.next(options);
      },
      onError: (DioException e, handler) {
        print('--- ERROR TYPE: ${e.type} ---');
        print('--- STATUS: ${e.response?.statusCode} ---');
        print('--- RESPONSE DATA: ${e.response?.data} ---');
        handler.next(e);
      },
    ));
  }
}
