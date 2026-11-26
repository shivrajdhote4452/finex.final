import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  final String message;
  final int statusCode;
  final dynamic details;

  ApiException(this.message, {this.statusCode = 400, this.details});

  @override
  String toString() => message;
}

class ApiClient {
  static final ApiClient _instance = ApiClient._internal();
  factory ApiClient() => _instance;
  ApiClient._internal();
  ApiClient.mock();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _tokenStorageKey = 'finex_auth_token';
  static const String _profileStorageKey = 'finex_user_profile';

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
  static String get _defaultUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    // Release builds on real physical devices target the deployed Render backend
    if (kReleaseMode) {
      return 'https://finex-final.onrender.com/api/v1';
    }
    if (kIsWeb ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.macOS ||
        defaultTargetPlatform == TargetPlatform.linux) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    return 'http://10.0.2.2:8000/api/v1';
  }

  String baseUrl = normalizeBaseUrl(_defaultUrl);
  String? _token;
  Map<String, dynamic>? _currentUserProfile;
  http.Client _httpClient = http.Client();

  @visibleForTesting
  void setHttpClient(http.Client? client) {
    _httpClient = client ?? http.Client();
  }

  /// Observable feed for real-time ledger updates across screens
  final ValueNotifier<List<Map<String, dynamic>>> recentOrdersNotifier =
      ValueNotifier<List<Map<String, dynamic>>>([]);

  void setBaseUrl(String url) {
    baseUrl = normalizeBaseUrl(url);
  }

  static final Map<String, String> _testStorage = {};

  /// Initialize and restore stored session and profile from secure storage
  Future<void> initSession() async {
    try {
      _token = await _storage.read(key: _tokenStorageKey).timeout(const Duration(milliseconds: 300));
      final rawProfile = await _storage.read(key: _profileStorageKey).timeout(const Duration(milliseconds: 300));
      if (rawProfile != null && rawProfile.isNotEmpty) {
        _currentUserProfile = Map<String, dynamic>.from(jsonDecode(rawProfile));
      }
    } catch (_) {
      _token = _testStorage[_tokenStorageKey];
      final raw = _testStorage[_profileStorageKey];
      if (raw != null && raw.isNotEmpty) {
        _currentUserProfile = Map<String, dynamic>.from(jsonDecode(raw));
      }
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

  Future<void> setProfile(Map<String, dynamic>? profile) async {
    if (profile == null) {
      _currentUserProfile = null;
      _testStorage.remove(_profileStorageKey);
      try {
        await _storage.delete(key: _profileStorageKey).timeout(const Duration(milliseconds: 300));
      } catch (_) {}
      return;
    }

    final existing = _currentUserProfile ?? {};
    final updated = Map<String, dynamic>.from(existing);

    profile.forEach((key, value) {
      if (value != null) {
        if (value is String) {
          if (value.trim().isNotEmpty) {
            updated[key] = value.trim();
          }
        } else {
          updated[key] = value;
        }
      }
    });

    _currentUserProfile = updated;
    final encoded = jsonEncode(updated);
    _testStorage[_profileStorageKey] = encoded;
    try {
      await _storage.write(key: _profileStorageKey, value: encoded).timeout(const Duration(milliseconds: 300));
    } catch (_) {}
  }

  Future<void> logout() async {
    try {
      if (_token != null) {
        final url = Uri.parse('$baseUrl/auth/revoke');
        await _httpClient.post(
          url,
          headers: _headers(),
          body: jsonEncode({'token': _token}),
        );
      }
    } catch (_) {
      // Safe fallback on network failure
    } finally {
      await setToken(null);
      await setProfile(null);
      recentOrdersNotifier.value = [];
    }
  }

  String? get token => _token;
  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  Map<String, dynamic>? get currentUserProfile => _currentUserProfile;

  String get userEmail => (_currentUserProfile?['email'] as String? ?? '').trim();

  String get userName {
    final name = _currentUserProfile?['full_name'] ??
        _currentUserProfile?['display_name'] ??
        _currentUserProfile?['name'] as String?;
    return (name ?? '').trim();
  }

  String get displayName {
    final name = userName;
    if (name.isEmpty) return '';
    return name.split(' ').first;
  }

  String get userInitials {
    final name = userName;
    if (name.isEmpty) return 'FI';
    final parts = name.split(' ').where((p) => p.isNotEmpty).toList();
    if (parts.length >= 2) {
      return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
    }
    return parts.first.substring(0, parts.first.length.clamp(1, 2)).toUpperCase();
  }

  bool get isOwner {
    if (!isAuthenticated) return false;
    return _currentUserProfile?['is_owner'] == true;
  }

  static String getTimeOfDayGreeting([String? name]) {
    final hour = DateTime.now().hour;
    final timeGreeting = (hour >= 5 && hour < 12)
        ? 'Good morning'
        : (hour >= 12 && hour < 17)
            ? 'Good afternoon'
            : 'Good evening';
    final trimmed = name?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      return '$timeGreeting, $trimmed';
    }
    return timeGreeting;
  }

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


  Future<void> _handleUnauthorizedIfNeeded(http.Response response) async {
    if (response.statusCode == 401) {
      await setToken(null);
      await setProfile(null);
      recentOrdersNotifier.value = [];
      return;
    }
    if (response.statusCode == 403) {
      final msg = _extractErrorMessage(response, '').toLowerCase();
      if (msg.contains('disabled') || msg.contains('inactive') || msg.contains('deactivated')) {
        await setToken(null);
        await setProfile(null);
        recentOrdersNotifier.value = [];
      }
    }
  }

  Map<String, dynamic> _decodeJsonObject(http.Response response) {
    if (response.body.trim().isEmpty) return <String, dynamic>{};
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {}
    return <String, dynamic>{};
  }

  String _extractErrorMessage(http.Response response, [String fallback = 'Request failed']) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        if (decoded['detail'] != null) {
          if (decoded['detail'] is String) return decoded['detail'] as String;
          if (decoded['detail'] is List) {
            return (decoded['detail'] as List)
                .map((e) => e is Map ? (e['msg'] ?? e.toString()) : e.toString())
                .join(', ');
          }
        }
        if (decoded['error'] is Map && decoded['error']['message'] != null) {
          return decoded['error']['message'].toString();
        }
        if (decoded['message'] != null && decoded['message'] is String) {
          return decoded['message'] as String;
        }
      }
    } catch (_) {}
    return '$fallback (${response.statusCode})';
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(String idToken, {String? email, String? name})?
      mockLoginWithGoogleHandler;

  Future<Map<String, dynamic>> loginWithGoogle(
    String idToken, {
    String? email,
    String? name,
  }) async {
    if (mockLoginWithGoogleHandler != null) {
      return await mockLoginWithGoogleHandler!(idToken, email: email, name: name);
    }
    final url = Uri.parse('$baseUrl/auth/google');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'id_token': idToken}),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      final token = data['data']['access_token'] as String?;
      await setToken(token);
      final initialProfile = <String, dynamic>{};
      if (email != null && email.isNotEmpty) initialProfile['email'] = email;
      if (name != null && name.isNotEmpty) {
        initialProfile['full_name'] = name;
        initialProfile['display_name'] = name.split(' ').first;
      }
      if (data['data']['email'] != null) initialProfile['email'] = data['data']['email'];
      if (data['data']['name'] != null) {
        initialProfile['full_name'] = data['data']['name'];
        initialProfile['display_name'] = (data['data']['name'] as String).split(' ').first;
      }
      if (initialProfile.isNotEmpty) {
        await setProfile(initialProfile);
      }
      try {
        await getProfile();
      } catch (_) {}
      return data['data'];
    }
    final errMsg = _extractErrorMessage(response, 'Google authentication failed');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(String email, String password)?
      mockLoginWithEmailHandler;

  Future<Map<String, dynamic>> loginWithEmail(
    String email,
    String password,
  ) async {
    if (mockLoginWithEmailHandler != null) {
      return await mockLoginWithEmailHandler!(email, password);
    }
    final cleanEmail = email.trim().toLowerCase();
    final url = Uri.parse('$baseUrl/auth/login');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'email': cleanEmail,
        'password': password,
      }),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      final token = data['data']['access_token'] as String?;
      await setToken(token);
      final initialProfile = <String, dynamic>{
        'id': data['data']['user_id'],
        'email': data['data']['email'] ?? cleanEmail,
        'full_name': data['data']['name'],
        'display_name': (data['data']['name'] as String?)?.split(' ').first,
      };
      await setProfile(initialProfile);
      try {
        await getProfile();
      } catch (_) {}
      return data['data'];
    }
    final errMsg = _extractErrorMessage(response, 'Invalid email or password');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(String email, String password, {String? name})?
      mockSignupWithEmailHandler;

  Future<Map<String, dynamic>> signupWithEmail(
    String email,
    String password, {
    String? name,
  }) async {
    if (mockSignupWithEmailHandler != null) {
      return await mockSignupWithEmailHandler!(email, password, name: name);
    }
    final cleanEmail = email.trim().toLowerCase();
    final url = Uri.parse('$baseUrl/auth/signup');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'email': cleanEmail,
        'password': password,
        'name': (name != null && name.trim().isNotEmpty) ? name.trim() : 'Investor',
      }),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    final errMsg = _extractErrorMessage(response, 'Account registration failed');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(String email)?
      mockForgotPasswordHandler;

  Future<Map<String, dynamic>> forgotPassword(String email) async {
    if (mockForgotPasswordHandler != null) {
      return await mockForgotPasswordHandler!(email);
    }
    final cleanEmail = email.trim().toLowerCase();
    final url = Uri.parse('$baseUrl/auth/forgot-password');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'email': cleanEmail}),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    final errMsg = _extractErrorMessage(response, 'Password reset request failed');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(String email, {String? password})?
      mockResendVerificationHandler;

  Future<Map<String, dynamic>> resendVerification(String email, {String? password}) async {
    if (mockResendVerificationHandler != null) {
      return await mockResendVerificationHandler!(email, password: password);
    }
    final cleanEmail = email.trim().toLowerCase();
    final url = Uri.parse('$baseUrl/auth/resend-verification');
    final Map<String, dynamic> body = {'email': cleanEmail};
    if (password != null && password.isNotEmpty) {
      body['password'] = password;
    }
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode(body),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    final errMsg = _extractErrorMessage(response, 'Could not resend verification email');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  Future<Map<String, dynamic>> verifyEmail(String token) async {
    final url = Uri.parse('$baseUrl/auth/verify-email');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'token': token.trim()}),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    final errMsg = _extractErrorMessage(response, 'Email verification failed');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  Future<Map<String, dynamic>> resetPassword(String token, String newPassword) async {
    final url = Uri.parse('$baseUrl/auth/reset-password');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'token': token.trim(), 'new_password': newPassword}),
    );
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    final errMsg = _extractErrorMessage(response, 'Password reset failed');
    throw ApiException(errMsg, statusCode: response.statusCode);
  }

  Future<Map<String, dynamic>> getProfile() async {
    final url = Uri.parse('$baseUrl/users/me');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      final profile = Map<String, dynamic>.from(data['data']);
      await setProfile(profile);
      return profile;
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to load profile'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> recordConsent({
    String consentVersion = 'v1.0',
    bool termsAccepted = true,
    bool privacyAccepted = true,
    bool educationalDisclaimerAccepted = true,
  }) async {
    final url = Uri.parse('$baseUrl/users/consent');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'consent_version': consentVersion,
        'terms_accepted': termsAccepted,
        'privacy_accepted': privacyAccepted,
        'educational_disclaimer_accepted': educationalDisclaimerAccepted,
      }),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to record consent'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> submitRiskAssessment({
    required String horizonCategory,
    required List<Map<String, dynamic>> answers,
    String questionnaireVersion = 'v1.0',
  }) async {
    final url = Uri.parse('$baseUrl/risk/assessments');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'questionnaire_version': questionnaireVersion,
        'horizon_category': horizonCategory,
        'answers': answers,
      }),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to submit risk assessment'),
      statusCode: response.statusCode,
    );
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

  Future<Map<String, dynamic>?> getQuote(String symbol) async {
    final url = Uri.parse('$baseUrl/market/quotes/${Uri.encodeComponent(symbol)}');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  // --- Paper Trading ---
  Future<Map<String, dynamic>> getAccount() async {
    final url = Uri.parse('$baseUrl/paper-trading/account');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to load account'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> submitOrder({
    required String symbol,
    required String side,
    required String orderType,
    required double quantity,
    double? limitPrice,
    String? idempotencyKey,
  }) async {
    final key = idempotencyKey ??
        'mob-ord-${DateTime.now().millisecondsSinceEpoch}-${math.Random().nextInt(900000) + 100000}';
    final cleanOrderType = orderType.toUpperCase();
    final url = Uri.parse('$baseUrl/paper-trading/orders');
    final response = await _httpClient.post(
      url,
      headers: _headers({'X-Idempotency-Key': key}),
      body: jsonEncode({
        'symbol': symbol,
        'side': side.toUpperCase(),
        'order_type': cleanOrderType,
        'quantity': quantity,
        if (cleanOrderType == 'LIMIT' && limitPrice != null) 'limit_price': limitPrice,
        'idempotency_key': key,
      }),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      final orderRes = Map<String, dynamic>.from(data['data']);
      double? toNum(dynamic v) {
        if (v == null) return null;
        if (v is num) return v.toDouble();
        if (v is String) return double.tryParse(v);
        return null;
      }
      final status = (orderRes['status'] ?? 'FILLED').toString().toUpperCase();
      final execPrice = status == 'FILLED'
          ? (toNum(orderRes['fill_price']) ?? toNum(orderRes['price']) ?? 0.0)
          : 0.0;
      final newEntry = <String, dynamic>{
        'id': orderRes['order_id'] ?? orderRes['id'] ?? 'ord-${DateTime.now().millisecondsSinceEpoch}',
        'order_id': orderRes['order_id'] ?? orderRes['id'] ?? 'ord-${DateTime.now().millisecondsSinceEpoch}',
        'symbol': symbol,
        'side': side.toUpperCase(),
        'order_type': cleanOrderType,
        'quantity': quantity,
        'price': execPrice,
        'fill_price': execPrice,
        'status': status,
        'rejection_reason': orderRes['rejection_reason'],
        'realized_pnl': toNum(orderRes['realized_pnl']),
        'created_at': DateTime.now().toIso8601String(),
        'is_replay': orderRes['is_replay'] == true,
      };
      recentOrdersNotifier.value = [newEntry, ...recentOrdersNotifier.value];
      return orderRes;
    }
    throw ApiException(
      _extractErrorMessage(response, 'Order submission failed'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>?> reconcileOrder(String idempotencyKey, [int limit = 10]) async {
    try {
      final orders = await getOrders(limit);
      for (final o in orders) {
        if (o['idempotency_key'] == idempotencyKey ||
            o['id'] == idempotencyKey ||
            o['order_id'] == idempotencyKey) {
          return o;
        }
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function(double amount)? mockDepositFundsHandler;

  Future<Map<String, dynamic>> depositFunds(double amount) async {
    if (mockDepositFundsHandler != null) {
      return mockDepositFundsHandler!(amount);
    }
    final url = Uri.parse('$baseUrl/paper-trading/deposit');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'amount': amount}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Virtual deposit failed'),
      statusCode: response.statusCode,
    );
  }

  Future<List<Map<String, dynamic>>> getOrders([int limit = 50]) async {
    final url = Uri.parse('$baseUrl/paper-trading/orders?limit=$limit');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      final orders = List<Map<String, dynamic>>.from(data['data']['orders'] ?? []);
      recentOrdersNotifier.value = orders;
      return orders;
    }
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw ApiException(
        _extractErrorMessage(response, 'Failed to fetch orders'),
        statusCode: response.statusCode,
      );
    }
    return recentOrdersNotifier.value;
  }

  // --- Indian Market Indices (Phase 1 Parity) ---
  Future<Map<String, dynamic>> getIndices({String? category, String? tier}) async {
    final queryParams = <String, String>{};
    if (category != null && category.isNotEmpty) queryParams['category'] = category.toLowerCase();
    if (tier != null && tier.isNotEmpty) queryParams['tier'] = tier;
    final uri = Uri.parse('$baseUrl/market/indices').replace(
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final response = await _httpClient.get(uri, headers: _headers());
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'indices': [], 'count': 0};
  }

  Future<Map<String, dynamic>?> getIndexQuote(String symbol) async {
    final uri = Uri.parse('$baseUrl/market/indices/${Uri.encodeComponent(symbol)}/quote');
    final response = await _httpClient.get(uri, headers: _headers());
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return null;
  }

  Future<Map<String, dynamic>> getIndexHistory(
    String symbol, {
    String? interval,
    String? range,
  }) async {
    final queryParams = <String, String>{};
    if (interval != null) queryParams['interval'] = interval;
    if (range != null) queryParams['range'] = range;
    final uri = Uri.parse('$baseUrl/market/indices/${Uri.encodeComponent(symbol)}/history').replace(
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final response = await _httpClient.get(uri, headers: _headers());
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'symbol': symbol, 'bars': []};
  }

  @visibleForTesting
  Future<Map<String, dynamic>> Function({bool confirmReset})? mockResetAccountHandler;

  Future<Map<String, dynamic>> resetAccount({bool confirmReset = true}) async {
    if (mockResetAccountHandler != null) {
      return mockResetAccountHandler!(confirmReset: confirmReset);
    }
    final url = Uri.parse('$baseUrl/paper-trading/reset');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'confirm_reset': confirmReset}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Account reset failed'),
      statusCode: response.statusCode,
    );
  }

  // --- Spending & CSV ---
  Future<Map<String, dynamic>> getTransactions() async {
    final url = Uri.parse('$baseUrl/spending/transactions');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200) {
      if (data['data'] != null) {
        return Map<String, dynamic>.from(data['data']);
      }
      return {'transactions': [], 'total': 0};
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to load transactions'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> previewCsv(String fileName, String csvContent) async {
    final url = Uri.parse('$baseUrl/spending/upload/preview');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'file_name': fileName, 'csv_content': csvContent}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'CSV preview failed'),
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> commitCsv(String previewId, [List<int>? acceptedIndices]) async {
    final url = Uri.parse('$baseUrl/spending/upload/commit');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'preview_id': previewId, 'accepted_indices': acceptedIndices}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'CSV commit failed'),
      statusCode: response.statusCode,
    );
  }

  // --- AI RAG Conversations & Chat ---
  Future<Map<String, dynamic>> createConversation([String title = 'Mobile Assistant']) async {
    final url = Uri.parse('$baseUrl/ai/conversations');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'title': title}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to create conversation'),
      statusCode: response.statusCode,
    );
  }

  Future<List<Map<String, dynamic>>> getConversations() async {
    final url = Uri.parse('$baseUrl/ai/conversations');
    final response = await _httpClient.get(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return List<Map<String, dynamic>>.from(data['data']['conversations'] ?? []);
    }
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw ApiException(
        _extractErrorMessage(response, 'Failed to fetch conversations'),
        statusCode: response.statusCode,
      );
    }
    return [];
  }

  Future<Map<String, dynamic>> sendAiMessage(String conversationId, String content) async {
    final url = Uri.parse('$baseUrl/ai/conversations/${Uri.encodeComponent(conversationId)}/messages');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({'content': content}),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'AI retrieval query failed'),
      statusCode: response.statusCode,
    );
  }

  // --- Market History & Technical Indicators ---
  Future<Map<String, dynamic>> getMarketHistory(
    String symbol, {
    String? interval,
    String? range,
    String? asOf,
  }) async {
    final queryParams = <String, String>{};
    if (interval != null) queryParams['interval'] = interval;
    if (range != null) queryParams['range'] = range;
    if (asOf != null) queryParams['as_of'] = asOf;
    final uri = Uri.parse('$baseUrl/market/history/${Uri.encodeComponent(symbol)}').replace(queryParameters: queryParams);
    final response = await _httpClient.get(uri, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'symbol': symbol, 'bars': []};
  }

  Future<List<Map<String, dynamic>>> getInstruments({String? market}) async {
    final queryParams = <String, String>{};
    if (market != null) queryParams['market'] = market;
    final uri = Uri.parse('$baseUrl/market/instruments').replace(queryParameters: queryParams);
    final response = await _httpClient.get(uri, headers: _headers());
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null && data['data']['instruments'] != null) {
      return List<Map<String, dynamic>>.from(data['data']['instruments']);
    }
    return [];
  }

  Future<Map<String, dynamic>> getIndicators(
    String symbol,
    String indicator, {
    int? period,
  }) async {
    final queryParams = <String, String>{'indicator': indicator};
    if (period != null) queryParams['period'] = period.toString();
    final uri = Uri.parse('$baseUrl/market/indicators/${Uri.encodeComponent(symbol)}').replace(queryParameters: queryParams);
    final response = await _httpClient.get(uri, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'series': []};
  }

  Future<Map<String, dynamic>> getMarketMode() async {
    final url = Uri.parse('$baseUrl/market/mode');
    final response = await _httpClient.get(url, headers: _headers());
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    return {'mode': 'INDIA_HISTORICAL_REPLAY', 'currency': 'INR'};
  }

  // --- AskFinEx AI Paper Investment Assistant ---
  Future<Map<String, dynamic>> sendAiAssistantMessage(
    String message, {
    Map<String, dynamic>? chartContext,
  }) async {
    final url = Uri.parse('$baseUrl/ai/assistant/chat');
    final response = await _httpClient.post(
      url,
      headers: _headers(),
      body: jsonEncode({
        'message': message,
        if (chartContext != null) 'chart_context': chartContext,
      }),
    );
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Assistant communication failed'),
      statusCode: response.statusCode,
    );
  }

  // Backward-compatible alias
  Future<Map<String, dynamic>> sendGeminiAssistantMessage(
    String message, {
    Map<String, dynamic>? chartContext,
  }) => sendAiAssistantMessage(message, chartContext: chartContext);

  Future<Map<String, dynamic>> executeProposal(String proposalId) async {
    final url = Uri.parse('$baseUrl/ai/assistant/proposals/${Uri.encodeComponent(proposalId)}/execute');
    final response = await _httpClient.post(url, headers: _headers());
    await _handleUnauthorizedIfNeeded(response);
    final data = _decodeJsonObject(response);
    if (response.statusCode == 200 && data['data'] != null) {
      return Map<String, dynamic>.from(data['data']);
    }
    throw ApiException(
      _extractErrorMessage(response, 'Failed to execute proposal'),
      statusCode: response.statusCode,
    );
  }
}

final apiClient = ApiClient();
