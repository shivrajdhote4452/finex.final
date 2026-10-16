import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  // Android emulator maps 10.0.2.2 to host localhost:8000
  String baseUrl = 'http://10.0.2.2:8000/api/v1';
  String? _token;

  void setToken(String? token) {
    _token = token;
  }

  String? get token => _token;
  bool get isAuthenticated => _token != null;

  Map<String, String> _headers([Map<String, String>? extra]) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'X-Correlation-ID': 'mobile-${DateTime.now().millisecondsSinceEpoch}',
    };
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    if (extra != null) {
      headers.addAll(extra);
    }
    return headers;
  }

  // --- Auth ---
  Future<Map<String, dynamic>> devLogin({
    String email = 'shivraj.dhote@finex.internal',
    String name = 'Shivraj Dhote',
  }) async {
    final url = Uri.parse('$baseUrl/auth/dev-login');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'email': email, 'name': name, 'user_id': 'usr-shivraj-001'}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      _token = data['data']['access_token'];
      return data['data'];
    }
    throw Exception(data['error']?['message'] ?? 'Login failed');
  }

  // --- Market Data ---
  Future<List<Map<String, dynamic>>> getInstruments() async {
    final url = Uri.parse('$baseUrl/market/instruments');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return List<Map<String, dynamic>>.from(data['data']['instruments'] ?? []);
    }
    return [];
  }

  Future<Map<String, dynamic>?> getQuote(String symbol) async {
    final url = Uri.parse('$baseUrl/market/quotes/$symbol');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  // --- Paper Trading ---
  Future<Map<String, dynamic>> getAccount() async {
    final url = Uri.parse('$baseUrl/paper-trading/account');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Failed to load account');
  }

  Future<Map<String, dynamic>> submitOrder({
    required String symbol,
    required String side,
    required String orderType,
    required double quantity,
    double? limitPrice,
    String? idempotencyKey,
  }) async {
    final key = idempotencyKey ?? 'mob-ord-${DateTime.now().millisecondsSinceEpoch}';
    final url = Uri.parse('$baseUrl/paper-trading/orders');
    final response = await http.post(
      url,
      headers: _headers({'X-Idempotency-Key': key}),
      body: jsonEncode({
        'symbol': symbol,
        'side': side,
        'order_type': orderType,
        'quantity': quantity,
        if (limitPrice != null) 'limit_price': limitPrice,
      }),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Order submission failed');
  }

  // --- Spending & CSV ---
  Future<Map<String, dynamic>> getTransactions() async {
    final url = Uri.parse('$baseUrl/spending/transactions');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'transactions': [], 'total': 0};
  }

  Future<Map<String, dynamic>> previewCsv(String fileName, String csvContent) async {
    final url = Uri.parse('$baseUrl/spending/upload/preview');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'file_name': fileName, 'csv_content': csvContent}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'CSV preview failed');
  }

  Future<Map<String, dynamic>> commitCsv(String previewId, [List<int>? acceptedIndices]) async {
    final url = Uri.parse('$baseUrl/spending/upload/commit');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'preview_id': previewId, 'accepted_indices': acceptedIndices}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'CSV commit failed');
  }

  // --- AI RAG Chat ---
  Future<Map<String, dynamic>> sendAiMessage(String conversationId, String content) async {
    final url = Uri.parse('$baseUrl/ai/conversations/$conversationId/messages');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'content': content}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'AI retrieval query failed');
  }
}

final apiClient = ApiClient();
