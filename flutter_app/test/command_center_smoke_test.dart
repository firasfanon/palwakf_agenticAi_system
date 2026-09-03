import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:palwakf_agentic_ai/src/agentic_api.dart';
import 'package:palwakf_agentic_ai/src/command_center.dart';

class _FakeDataSource implements AgenticDataSource {
  @override
  String get resolvedBase => 'http://127.0.0.1:8000';

  @override
  Future<DashboardSnapshot> fetchSnapshot() async {
    return DashboardSnapshot(
      core: <String, dynamic>{
        'status': 'PASS',
        'agent_count': 14,
        'mapped_agent_count': 14,
        'self_authorization': 'FORBIDDEN',
        'authority_expansion': 'FORBIDDEN',
        'default_execution': 'READ_ONLY',
        'cross_project_access': 'DENY_BY_DEFAULT',
      },
      learning: <String, dynamic>{
        'status': 'PASS',
        'experience_store': 'AVAILABLE',
        'evaluation_engine': 'AVAILABLE',
        'learning_engine': 'AVAILABLE',
        'multi_agent_orchestrator': 'AVAILABLE',
        'workspace_authority': 'EXTERNAL_CONTRACT',
        'mind_review': 'EXTERNAL_CONTRACT',
        'auto_promotion': 'FORBIDDEN',
      },
      agents: List<Map<String, dynamic>>.generate(14, (index) {
        return <String, dynamic>{
          'agent_id': 'agent_$index',
          'role_id': index == 0 ? 'coordinator' : 'tester',
          'runtime_profile_id': 'runtime_$index',
          'skill_ids': <String>['skill_$index'],
          'runnable': true,
          'authority_status': 'EXTERNAL_AUTHORITY_REQUIRED',
          'filesystem_scope': 'READ_ONLY_BY_DEFAULT',
        };
      }),
      modelProviders: <String, dynamic>{
        'ollama': <String, dynamic>{
          'provider_id': 'ollama',
          'healthy': true,
          'models': <String>['llama3.2:3b', 'qwen2.5:3b', 'gemma4'],
          'latency_ms': 4.2,
        },
      },
      executionProviders: <String, dynamic>{
        'native': <String, dynamic>{'provider_id': 'native', 'healthy': true},
        'hermes': <String, dynamic>{'provider_id': 'hermes', 'healthy': true},
      },
      fetchedAt: DateTime(2026, 9, 2, 17),
    );
  }
}

Future<void> _pumpCommandCenterAt(
  WidgetTester tester,
  Size logicalSize,
) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = logicalSize;

  await tester.pumpWidget(
    AgenticCommandCenterApp(dataSource: _FakeDataSource()),
  );

  // The fake source completes immediately. Two deterministic frames are enough
  // to render the initial shell and post-refresh snapshot.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 1));
}

Future<void> _disposeCommandCenterView(WidgetTester tester) async {
  // Unmount the Material/semantics tree before restoring test-view metrics.
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pump();

  tester.view.resetPhysicalSize();
  tester.view.resetDevicePixelRatio();

  // Flush the metrics restoration against the now-empty tree.
  await tester.pump();
}

Future<void> _runAtSize(
  WidgetTester tester,
  Size size,
  Future<void> Function() assertions,
) async {
  await _pumpCommandCenterAt(tester, size);
  try {
    await assertions();
    expect(tester.takeException(), isNull);
  } finally {
    await _disposeCommandCenterView(tester);
  }
}

void main() {
  testWidgets(
    'desktop command center renders Arabic RTL without exception',
    (tester) async {
      await _runAtSize(tester, const Size(1440, 900), () async {
        expect(find.text('مركز قيادة PalWakf Agentic AI'), findsOneWidget);
        expect(find.text('الوكلاء'), findsWidgets);
        expect(find.text('الحوكمة والسلطة'), findsOneWidget);
        expect(find.text('14'), findsOneWidget);
      });
    },
  );

  testWidgets('mid width rail remains overflow free', (tester) async {
    await _runAtSize(tester, const Size(900, 700), () async {
      expect(find.byType(NavigationRail), findsOneWidget);
    });
  });

  testWidgets(
    'narrow command center keeps primary navigation usable',
    (tester) async {
      await _runAtSize(tester, const Size(390, 844), () async {
        expect(find.byType(NavigationBar), findsOneWidget);
        expect(find.text('الرئيسية'), findsOneWidget);
        expect(find.text('الوكلاء'), findsWidgets);
      });
    },
  );

  testWidgets(
    'compact breakpoint uses bottom navigation below 760',
    (tester) async {
      await _runAtSize(tester, const Size(759, 700), () async {
        expect(find.byType(NavigationBar), findsOneWidget);
        expect(find.byType(NavigationRail), findsNothing);
      });
    },
  );

  testWidgets('rail breakpoint remains overflow free at 760', (tester) async {
    await _runAtSize(tester, const Size(760, 700), () async {
      expect(find.byType(NavigationRail), findsOneWidget);
      expect(find.byType(NavigationBar), findsNothing);
    });
  });
}
