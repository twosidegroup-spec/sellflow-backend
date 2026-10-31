import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService extends ChangeNotifier {
  final http.Client _client;

  String _baseUrl = 'http://192.168.0.219:8000';
  bool _isConnecting = false;
  bool get isConnecting => _isConnecting;
  String? _token;
  String? _lastEmail;
  bool _isLoading = false;
  String? _error;

  // State
  List<Product> _products = [];
  List<Order> _orders = [];
  List<Customer> _customers = [];
  List<Payment> _payments = [];
  User? _currentUser;
  Business? _currentBusiness;
  DashboardSummary? _summary;

  ApiService([http.Client? client]) : _client = client ?? http.Client();

  // Getters
  String get baseUrl => _baseUrl;
  bool get isLoading => _isLoading;
  String? get error => _error;
  List<Product> get products => _products;
  List<Order> get orders => _orders;
  List<Customer> get customers => _customers;
  List<Payment> get payments => _payments;
  User? get currentUser => _currentUser;
  Business? get currentBusiness => _currentBusiness;
  DashboardSummary? get summary => _summary;
  String? get lastEmail => _lastEmail;
  bool get isAuthenticated => _token != null;

  /// The business the dashboard should load data for.
  int get _businessId => _currentBusiness?.id ?? 1;

  /// Try to find a reachable backend automatically so the user never has to
  /// type a URL. Tries common local addresses first, then scans the LAN.
  Future<void> autoConnect() async {
    _isConnecting = true;
    notifyListeners();
    try {
      final candidates = <String>{};
      if (kIsWeb) {
        candidates.add(Uri.base.origin);
      } else {
        candidates.addAll(const [
          'http://10.0.2.2:8000',
          'http://localhost:8000',
          'http://127.0.0.1:8000',
        ]);
      }
      candidates.add('http://localhost:8000');

      for (final c in candidates) {
        if (await _probe(c)) {
          await _applyBaseUrl(c);
          return;
        }
      }

      // Fallback: scan common LAN subnets (mobile only).
      if (!kIsWeb) {
        final found = await _scanSubnets();
        if (found != null) {
          await _applyBaseUrl(found);
          return;
        }
      }

      _error = 'Could not auto-connect. Set Server URL in Settings.';
    } finally {
      _isConnecting = false;
      notifyListeners();
    }
  }

  Future<void> _applyBaseUrl(String url) async {
    _baseUrl = url;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('server_base_url', url);
    } catch (_) {}
  }

  Future<bool> _probe(String url) async {
    try {
      final r = await _client
          .get(Uri.parse('$url/health'))
          .timeout(const Duration(milliseconds: 1200));
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<String?> _scanSubnets() async {
    const prefixes = ['192.168.0', '192.168.1', '10.0.0'];
    for (final prefix in prefixes) {
      for (int start = 1; start <= 254; start += 50) {
        final end = (start + 49).clamp(1, 254);
        final futures = <Future<String?>>[];
        for (int i = start; i <= end; i++) {
          final url = 'http://$prefix.$i:8000';
          futures.add(_probe(url).then((ok) => ok ? url : null));
        }
        final results = await Future.wait(futures);
        for (final r in results) {
          if (r != null) return r;
        }
      }
    }
    return null;
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url;
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('server_base_url', url);
    } catch (_) {}
  }

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('auth_token', token);
    _token = token;
  }

  Future<String?> _loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('auth_token');
  }

  Future<void> _saveEmail(String email) async {
    _lastEmail = email;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('user_email', email);
  }

  Future<String?> getSavedEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('user_email');
  }

  Future<void> initialize() async {
    final token = await _loadToken();
    if (token != null) {
      _token = token;
    }
    _lastEmail = await getSavedEmail();
    // Restore a user-configured backend URL (if any)
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('server_base_url');
      if (saved != null && saved.isNotEmpty) {
        _baseUrl = saved;
        if (await _probe(saved)) {
          notifyListeners();
          return;
        }
      }
    } catch (_) {}
    await autoConnect();
  }

  Future<void> logout() async {
    _token = null;
    _currentUser = null;
    _currentBusiness = null;
    _products.clear();
    _orders.clear();
    _customers.clear();
    _payments.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    notifyListeners();
  }

  Future<bool> login(String email, String passcode) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': passcode}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await _saveToken(data['access_token'] as String);
        await _saveEmail(email);
        await fetchCurrentUser();
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _error = 'Invalid credentials';
      }
    } catch (e) {
      _error = 'Connection failed: $e';
    }

    _isLoading = false;
    notifyListeners();
    return false;
  }

  Future<bool> register(
    String email,
    String passcode,
    String fullName, {
    String? businessName,
    String? phone,
    String? paymentProvider,
    String? receivingNumber,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'password': passcode,
          'full_name': fullName,
          if (businessName != null && businessName.isNotEmpty)
            'business_name': businessName,
          if (phone != null && phone.isNotEmpty) 'phone': phone,
          if (receivingNumber != null && receivingNumber.isNotEmpty)
            'receiving_number': receivingNumber
          else if (phone != null && phone.isNotEmpty)
            'receiving_number': phone,
          if (paymentProvider != null && paymentProvider.isNotEmpty)
            'payment_provider': paymentProvider,
        }),
      );

      if (response.statusCode == 201) {
        // Remember the email so the passcode login screen can use it later
        await _saveEmail(email);
        return await login(email, passcode);
      }

      String detail = '';
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        if (data['detail'] is String) detail = data['detail'] as String;
      } catch (_) {}

      if (response.statusCode == 400 &&
          detail.toLowerCase().contains('already registered')) {
        // The account already exists. If the entered passcode matches it,
        // sign the user in directly instead of failing.
        _isLoading = false;
        notifyListeners();
        final loggedIn = await login(email, passcode);
        if (!loggedIn) {
          _error =
              'This email is already registered. Please log in with your existing passcode.';
          notifyListeners();
        }
        return loggedIn;
      }

      _error = detail.isNotEmpty ? detail : 'Registration failed';
    } catch (e) {
      _error = 'Connection failed: $e';
    }

    _isLoading = false;
    notifyListeners();
    return false;
  }

  Future<void> fetchCurrentUser() async {
    if (_token == null) return;

    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/auth/me'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentUser = User.fromJson(data);
        final businessJson = data['business'];
        _currentBusiness = businessJson is Map<String, dynamic>
            ? Business.fromJson(businessJson)
            : null;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Failed to fetch current user: $e');
    }
  }

  // Analytics summary for the overview dashboard
  Future<void> fetchSummary() async {    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/analytics/summary'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _summary = DashboardSummary.fromJson(data);
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Failed to fetch summary: $e');
    }
  }

  // Update profile / payment settings for the signed-in user
  Future<bool> updateMe({
    String? fullName,
    String? phone,
    String? paymentProvider,
    String? receivingNumber,
  }) async {
    try {
      final response = await _client.put(
        Uri.parse('$_baseUrl/api/v1/auth/me'),
        headers: _authHeaders(),
        body: jsonEncode({
          if (fullName != null) 'full_name': fullName,
          if (phone != null) 'phone': phone,
          if (paymentProvider != null) 'payment_provider': paymentProvider,
          if (receivingNumber != null) 'receiving_number': receivingNumber,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentUser = User.fromJson(data);
        final businessJson = data['business'];
        _currentBusiness = businessJson is Map<String, dynamic>
            ? Business.fromJson(businessJson)
            : null;
        notifyListeners();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to update profile: $e');
    }
    return false;
  }

  /// Returns null on success, or an error message on failure.
  Future<String?> changePasscode(
      String currentPasscode, String newPasscode) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/auth/passcode/change'),
        headers: _authHeaders(),
        body: jsonEncode({
          'current_password': currentPasscode,
          'new_password': newPasscode,
        }),
      );

      if (response.statusCode == 200) return null;
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        if (data['detail'] is String) return data['detail'] as String;
      } catch (_) {}
      return 'Could not change passcode';
    } catch (e) {
      return 'Connection failed. Please check your network.';
    }
  }

  Future<bool> updateBusiness(String name) async {
    try {
      final response = await _client.patch(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId'),
        headers: _authHeaders(),
        body: jsonEncode({'name': name}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentBusiness = Business.fromJson(data);
        notifyListeners();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to update business: $e');
    }
    return false;
  }

  Future<bool> createProduct({
    required String name,
    required String sku,
    required double costPrice,
    required double sellingPrice,
    required int stockQuantity,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/products/'),
        headers: _authHeaders(),
        body: jsonEncode({
          'name': name,
          'sku': sku,
          'cost_price': costPrice,
          'selling_price': sellingPrice,
          'stock_quantity': stockQuantity,
        }),
      );

      if (response.statusCode == 201) {
        await fetchProducts();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to create product: $e');
    }
    return false;
  }

  Future<bool> updateProductStock(int productId, int stockQuantity) async {
    try {
      final response = await _client.put(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/products/$productId'),
        headers: _authHeaders(),
        body: jsonEncode({'stock_quantity': stockQuantity}),
      );

      if (response.statusCode == 200) {
        await fetchProducts();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to update product stock: $e');
    }
    return false;
  }

  Future<bool> createCustomer({
    required String name,
    String? phone,
    String? email,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/customers/'),
        headers: _authHeaders(),
        body: jsonEncode({
          'name': name,
          if (phone != null && phone.isNotEmpty) 'phone': phone,
          if (email != null && email.isNotEmpty) 'email': email,
        }),
      );

      if (response.statusCode == 201) {
        await fetchCustomers();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to create customer: $e');
    }
    return false;
  }

  Future<bool> createOrder({
    int? customerId,
    required List<Map<String, dynamic>> items,
    double deliveryFee = 0,
    double discount = 0,
    String? notes,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/orders/'),
        headers: _authHeaders(),
        body: jsonEncode({
          if (customerId != null) 'customer_id': customerId,
          'items': items,
          'delivery_fee': deliveryFee,
          'discount': discount,
          if (notes != null && notes.isNotEmpty) 'notes': notes,
        }),
      );

      if (response.statusCode == 201) {
        await fetchOrders();
        await fetchSummary();
        return true;
      }
    } catch (e) {
      debugPrint('Failed to create order: $e');
    }
    return false;
  }

  // Payment reconciliation
  Map<String, dynamic>? _reconciliation;
  Map<String, dynamic>? get reconciliation => _reconciliation;

  // Auto-detected incoming payments
  List<DetectedPayment> _detectedPayments = [];
  List<DetectedPayment> get detectedPayments => _detectedPayments;

  Future<void> fetchDetectedPayments() async {
    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/payments/detected'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _detectedPayments =
            data.map((e) => DetectedPayment.fromJson(e)).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Failed to fetch detected payments: $e');
    }
  }

  /// Simulates an incoming provider payment on the connected receiving number.
  /// Used to test the automatic detection pipeline.
  Future<Map<String, dynamic>?> simulateIncomingPayment({
    required double amount,
    required String method,
  }) async {
    final receiver = _currentUser?.receivingNumber ?? _currentUser?.phone;
    if (receiver == null || receiver.isEmpty) {
      return {'error': 'no_number'};
    }

    try {
      final response = await _client.post(
        Uri.parse('$_baseUrl/api/v1/payments/detect'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'receiver_number': receiver,
          'amount': amount,
          'method': method,
          'sender_number': '01700000000',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        await fetchDetectedPayments();
        if (data['matched'] == true) {
          await fetchPayments();
          await fetchSummary();
        }
        return data;
      }
      if (response.statusCode == 404) {
        return {'error': 'not_connected'};
      }
    } catch (e) {
      debugPrint('Failed to simulate incoming payment: $e');
    }
    return null;
  }

  Future<void> fetchReconciliationStatus() async {
    try {
      final response = await _client.get(
        Uri.parse(
            '$_baseUrl/api/v1/businesses/$_businessId/payments/reconciliation/status'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        _reconciliation = jsonDecode(response.body) as Map<String, dynamic>;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Failed to fetch reconciliation: $e');
    }
  }

  Future<Map<String, dynamic>?> verifyMobilePayment({
    required String method,
    required String transactionId,
    required double amount,
  }) async {
    try {
      final response = await _client.post(
        Uri.parse(
            '$_baseUrl/api/v1/businesses/$_businessId/payments/verify-mobile'),
        headers: _authHeaders(),
        body: jsonEncode({
          'transaction_id': transactionId,
          'amount': amount,
          'method': method,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('Failed to verify payment: $e');
    }
    return null;
  }

  // Products
  Future<List<Product>> fetchProducts() async {
    _isLoading = true;
    notifyListeners();

    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/products'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _products = data.map((e) => Product.fromJson(e)).toList();
        _isLoading = false;
        notifyListeners();
        return _products;
      }
    } catch (e) {
      debugPrint('Failed to fetch products: $e');
    }

    _isLoading = false;
    notifyListeners();
    return _products;
  }

  // Orders
  Future<List<Order>> fetchOrders() async {
    _isLoading = true;
    notifyListeners();

    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/orders'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _orders = data.map((e) => Order.fromJson(e)).toList();
        _isLoading = false;
        notifyListeners();
        return _orders;
      }
    } catch (e) {
      debugPrint('Failed to fetch orders: $e');
    }

    _isLoading = false;
    notifyListeners();
    return _orders;
  }

  // Customers
  Future<List<Customer>> fetchCustomers() async {
    _isLoading = true;
    notifyListeners();

    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/customers'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _customers = data.map((e) => Customer.fromJson(e)).toList();
        _isLoading = false;
        notifyListeners();
        return _customers;
      }
    } catch (e) {
      debugPrint('Failed to fetch customers: $e');
    }

    _isLoading = false;
    notifyListeners();
    return _customers;
  }

  // Payments
  Future<List<Payment>> fetchPayments() async {
    _isLoading = true;
    notifyListeners();

    try {
      final response = await _client.get(
        Uri.parse('$_baseUrl/api/v1/businesses/$_businessId/payments'),
        headers: _authHeaders(),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _payments = data.map((e) => Payment.fromJson(e)).toList();
        _isLoading = false;
        notifyListeners();
        return _payments;
      }
    } catch (e) {
      debugPrint('Failed to fetch payments: $e');
    }

    _isLoading = false;
    notifyListeners();
    return _payments;
  }

  Map<String, String> _authHeaders() {
    return {
      'Content-Type': 'application/json',
      if (_token != null) 'Authorization': 'Bearer $_token',
    };
  }
}

