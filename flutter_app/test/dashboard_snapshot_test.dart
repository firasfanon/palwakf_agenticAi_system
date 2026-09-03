import 'package:flutter_test/flutter_test.dart';
import 'package:palwakf_agentic_ai/src/agentic_api.dart';

void main() {
  test('snapshot derives agent provider and model metrics', () {
    final snapshot = DashboardSnapshot(
      core: <String, dynamic>{'status': 'PASS'},
      learning: <String, dynamic>{'status': 'PASS'},
      agents: <Map<String, dynamic>>[
        <String, dynamic>{'runnable': true},
        <String, dynamic>{'runnable': false},
      ],
      modelProviders: <String, dynamic>{
        'ollama': <String, dynamic>{
          'healthy': true,
          'models': <String>['a', 'b']
        },
      },
      executionProviders: <String, dynamic>{
        'native': <String, dynamic>{'healthy': true},
        'hermes': <String, dynamic>{'healthy': false},
      },
      fetchedAt: DateTime(2026, 9, 2),
    );

    expect(snapshot.totalAgents, 2);
    expect(snapshot.runnableAgents, 1);
    expect(snapshot.modelCount, 2);
    expect(snapshot.healthyProviderCount, 2);
    expect(snapshot.discoveredProviderCount, 3);
    expect(snapshot.hasEndpointErrors, isFalse);
  });
}
