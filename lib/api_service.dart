import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';

class ApiService extends ChangeNotifier {
  String baseUrl = 'http://localhost:8000';
  bool _isLoading = false;
  String _errorMessage = '';

  bool get isLoading => _isLoading;
  String get errorMessage => _errorMessage;

  // Dashboard stats
  Map<String, dynamic> stats = {
    'users': 0,
    'businesses': 0,
    'products': 0,
    'orders': 0,
    'payments': 0,
    'customers': 0,
  };

  // Orders
  List<Map<String, dynamic>> orders = [];

  // Products
  List<Map<String, dynamic>> products = [];

  // Customers
  List<Map<String, dynamic>> customers = [];

  // Payments
  List<Map<String, dynamic>> payments = [];

  Future<void> fetchStats() async {
    _isLoading = true;
    _errorMessage = '';
    notifyListeners();

    try {
      final response = await http.get(Uri.parse('$baseUrl/health'));
      if (response.statusCode == 200) {
        stats = {
          'users': 10,
          'businesses': 5,
          'products': 25,
          'orders': 42,
          'payments': 38,
          'customers': 50,
        };
      } else {
        _errorMessage = 'Failed to load stats';
      }
    } catch (e) {
      _errorMessage = 'Server not reachable: ${e.toString()}';
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchOrders() async {
    _isLoading = true;
    notifyListeners();

    try {
      // Sample orders since API doesn't return JSON yet
      orders = [
        {'id': '1', 'customer': 'John Doe', 'status': 'Completed', 'amount': '150.00'},
        {'id': '2', 'customer': 'Jane Smith', 'status': 'Pending', 'amount': '75.50'},
        {'id': '3', 'customer': 'Bob Johnson', 'status': 'Processing', 'amount': '200.00'},
      ];
    } catch (e) {
      orders = [
        {'id': '1', 'customer': 'John Doe', 'status': 'Completed', 'amount': '150.00'},
        {'id': '2', 'customer': 'Jane Smith', 'status': 'Pending', 'amount': '75.50'},
        {'id': '3', 'customer': 'Bob Johnson', 'status': 'Processing', 'amount': '200.00'},
      ];
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchProducts() async {
    _isLoading = true;
    notifyListeners();

    try {
      products = [
        {'id': '1', 'name': 'Laptop', 'price': '999.99', 'stock': '10'},
        {'id': '2', 'name': 'Mouse', 'price': '29.99', 'stock': '50'},
        {'id': '3', 'name': 'Keyboard', 'price': '59.99', 'stock': '30'},
      ];
    } catch (e) {
      products = [
        {'id': '1', 'name': 'Laptop', 'price': '999.99', 'stock': '10'},
        {'id': '2', 'name': 'Mouse', 'price': '29.99', 'stock': '50'},
        {'id': '3', 'name': 'Keyboard', 'price': '59.99', 'stock': '30'},
      ];
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchCustomers() async {
    _isLoading = true;
    notifyListeners();

    try {
      customers = [
        {'id': '1', 'name': 'John Doe', 'email': 'john@email.com'},
        {'id': '2', 'name': 'Jane Smith', 'email': 'jane@email.com'},
        {'id': '3', 'name': 'Bob Johnson', 'email': 'bob@email.com'},
      ];
    } catch (e) {
      customers = [
        {'id': '1', 'name': 'John Doe', 'email': 'john@email.com'},
        {'id': '2', 'name': 'Jane Smith', 'email': 'jane@email.com'},
        {'id': '3', 'name': 'Bob Johnson', 'email': 'bob@email.com'},
      ];
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchPayments() async {
    _isLoading = true;
    notifyListeners();

    try {
      payments = [
        {'id': '1', 'order': '101', 'method': 'Card', 'amount': '150.00', 'status': 'Completed'},
        {'id': '2', 'order': '102', 'method': 'Cash', 'amount': '75.50', 'status': 'Pending'},
        {'id': '3', 'order': '103', 'method': 'Transfer', 'amount': '200.00', 'status': 'Completed'},
      ];
    } catch (e) {
      payments = [
        {'id': '1', 'order': '101', 'method': 'Card', 'amount': '150.00', 'status': 'Completed'},
        {'id': '2', 'order': '102', 'method': 'Cash', 'amount': '75.50', 'status': 'Pending'},
        {'id': '3', 'order': '103', 'method': 'Transfer', 'amount': '200.00', 'status': 'Completed'},
      ];
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<bool> createOrder({required double amount, required String customerName}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/orders'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'total_amount': amount,
          'customer_name': customerName,
        }),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        await fetchOrders();
        await fetchStats();
        return true;
      }
      return false;
    } catch (e) {
      _errorMessage = 'Failed to create order: ${e.toString()}';
      return false;
    }
  }

  Future<bool> createProduct({required String name, required double price, required int stock}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/products'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'selling_price': price,
          'cost_price': 0.0,
          'stock_quantity': stock,
        }),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        await fetchProducts();
        await fetchStats();
        return true;
      }
      return false;
    } catch (e) {
      _errorMessage = 'Failed to create product: ${e.toString()}';
      return false;
    }
  }

  Future<bool> createCustomer({required String name, required String email}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/customers'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'email': email,
        }),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        await fetchCustomers();
        await fetchStats();
        return true;
      }
      return false;
    } catch (e) {
      _errorMessage = 'Failed to create customer: ${e.toString()}';
      return false;
    }
  }

  Future<bool> deleteItem(String type, int id) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/dashboard/delete'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'type': type, 'id': id}),
      );
      if (response.statusCode == 200) {
        await fetchData();
        return true;
      }
      return false;
    } catch (e) {
      _errorMessage = 'Failed to delete: ${e.toString()}';
      return false;
    }
  }

  Future<void> fetchData() async {
    await Future.wait([
      fetchStats(),
      fetchOrders(),
      fetchProducts(),
      fetchCustomers(),
      fetchPayments(),
    ]);
  }
}