// Data Models

/// Tolerant number parsing: the API can serialize Decimal values as
/// strings (e.g. "800.00") or numbers depending on the backend.
double _toDouble(dynamic value) {
  if (value == null) return 0;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString()) ?? 0;
}

int _toInt(dynamic value) {
  if (value == null) return 0;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString()) ?? 0;
}
class User {
  final int id;
  final String email;
  final String fullName;
  final String? phone;
  final String? paymentProvider;
  final String? receivingNumber;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    this.phone,
    this.paymentProvider,
    this.receivingNumber,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      phone: json['phone'] as String?,
      paymentProvider: json['payment_provider'] as String?,
      receivingNumber: json['receiving_number'] as String?,
    );
  }
}

class Business {
  final int id;
  final String name;

  Business({required this.id, required this.name});

  factory Business.fromJson(Map<String, dynamic> json) {
    return Business(
      id: json['id'] as int,
      name: json['name'] as String,
    );
  }
}

class Product {
  final int id;
  final String name;
  final String sku;
  final double sellingPrice;
  final double costPrice;
  final int stockQuantity;

  Product({
    required this.id,
    required this.name,
    required this.sku,
    required this.sellingPrice,
    required this.costPrice,
    required this.stockQuantity,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int,
      name: json['name'] as String,
      sku: json['sku'] as String,
      sellingPrice: _toDouble(json['selling_price']),
      costPrice: _toDouble(json['cost_price']),
      stockQuantity: _toInt(json['stock_quantity']),
    );
  }
}

