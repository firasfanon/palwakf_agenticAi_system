import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class DashboardSnapshot {
  DashboardSnapshot({
    required this.core,
    required this.learning,
    required this.agents,
    required this.modelProviders,
    required this.executionProviders,
    required this.fetchedAt,
  });

  final Map<String, dynamic> core;
  final Map<String, dynamic> learning;
  final List<Map<String, dynamic>> agents;
  final Map<String, dynamic> modelProviders;
  final Map<String, dynamic> executionProviders;
  final DateTime fetchedAt;

  bool get coreHealthy => core['status'] == 'PASS';
  bool get learningHealthy => learning['status'] == 'PASS';
  bool get hasEndpointErrors =>
      _hasError(core) ||
      _hasError(learning) ||
      _hasError(modelProviders) ||
      _hasError(executionProviders);

  int get totalAgents => agents.length;
  int get runnableAgents =>
      agents.where((agent) => agent['runnable'] == true).length;

  int get modelCount {
    final ollama = modelProviders['ollama'];
    if (ollama is! Map) return 0;
    final models = ollama['models'];
    return models is List ? models.length : 0;
  }

  int get healthyProviderCount {
    var count = 0;
    final ollama = modelProviders['ollama'];
    if (ollama is Map && ollama['healthy'] == true) count += 1;
    for (final value in executionProviders.values) {
      if (value is Map && value['healthy'] == true) count += 1;
    }
    return count;
  }

  int get discoveredProviderCount {
    var count = 0;
    if (modelProviders['ollama'] is Map) count += 1;
    count += executionProviders.values.whereType<Map>().length;
    return count;
  }

  static bool _hasError(Map<String, dynamic> value) =>
      value.containsKey('_error');
}

abstract class AgenticDataSource {
  Future<DashboardSnapshot> fetchSnapshot();
  String get resolvedBase;
}

class AgenticApi implements AgenticDataSource {
  AgenticApi({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;
  static const _configuredBase = String.fromEnvironment('AGENTIC_API_BASE');

  @override
  String get resolvedBase {
    if (_configuredBase.trim().isNotEmpty) {
      return _configuredBase.trim().replaceAll(RegExp(r'/$'), '');
    }
    if (kIsWeb) return Uri.base.origin;
    return 'http://127.0.0.1:8000';
  }

  Uri _uri(String path) => Uri.parse('$resolvedBase$path');

  Future<dynamic> _safeGet(String path) async {
    try {
      final response =
          await _client.get(_uri(path)).timeout(const Duration(seconds: 8));
      if (response.statusCode < 200 || response.statusCode >= 300) {
        return <String, dynamic>{
          '_error': 'HTTP_${response.statusCode}',
          '_path': path,
        };
      }
      return jsonDecode(utf8.decode(response.bodyBytes));
    } on TimeoutException {
      return <String, dynamic>{'_error': 'TIMEOUT', '_path': path};
    } catch (error) {
      return <String, dynamic>{
        '_error': error.runtimeType.toString(),
        '_path': path,
      };
    }
  }

  @override
  Future<DashboardSnapshot> fetchSnapshot() async {
    final results = await Future.wait<dynamic>([
      _safeGet('/api/v1/agentic/health'),
      _safeGet('/api/v1/agentic/learning/health'),
      _safeGet('/api/v1/agentic/agents'),
      _safeGet('/api/v1/agentic/providers/models'),
      _safeGet('/api/v1/agentic/providers/execution'),
    ]);

    final core = _asMap(results[0]);
    final learning = _asMap(results[1]);
    final agentPayload = results[2];
    final agents = agentPayload is List
        ? agentPayload
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList()
        : <Map<String, dynamic>>[];

    return DashboardSnapshot(
      core: core,
      learning: learning,
      agents: agents,
      modelProviders: _asMap(results[3]),
      executionProviders: _asMap(results[4]),
      fetchedAt: DateTime.now(),
    );
  }

  Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map) return Map<String, dynamic>.from(value);
    return <String, dynamic>{'_error': 'INVALID_PAYLOAD'};
  }
}
