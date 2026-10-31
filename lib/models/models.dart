class Business {
  final int id;
  final String name;
  final String slug;
  final DateTime createdAt;
  final DateTime updatedAt;

  Business({
    required this.id,
    required this.name,
    required this.slug,
    required this.createdAt,
    required this.updatedAt,
  });

  factory Business.fromJson(Map<String, dynamic> json) {
    return Business(
      id: json['id'] as int,
      name: json['name'] as String,
      slug: json['slug'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }
}

class User {
  final int id;
  final String email;
  final String fullName;
  final String? phone;
  final Business? business;
  final DateTime createdAt;

  User({
    required this.id,
    required this.email,
    required this.fullName,
    this.phone,
    this.business,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      phone: json['phone'] as String?,
      business: json['business'] != null 
          ? Business.fromJson(json['business'] as Map<String, dynamic>)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class Order {
  final int id;
  final int businessId;
  final int? customerId;
  final String status;
  final double totalAmount;
  final double totalCost;
  final DateTime createdAt;

  Order({
    required this.id,
    required this.businessId,
    this.customerId,
    required this.status,
    required this.totalAmount,
    required this.totalCost,
    required this.createdAt,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    return Order(
      id: json['id'] as int,
      businessId: json['business_id'] as int,
      customerId: json['customer_id'] as int?,
      status: json['status'] as String,
      totalAmount: (json['total_amount'] as num).toDouble(),
      totalCost: (json['total_cost'] as num).toDouble(),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class Customer {
  final int id;
  final int businessId;
  final String name;
  final String? phone;
  final String? email;
  final String? address;
  final DateTime createdAt;

  Customer({
    required this.id,
    required this.businessId,
    required this.name,
    this.phone,
    this.email,
    this.address,
    required this.createdAt,
  });

  factory Customer.fromJson(Map<String, dynamic> json) {
    return Customer(
      id: json['id'] as int,
      businessId: json['business_id'] as int,
      name: json['name'] as String,
      phone: json['phone'] as String?,
      email: json['email'] as String?,
      address: json['address'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class Product {
  final int id;
  final int businessId;
  final String name;
  final String sku;
  final String? description;
  final double costPrice;
  final double sellingPrice;
  final int stockQuantity;
  final String status;
  final DateTime createdAt;

  Product({
    required this.id,
    required this.businessId,
    required this.name,
    required this.sku,
    this.description,
    required this.costPrice,
    required this.sellingPrice,
    required this.stockQuantity,
    required this.status,
    required this.createdAt,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int,
      businessId: json['business_id'] as int,
      name: json['name'] as String,
      sku: json['sku'] as String,
      description: json['description'] as String?,
      costPrice: (json['cost_price'] as num).toDouble(),
      sellingPrice: (json['selling_price'] as num).toDouble(),
      stockQuantity: json['stock_quantity'] as int,
      status: json['status'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  bool get isLowStock => stockQuantity > 0 && stockQuantity < 10;
  bool get isOutOfStock => stockQuantity == 0;
}

class Payment {
  final int id;
  final int businessId;
  final int? orderId;
  final double amount;
  final String method;
  final String? transactionId;
  final String status;
  final DateTime? paidAt;
  final String? notes;
  final DateTime createdAt;

  Payment({
    required this.id,
    required this.businessId,
    this.orderId,
    required this.amount,
    required this.method,
    this.transactionId,
    required this.status,
    this.paidAt,
    this.notes,
    required this.createdAt,
  });

  factory Payment.fromJson(Map<String, dynamic> json) {
    return Payment(
      id: json['id'] as int,
      businessId: json['business_id'] as int,
      orderId: json['order_id'] as int?,
      amount: (json['amount'] as num).toDouble(),
      method: json['method'] as String,
      transactionId: json['transaction_id'] as String?,
      status: json['status'] as String,
      paidAt: json['paid_at'] != null 
          ? DateTime.parse(json['paid_at'] as String)
          : null,
      notes: json['notes'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