class Order {
  final int id;
  final String status;
  final double totalAmount;
  final DateTime createdAt;
  final int? customerId;

  Order({
    required this.id,
    required this.status,
    required this.totalAmount,
    required this.createdAt,
    this.customerId,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    return Order(
      id: json['id'] as int,
      status: json['status'] as String,
      totalAmount: _toDouble(json['total_amount']),
      createdAt: DateTime.parse(json['created_at'] as String),
      customerId: json['customer_id'] as int?,
    );
  }
}

class Customer {
  final int id;
  final String name;
  final String? email;
  final String? phone;

  Customer({required this.id, required this.name, this.email, this.phone});

  factory Customer.fromJson(Map<String, dynamic> json) {
    return Customer(
      id: json['id'] as int,
      name: json['name'] as String,
      email: json['email'] as String?,
      phone: json['phone'] as String?,
    );
  }
}

class Payment {
  final int id;
  final String method;
  final double amount;
  final String status;
  final DateTime createdAt;
  final int? orderId;
  final DateTime? paidAt;

  Payment({
    required this.id,
    required this.method,
    required this.amount,
    required this.status,
    required this.createdAt,
    this.orderId,
    this.paidAt,
  });

  factory Payment.fromJson(Map<String, dynamic> json) {
    return Payment(
      id: json['id'] as int,
      method: json['method'] as String,
      amount: _toDouble(json['amount']),
      status: json['status'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      orderId: json['order_id'] as int?,
      paidAt: json['paid_at'] != null
          ? DateTime.tryParse(json['paid_at'] as String)
          : null,
    );
  }
}

class DailyPoint {
  final String date;
  final double revenue;
  final double profit;
  final int orders;

