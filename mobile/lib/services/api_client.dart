import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _tokenStorageKey = 'finex_auth_token';

  static String normalizeBaseUrl(String url) {
    var trimmed = url.trim();
    while (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    if (!trimmed.endsWith('/api/v1')) {
      if (trimmed.endsWith('/api')) {
        trimmed = '$trimmed/v1';
      } else {
        trimmed = '$trimmed/api/v1';
      }
    }
    return trimmed;
  }

  // Environment-specific API configuration
  static const String _defaultUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
  String baseUrl = normalizeBaseUrl(_defaultUrl);
  String? _token;

  void setBaseUrl(String url) {
    baseUrl = normalizeBaseUrl(url);
  }

  static final Map<String, String> _testStorage = {};

  /// Initialize and restore stored session from secure storage
  Future<void> initSession() async {
    try {
      _token = await _storage.read(key: _tokenStorageKey).timeout(const Duration(milliseconds: 300));
    } catch (_) {
      _token = _testStorage[_tokenStorageKey];
    }
  }

  Future<void> setToken(String? token) async {
    _token = token;
    if (token != null) {
      _testStorage[_tokenStorageKey] = token;
    } else {
      _testStorage.remove(_tokenStorageKey);
    }
    try {
      if (token != null && token.isNotEmpty) {
        await _storage.write(key: _tokenStorageKey, value: token).timeout(const Duration(milliseconds: 300));
      } else {
        await _storage.delete(key: _tokenStorageKey).timeout(const Duration(milliseconds: 300));
      }
    } catch (_) {}
  }

  Future<void> logout() async {
    try {
      if (_token != null) {
        final url = Uri.parse('$baseUrl/auth/revoke');
        await http.post(
          url,
          headers: _headers(),
          body: jsonEncode({'token': _token}),
        );
      }
    } catch (_) {
      // Safe fallback on network failure
    } finally {
      await setToken(null);
    }
  }

  String? get token => _token;
  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  Map<String, String> _headers([Map<String, String>? extra]) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'X-Correlation-ID': 'mobile-${DateTime.now().millisecondsSinceEpoch}',
    };
    if (_token != null && _token!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_token';
    }
    if (extra != null) {
      headers.addAll(extra);
    }
    return headers;
  }

  // --- Auth & Onboarding ---
  Future<Map<String, dynamic>> devLogin({
    String email = 'shivraj.dhote@finex.internal',
    String name = 'Shivraj Dhote',
  }) async {
    if (!kDebugMode) {
      throw Exception('Developer sandbox sign-in is disabled in production builds.');
    }
    final url = Uri.parse('$baseUrl/auth/dev-login');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'email': email, 'name': name, 'user_id': 'usr-shivraj-001'}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      final token = data['data']['access_token'] as String?;
      await setToken(token);
      return data['data'];
    }
    throw Exception(data['error']?['message'] ?? 'Login failed');
  }

  Future<Map<String, dynamic>> loginWithGoogle(String idToken) async {
    final url = Uri.parse('$baseUrl/auth/google');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'id_token': idToken}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      final token = data['data']['access_token'] as String?;
      await setToken(token);
      return data['data'];
    }
    throw Exception(data['error']?['message'] ?? 'Google authentication failed');
  }

  Future<Map<String, dynamic>> getProfile() async {
    final url = Uri.parse('$baseUrl/users/me');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Failed to load profile');
  }

  Future<Map<String, dynamic>> recordConsent({
    String consentVersion = 'v1.0',
    bool termsAccepted = true,
    bool privacyAccepted = true,
    bool educationalDisclaimerAccepted = true,
  }) async {
    final url = Uri.parse('$baseUrl/users/consent');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'consent_version': consentVersion,
        'terms_accepted': termsAccepted,
        'privacy_accepted': privacyAccepted,
        'educational_disclaimer_accepted': educationalDisclaimerAccepted,
      }),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Failed to record consent');
  }

  Future<Map<String, dynamic>> submitRiskAssessment({
    required String horizonCategory,
    required List<Map<String, dynamic>> answers,
    String questionnaireVersion = 'v1.0',
  }) async {
    final url = Uri.parse('$baseUrl/risk/assessments');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'questionnaire_version': questionnaireVersion,
        'horizon_category': horizonCategory,
        'answers': answers,
      }),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Failed to submit risk assessment');
  }

  // Backward compatibility alias
  Future<Map<String, dynamic>> submitRiskProfile({
    required String scoreTier,
    required Map<String, dynamic> answers,
  }) async {
    // Map simplified tier to questionnaire schema
    final horizon = answers['investment_horizon'] == 'LESS_THAN_1_YEAR'
        ? '<1'
        : answers['investment_horizon'] == '1-3_YEARS'
            ? '1-3'
            : answers['investment_horizon'] == '3-5_YEARS'
                ? '3-5'
                : '>5';
    final qAnswers = [
      {'question_id': 'Q1', 'option_id': scoreTier == 'CONSERVATIVE' ? 'Q1_A' : scoreTier == 'MODERATE' ? 'Q1_C' : 'Q1_D', 'score': scoreTier == 'CONSERVATIVE' ? 10 : scoreTier == 'MODERATE' ? 70 : 100},
      {'question_id': 'Q2', 'option_id': 'Q2_C', 'score': 75},
      {'question_id': 'Q3', 'option_id': scoreTier == 'CONSERVATIVE' ? 'Q3_A' : scoreTier == 'MODERATE' ? 'Q3_B' : 'Q3_C', 'score': scoreTier == 'CONSERVATIVE' ? 20 : scoreTier == 'MODERATE' ? 60 : 95},
      {'question_id': 'Q4', 'option_id': 'Q4_C', 'score': 70},
    ];
    return submitRiskAssessment(horizonCategory: horizon, answers: qAnswers);
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
        'idempotency_key': key,
      }),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Order submission failed');
  }

  Future<List<Map<String, dynamic>>> getOrders([int limit = 50]) async {
    final url = Uri.parse('$baseUrl/paper-trading/orders?limit=$limit');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return List<Map<String, dynamic>>.from(data['data']['orders'] ?? []);
    }
    return [];
  }

  Future<Map<String, dynamic>> resetAccount({bool confirmReset = true}) async {
    final url = Uri.parse('$baseUrl/paper-trading/reset');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'confirm_reset': confirmReset}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Account reset failed');
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

  // --- AI RAG Conversations & Chat ---
  Future<Map<String, dynamic>> createConversation([String title = 'Mobile Assistant']) async {
    final url = Uri.parse('$baseUrl/ai/conversations');
    final response = await http.post(
      url,
      headers: _headers(),
      body: jsonEncode({'title': title}),
    );
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw Exception(data['error']?['message'] ?? 'Failed to create conversation');
  }

  Future<List<Map<String, dynamic>>> getConversations() async {
    final url = Uri.parse('$baseUrl/ai/conversations');
    final response = await http.get(url, headers: _headers());
    final data = jsonDecode(response.body);
    if (response.statusCode == 200 && data['data'] != null) {
      return List<Map<String, dynamic>>.from(data['data']['conversations'] ?? []);
    }
    return [];
  }

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