  DailyPoint({
    required this.date,
    required this.revenue,
    required this.profit,
    required this.orders,
  });

  factory DailyPoint.fromJson(Map<String, dynamic> json) {
    return DailyPoint(
      date: json['date'] as String,
      revenue: _toDouble(json['revenue']),
      profit: _toDouble(json['profit']),
      orders: _toInt(json['orders']),
    );
  }
}

class DashboardSummary {
  final double todayRevenue;
  final double todayProfit;
  final int todayOrders;
  final double totalRevenue;
  final double totalProfit;
  final int totalOrders;
  final int pendingDeliveries;
  final List<DailyPoint> daily;
  DashboardSummary({
    required this.todayRevenue,
    required this.todayProfit,
    required this.todayOrders,
    required this.totalRevenue,
    required this.totalProfit,
    required this.totalOrders,
    required this.pendingDeliveries,
    required this.daily,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      todayRevenue: _toDouble(json['today_revenue']),
      todayProfit: _toDouble(json['today_profit']),
      todayOrders: _toInt(json['today_orders']),
      totalRevenue: _toDouble(json['total_revenue']),
      totalProfit: _toDouble(json['total_profit']),
      totalOrders: _toInt(json['total_orders']),
      pendingDeliveries: _toInt(json['pending_deliveries']),
      daily: ((json['daily'] as List<dynamic>?) ?? [])
          .map((e) => DailyPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class DetectedPayment {
  final int id;
  final double amount;
  final String method;
  final String? senderNumber;
  final String? transactionId;
  final bool matched;
  final int? orderId;
  final DateTime time;

  DetectedPayment({
    required this.id,
    required this.amount,
    required this.method,
    this.senderNumber,
    this.transactionId,
    required this.matched,
    this.orderId,
    required this.time,
  });

  factory DetectedPayment.fromJson(Map<String, dynamic> json) {
    return DetectedPayment(
      id: json['id'] as int,
      amount: _toDouble(json['amount']),
      method: json['method'] as String,
      senderNumber: json['sender_number'] as String?,
      transactionId: json['transaction_id'] as String?,
      matched: json['matched'] == true,
      orderId: json['order_id'] as int?,
      time: DateTime.parse(
          (json['paid_at'] ?? json['created_at']) as String),
    );
  }
}
