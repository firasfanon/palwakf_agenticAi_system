import 'dart:async';

import 'package:flutter/material.dart';

import 'agentic_api.dart';

const _navItems = <_NavItem>[
  _NavItem('الرئيسية', Icons.dashboard_rounded),
  _NavItem('الوكلاء', Icons.smart_toy_rounded),
  _NavItem('التشغيل', Icons.play_circle_fill_rounded),
  _NavItem('التعلم', Icons.psychology_rounded),
  _NavItem('المزودون', Icons.hub_rounded),
  _NavItem('الحوكمة والسلطة', Icons.gpp_good_rounded),
  _NavItem('الأدلة', Icons.fact_check_rounded),
  _NavItem('الإعدادات', Icons.settings_rounded),
];

const _roleLabels = <String, String>{
  'coordinator': 'المنسق',
  'sovereignty_reviewer': 'مراجع السيادة',
  'knowledge_researcher': 'باحث المعرفة',
  'ui_ux_designer': 'مصمم الواجهة والتجربة',
  'documentation_handoff': 'التوثيق والتوريث',
  'product_analyst': 'محلل المنتج',
  'solution_architect': 'معماري الحلول',
  'qa_security_reviewer': 'مراجع الجودة والأمان',
  'tester': 'الاختبارات',
  'coding_builder': 'منفذ البرمجة',
  'frontend_engineer': 'مهندس الواجهة',
  'backend_engineer': 'مهندس الخلفية',
  'database_engineer': 'مهندس قواعد البيانات',
  'release_engineer': 'مهندس الإصدار',
};

class AgenticCommandCenterApp extends StatelessWidget {
  const AgenticCommandCenterApp({super.key, this.dataSource});

  final AgenticDataSource? dataSource;

  @override
  Widget build(BuildContext context) {
    final seed = const Color(0xFF2D6A9F);
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'PalWakf Agentic AI',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
          surface: const Color(0xFF101820),
        ),
        scaffoldBackgroundColor: const Color(0xFF0B1117),
        dividerColor: Colors.white12,
        textTheme: const TextTheme(
          headlineLarge: TextStyle(fontWeight: FontWeight.w800, height: 1.15),
          headlineMedium: TextStyle(fontWeight: FontWeight.w800),
          titleLarge: TextStyle(fontWeight: FontWeight.w700),
          titleMedium: TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      home: Directionality(
        textDirection: TextDirection.rtl,
        child: CommandCenterShell(dataSource: dataSource ?? AgenticApi()),
      ),
    );
  }
}

class CommandCenterShell extends StatefulWidget {
  const CommandCenterShell({super.key, required this.dataSource});

  final AgenticDataSource dataSource;

  @override
  State<CommandCenterShell> createState() => _CommandCenterShellState();
}

class _CommandCenterShellState extends State<CommandCenterShell> {
  DashboardSnapshot? _snapshot;
  bool _loading = true;
  bool _autoRefresh = true;
  int _selected = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _refresh();
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (_autoRefresh) _refresh(silent: true);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh({bool silent = false}) async {
    if (!silent && mounted) setState(() => _loading = true);
    final next = await widget.dataSource.fetchSnapshot();
    if (!mounted) return;
    setState(() {
      _snapshot = next;
      _loading = false;
    });
  }

  void _go(int index) => setState(() => _selected = index);

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        final compact = width < 760;
        final extended = width >= 1180;
        final page = _buildPage();

        if (compact) {
          return Scaffold(
            appBar: AppBar(
              title: const _BrandTitle(compact: true),
              actions: [_RefreshButton(onPressed: _refresh)],
            ),
            body: page,
            bottomNavigationBar: NavigationBar(
              selectedIndex: _selected > 4 ? 4 : _selected,
              onDestinationSelected: (index) => _go(index),
              labelBehavior:
                  NavigationDestinationLabelBehavior.onlyShowSelected,
              destinations: _navItems.take(5).map((item) {
                return NavigationDestination(
                    icon: Icon(item.icon), label: item.label);
              }).toList(),
            ),
            drawer: Drawer(
              child: SafeArea(
                child: ListView(
                  padding: const EdgeInsets.all(12),
                  children: [
                    const _BrandTitle(compact: false),
                    const SizedBox(height: 20),
                    for (var i = 5; i < _navItems.length; i++)
                      ListTile(
                        leading: Icon(_navItems[i].icon),
                        title: Text(_navItems[i].label),
                        selected: _selected == i,
                        onTap: () {
                          Navigator.pop(context);
                          _go(i);
                        },
                      ),
                  ],
                ),
              ),
            ),
          );
        }

        return Scaffold(
          body: Row(
            children: [
              SizedBox(
                width: extended ? 250 : 80,
                child: NavigationRail(
                  extended: extended,
                  selectedIndex: _selected,
                  onDestinationSelected: _go,
                  backgroundColor: const Color(0xFF0F1720),
                  minWidth: 80,
                  minExtendedWidth: 250,
                  leading: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 20, 12, 28),
                    child: SizedBox(
                      width: extended ? 220 : 44,
                      child: extended
                          ? const _BrandTitle(compact: false)
                          : const Icon(Icons.auto_awesome_rounded),
                    ),
                  ),
                  trailing: Padding(
                    padding: const EdgeInsets.only(top: 20),
                    child: extended
                        ? _ConnectionMiniCard(snapshot: _snapshot)
                        : _HealthDot(snapshot: _snapshot),
                  ),
                  destinations: _navItems.map((item) {
                    return NavigationRailDestination(
                      icon: Icon(item.icon),
                      selectedIcon: Icon(item.icon),
                      label: Text(item.label),
                    );
                  }).toList(),
                ),
              ),
              const VerticalDivider(width: 1),
              Expanded(
                child: Column(
                  children: [
                    _TopBar(
                      snapshot: _snapshot,
                      loading: _loading,
                      autoRefresh: _autoRefresh,
                      onRefresh: _refresh,
                      onAutoRefresh: (value) =>
                          setState(() => _autoRefresh = value),
                    ),
                    const Divider(height: 1),
                    Expanded(child: page),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildPage() {
    final snapshot = _snapshot;
    if (_loading && snapshot == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (snapshot == null) {
      return _EmptyState(
        icon: Icons.cloud_off_rounded,
        title: 'تعذر تحميل الحالة',
        body: 'لم تتوفر بعد قراءة صالحة من Agentic API.',
        action: FilledButton.icon(
          onPressed: _refresh,
          icon: const Icon(Icons.refresh_rounded),
          label: const Text('إعادة المحاولة'),
        ),
      );
    }

    return switch (_selected) {
      0 => _DashboardPage(snapshot: snapshot, go: _go),
      1 => _AgentsPage(agents: snapshot.agents),
      2 => _OperationsPage(snapshot: snapshot),
      3 => _LearningPage(snapshot: snapshot),
      4 => _ProvidersPage(snapshot: snapshot),
      5 => _AuthorityPage(snapshot: snapshot),
      6 => _EvidencePage(snapshot: snapshot),
      _ => _SettingsPage(apiBase: widget.dataSource.resolvedBase),
    };
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.snapshot,
    required this.loading,
    required this.autoRefresh,
    required this.onRefresh,
    required this.onAutoRefresh,
  });

  final DashboardSnapshot? snapshot;
  final bool loading;
  final bool autoRefresh;
  final VoidCallback onRefresh;
  final ValueChanged<bool> onAutoRefresh;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 72,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 22),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final showStatus = constraints.maxWidth >= 380;
            final showAutoRefresh = constraints.maxWidth >= 620;
            final compactBrand = constraints.maxWidth < 720;

            return Row(
              children: [
                Expanded(child: _BrandTitle(compact: compactBrand)),
                if (showStatus) ...[
                  _SystemStatus(snapshot: snapshot),
                  const SizedBox(width: 12),
                ],
                if (showAutoRefresh)
                  Tooltip(
                    message: 'تحديث تلقائي كل 15 ثانية',
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.autorenew_rounded, size: 18),
                        Switch(value: autoRefresh, onChanged: onAutoRefresh),
                      ],
                    ),
                  ),
                IconButton(
                  onPressed: loading ? null : onRefresh,
                  tooltip: 'تحديث الآن',
                  icon: loading
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.refresh_rounded),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _DashboardPage extends StatelessWidget {
  const _DashboardPage({required this.snapshot, required this.go});

  final DashboardSnapshot snapshot;
  final ValueChanged<int> go;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        _Hero(snapshot: snapshot),
        const SizedBox(height: 18),
        LayoutBuilder(
          builder: (context, constraints) {
            final cardWidth = constraints.maxWidth >= 1100
                ? (constraints.maxWidth - 42) / 4
                : constraints.maxWidth >= 700
                    ? (constraints.maxWidth - 14) / 2
                    : constraints.maxWidth;
            return Wrap(
              spacing: 14,
              runSpacing: 14,
              children: [
                _MetricCard(
                  width: cardWidth,
                  label: 'الوكلاء',
                  value: '${snapshot.totalAgents}',
                  detail: '${snapshot.runnableAgents} جاهزون للتخطيط المحكوم',
                  icon: Icons.smart_toy_rounded,
                  onTap: () => go(1),
                ),
                _MetricCard(
                  width: cardWidth,
                  label: 'المزودون',
                  value:
                      '${snapshot.healthyProviderCount}/${snapshot.discoveredProviderCount}',
                  detail: 'حالة Native / Hermes / Ollama',
                  icon: Icons.hub_rounded,
                  onTap: () => go(4),
                ),
                _MetricCard(
                  width: cardWidth,
                  label: 'النماذج المحلية',
                  value: '${snapshot.modelCount}',
                  detail: 'مكتشفة عبر Ollama',
                  icon: Icons.memory_rounded,
                  onTap: () => go(4),
                ),
                _MetricCard(
                  width: cardWidth,
                  label: 'التعلم',
                  value: snapshot.learningHealthy ? 'جاهز' : 'مقيّد',
                  detail: 'Experience → Evaluation → Candidate',
                  icon: Icons.psychology_rounded,
                  onTap: () => go(3),
                ),
              ],
            );
          },
        ),
        const SizedBox(height: 18),
        _SectionCard(
          title: 'المسار الوكيلي الحاكم',
          subtitle:
              'تدفق مرئي للمنظومة — لا يعني أن كل مرحلة تعمل الآن في Run حي.',
          child: const _Pipeline(),
        ),
        const SizedBox(height: 18),
        LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 900;
            final authority = _SectionCard(
              title: 'حدود السلطة',
              subtitle: 'تظل أضيق سياسة هي الحاكمة.',
              child: _AuthoritySummary(snapshot: snapshot),
            );
            final activity = _SectionCard(
              title: 'نبض النظام',
              subtitle: 'قراءات حقيقية من واجهات الحالة المتاحة.',
              child: _Activity(snapshot: snapshot),
            );
            if (stacked) {
              return Column(
                  children: [authority, const SizedBox(height: 18), activity]);
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: authority),
                const SizedBox(width: 18),
                Expanded(child: activity)
              ],
            );
          },
        ),
        const SizedBox(height: 18),
        _SectionCard(
          title: 'إجراءات سريعة آمنة',
          subtitle:
              'تنقلات وقراءات فقط؛ لا يوجد تشغيل أو كتابة تلقائية من لوحة V1.',
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _ActionButton(
                  label: 'استعراض الوكلاء',
                  icon: Icons.smart_toy_rounded,
                  onTap: () => go(1)),
              _ActionButton(
                  label: 'حالة المزودين',
                  icon: Icons.hub_rounded,
                  onTap: () => go(4)),
              _ActionButton(
                  label: 'التعلم والتقييم',
                  icon: Icons.psychology_rounded,
                  onTap: () => go(3)),
              _ActionButton(
                  label: 'السلطة والحوكمة',
                  icon: Icons.gpp_good_rounded,
                  onTap: () => go(5)),
              _ActionButton(
                  label: 'الأدلة',
                  icon: Icons.fact_check_rounded,
                  onTap: () => go(6)),
            ],
          ),
        ),
      ],
    );
  }
}

class _AgentsPage extends StatefulWidget {
  const _AgentsPage({required this.agents});

  final List<Map<String, dynamic>> agents;

  @override
  State<_AgentsPage> createState() => _AgentsPageState();
}

class _AgentsPageState extends State<_AgentsPage> {
  String _query = '';
  bool? _runnable;

  @override
  Widget build(BuildContext context) {
    final q = _query.trim().toLowerCase();
    final filtered = widget.agents.where((agent) {
      final role = '${agent['role_id'] ?? ''}'.toLowerCase();
      final id = '${agent['agent_id'] ?? ''}'.toLowerCase();
      final matchesText = q.isEmpty ||
          role.contains(q) ||
          id.contains(q) ||
          (_roleLabels[role] ?? '').contains(_query);
      final matchesRun = _runnable == null || agent['runnable'] == _runnable;
      return matchesText && matchesRun;
    }).toList();

    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'أسطول الوكلاء',
          subtitle:
              'الهوية والدور وRuntime Profile والمهارات وحدود التنفيذ كما يعرضها Agentic Core.',
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SizedBox(
              width: 360,
              child: TextField(
                onChanged: (value) => setState(() => _query = value),
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search_rounded),
                  hintText: 'ابحث عن وكيل أو دور...',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            FilterChip(
                label: const Text('الكل'),
                selected: _runnable == null,
                onSelected: (_) => setState(() => _runnable = null)),
            FilterChip(
                label: const Text('جاهز'),
                selected: _runnable == true,
                onSelected: (_) => setState(() => _runnable = true)),
            FilterChip(
                label: const Text('غير جاهز'),
                selected: _runnable == false,
                onSelected: (_) => setState(() => _runnable = false)),
          ],
        ),
        const SizedBox(height: 16),
        if (filtered.isEmpty)
          const _EmptyState(
            icon: Icons.search_off_rounded,
            title: 'لا توجد نتائج',
            body: 'غيّر البحث أو المرشح.',
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth >= 1100
                  ? (constraints.maxWidth - 28) / 3
                  : constraints.maxWidth >= 700
                      ? (constraints.maxWidth - 14) / 2
                      : constraints.maxWidth;
              return Wrap(
                spacing: 14,
                runSpacing: 14,
                children: filtered
                    .map((agent) => _AgentCard(agent: agent, width: width))
                    .toList(),
              );
            },
          ),
      ],
    );
  }
}

class _OperationsPage extends StatelessWidget {
  const _OperationsPage({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'مركز التشغيل',
          subtitle:
              'واجهة المراقبة V1 لا تنشئ Runs من تلقاء نفسها ولا توسّع السلطة.',
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'حالة التنفيذ',
          subtitle:
              'المتاح حاليًا هو Provider/Runtime readiness، وليس قائمة Runs حية.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _TruthRow(
                  label: 'التنفيذ الافتراضي',
                  value: '${snapshot.core['default_execution'] ?? 'UNKNOWN'}'),
              _TruthRow(
                  label: 'التفويض الذاتي',
                  value: '${snapshot.core['self_authorization'] ?? 'UNKNOWN'}'),
              _TruthRow(
                  label: 'توسيع السلطة',
                  value:
                      '${snapshot.core['authority_expansion'] ?? 'UNKNOWN'}'),
              const Divider(),
              const Text(
                  'لا توجد في Agentic API الحالية واجهة GET لقائمة التشغيلات النشطة؛ لذلك لا تعرض هذه الشاشة بيانات Run مصطنعة.'),
            ],
          ),
        ),
      ],
    );
  }
}

class _LearningPage extends StatelessWidget {
  const _LearningPage({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'التعلم والتقييم',
          subtitle:
              'يعرض حالة محركات التعلم دون الادعاء أن Candidate أصبح معرفة مؤسسية معتمدة.',
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'سلسلة التعلم المحكومة',
          subtitle: 'المراجعة الخارجية تبقى شرطًا قبل قبول المعرفة.',
          child: const _LearningPipeline(),
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'حالة المحركات',
          subtitle: 'قراءة مباشرة من /api/v1/agentic/learning/health',
          child: _KeyValueGrid(data: snapshot.learning),
        ),
      ],
    );
  }
}

class _ProvidersPage extends StatelessWidget {
  const _ProvidersPage({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final cards = <Widget>[];
    final ollama = snapshot.modelProviders['ollama'];
    if (ollama is Map) {
      cards.add(_ProviderCard(
          title: 'Ollama', data: Map<String, dynamic>.from(ollama)));
    }
    for (final entry in snapshot.executionProviders.entries) {
      if (entry.value is Map) {
        cards.add(_ProviderCard(
            title: entry.key,
            data: Map<String, dynamic>.from(entry.value as Map)));
      }
    }
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'النماذج والمزودون',
          subtitle:
              'Ollama للنماذج المحلية، وNative/Hermes كمزودي تنفيذ قابلين للاستبدال ضمن السلطة.',
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth >= 1000
                ? (constraints.maxWidth - 28) / 3
                : constraints.maxWidth >= 650
                    ? (constraints.maxWidth - 14) / 2
                    : constraints.maxWidth;
            return Wrap(
              spacing: 14,
              runSpacing: 14,
              children: cards
                  .map((card) => SizedBox(width: width, child: card))
                  .toList(),
            );
          },
        ),
      ],
    );
  }
}

class _AuthorityPage extends StatelessWidget {
  const _AuthorityPage({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'الحوكمة والسلطة',
          subtitle: 'هذه الشاشة تشرح حدود النظام؛ ولا تمنح أي صلاحية جديدة.',
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'السلطة الخارجية الحاكمة',
          subtitle:
              'Workspace/Human explicit authority تحدد الحد الأعلى، وAgentic AI يستطيع التضييق أو الرفض فقط.',
          child: _AuthoritySummary(snapshot: snapshot, expanded: true),
        ),
        const SizedBox(height: 16),
        const _SectionCard(
          title: 'ثوابت غير قابلة للتجاوز',
          subtitle: 'تظل هذه الحدود نافذة حتى صدور تفويض صريح مستقل.',
          child: Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _RulePill('NO SELF AUTHORIZATION', Icons.lock_rounded),
              _RulePill('NO AUTHORITY EXPANSION', Icons.security_rounded),
              _RulePill('CROSS PROJECT = DENY', Icons.domain_disabled_rounded),
              _RulePill('WRITE = SEPARATE AUTHORITY', Icons.edit_off_rounded),
              _RulePill(
                  'AUTO PROMOTION = FORBIDDEN', Icons.psychology_alt_rounded),
            ],
          ),
        ),
      ],
    );
  }
}

class _EvidencePage extends StatelessWidget {
  const _EvidencePage({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'الأدلة والتدقيق',
          subtitle:
              'يعرض نموذج الدليل المقبول وحدود ما هو متاح عبر API الحالية.',
        ),
        const SizedBox(height: 16),
        const _SectionCard(
          title: 'Run Lineage المعتمد',
          subtitle: 'السلسلة التي أغلقت Mega Batch B تقنيًا.',
          child: _EvidenceLineage(),
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'الوضع الحالي',
          subtitle:
              'لا توجد بعد واجهة GET عامة لاستعراض ملفات Evidence من Flutter V1.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _TruthRow(
                  label: 'Core',
                  value: snapshot.coreHealthy ? 'PASS' : 'NOT PASS'),
              _TruthRow(
                  label: 'Learning',
                  value: snapshot.learningHealthy ? 'PASS' : 'NOT PASS'),
              const _TruthRow(
                  label: 'Institutional auto-promotion', value: 'FORBIDDEN'),
              const SizedBox(height: 8),
              const Text(
                  'سيضاف مستعرض Evidence فقط عندما يوفر Backend عقد قراءة مخصصًا وآمنًا؛ لن تقرأ الواجهة نظام الملفات مباشرة.'),
            ],
          ),
        ),
      ],
    );
  }
}

class _SettingsPage extends StatelessWidget {
  const _SettingsPage({required this.apiBase});
  final String apiBase;

  @override
  Widget build(BuildContext context) {
    return _PageScroll(
      children: [
        const _PageHeader(
          title: 'الإعدادات',
          subtitle: 'إعدادات عرض محلية فقط في هذه النسخة.',
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'اتصال Agentic API',
          subtitle: 'يمكن تغييره وقت البناء/التشغيل عبر AGENTIC_API_BASE.',
          child: SelectableText(apiBase,
              style: Theme.of(context).textTheme.titleMedium),
        ),
        const SizedBox(height: 16),
        const _SectionCard(
          title: 'سياسة النسخة V1',
          subtitle: 'لوحة تشغيل ومراقبة لا تمنح صلاحيات كتابة.',
          child: Text(
              'READ_ONLY_VISIBILITY_BY_DEFAULT = TRUE\nREACT_FALLBACK = PRESERVED\nPRODUCTION = NOT CERTIFIED'),
        ),
      ],
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final healthy = snapshot.coreHealthy &&
        snapshot.learningHealthy &&
        !snapshot.hasEndpointErrors;
    return Container(
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: [Color(0xFF183B59), Color(0xFF102535), Color(0xFF101820)],
        ),
        border: Border.all(color: Colors.white12),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final narrow = constraints.maxWidth < 720;
          final copy = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('مركز قيادة PalWakf Agentic AI',
                  style: Theme.of(context).textTheme.headlineLarge),
              const SizedBox(height: 10),
              Text(
                'منظومة تشغيل ومراقبة الوكلاء والتعلم المحكوم تحت سلطة خارجية، مع مزودين قابلين للاستبدال.',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(color: Colors.white70, height: 1.6),
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _StatusChip(
                      label: healthy ? 'SYSTEM HEALTHY' : 'SYSTEM PARTIAL',
                      good: healthy),
                  _StatusChip(
                      label: '${snapshot.totalAgents} AGENTS',
                      good: snapshot.totalAgents == 14),
                  const _StatusChip(label: 'EXTERNAL AUTHORITY', good: true),
                  const _StatusChip(label: 'READ ONLY DEFAULT', good: true),
                ],
              ),
            ],
          );
          final mark = Container(
            width: narrow ? double.infinity : 240,
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.black.withAlpha(55),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: Colors.white12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.auto_awesome_rounded, size: 34),
                const SizedBox(height: 14),
                const Text('FINAL INVARIANT',
                    style: TextStyle(
                        color: Colors.white60,
                        fontSize: 12,
                        letterSpacing: 1.1)),
                const SizedBox(height: 8),
                Text('EXECUTE + LEARN',
                    style: Theme.of(context).textTheme.titleLarge),
                const Text('under external authority',
                    style: TextStyle(color: Colors.white70)),
              ],
            ),
          );
          if (narrow) {
            return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [copy, const SizedBox(height: 20), mark]);
          }
          return Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
            Expanded(child: copy),
            const SizedBox(width: 24),
            mark
          ]);
        },
      ),
    );
  }
}

class _Pipeline extends StatelessWidget {
  const _Pipeline();

  @override
  Widget build(BuildContext context) {
    const nodes = <(String, IconData)>[
      ('المهمة', Icons.assignment_rounded),
      ('الوكيل', Icons.smart_toy_rounded),
      ('المهارة', Icons.extension_rounded),
      ('النموذج', Icons.memory_rounded),
      ('التنفيذ', Icons.play_circle_rounded),
      ('الأدوات', Icons.construction_rounded),
      ('النتيجة', Icons.task_alt_rounded),
      ('التقييم', Icons.rule_rounded),
      ('التعلم', Icons.psychology_rounded),
      ('المراجعة', Icons.verified_user_rounded),
    ];
    return Wrap(
      spacing: 8,
      runSpacing: 10,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        for (var i = 0; i < nodes.length; i++) ...[
          _PipelineNode(label: nodes[i].$1, icon: nodes[i].$2),
          if (i != nodes.length - 1)
            const Icon(Icons.arrow_back_rounded,
                size: 18, color: Colors.white38),
        ],
      ],
    );
  }
}

class _LearningPipeline extends StatelessWidget {
  const _LearningPipeline();

  @override
  Widget build(BuildContext context) {
    const items = [
      ('RunReceipt', 'إثبات التشغيل'),
      ('ExperienceRecord', 'الخبرة'),
      ('EvaluationReceipt', 'التقييم'),
      ('LearningCandidate', 'مرشح التعلم'),
      ('Mind Review', 'مراجعة خارجية'),
      ('Accepted Knowledge', 'اعتماد مؤسسي فقط'),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: items.map((item) {
        return Container(
          width: 190,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xFF0D2231),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.$1,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text(item.$2, style: const TextStyle(color: Colors.white60))
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _EvidenceLineage extends StatelessWidget {
  const _EvidenceLineage();

  @override
  Widget build(BuildContext context) {
    return const Text(
      'Execution → RunReceipt → ExperienceRecord → EvaluationReceipt → LearningCandidate → External Review → Certification',
      style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, height: 1.8),
    );
  }
}

class _AuthoritySummary extends StatelessWidget {
  const _AuthoritySummary({required this.snapshot, this.expanded = false});
  final DashboardSnapshot snapshot;
  final bool expanded;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[
      _TruthRow(
          label: 'Self authorization',
          value: '${snapshot.core['self_authorization'] ?? 'UNKNOWN'}'),
      _TruthRow(
          label: 'Authority expansion',
          value: '${snapshot.core['authority_expansion'] ?? 'UNKNOWN'}'),
      _TruthRow(
          label: 'Cross-project',
          value: '${snapshot.core['cross_project_access'] ?? 'UNKNOWN'}'),
      _TruthRow(
          label: 'Default execution',
          value: '${snapshot.core['default_execution'] ?? 'UNKNOWN'}'),
    ];
    if (expanded) {
      rows.addAll(const [
        _TruthRow(
            label: 'Accepted project knowledge auto-write', value: 'FORBIDDEN'),
        _TruthRow(label: 'Bounded write', value: 'SEPARATE EXPLICIT AUTHORITY'),
        _TruthRow(label: 'Production', value: 'NOT CERTIFIED'),
      ]);
    }
    return Column(children: rows);
  }
}

class _Activity extends StatelessWidget {
  const _Activity({required this.snapshot});
  final DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final items = [
      (
        'Agentic Core',
        snapshot.coreHealthy ? 'PASS' : 'CHECK',
        Icons.account_tree_rounded
      ),
      (
        'Learning Engine',
        snapshot.learningHealthy ? 'PASS' : 'CHECK',
        Icons.psychology_rounded
      ),
      (
        'Providers',
        '${snapshot.healthyProviderCount} healthy',
        Icons.hub_rounded
      ),
      (
        'Agents',
        '${snapshot.runnableAgents}/${snapshot.totalAgents} runnable',
        Icons.smart_toy_rounded
      ),
    ];
    return Column(
      children: [
        for (final item in items)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Icon(item.$3),
            title: Text(item.$1),
            trailing: Text(item.$2,
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        const Divider(),
        Align(
          alignment: Alignment.centerRight,
          child: Text('آخر قراءة: ${_formatTime(snapshot.fetchedAt)}',
              style: const TextStyle(color: Colors.white54)),
        ),
      ],
    );
  }
}

class _AgentCard extends StatelessWidget {
  const _AgentCard({required this.agent, required this.width});
  final Map<String, dynamic> agent;
  final double width;

  @override
  Widget build(BuildContext context) {
    final role = '${agent['role_id'] ?? 'unknown'}';
    final skills = agent['skill_ids'] is List
        ? List<dynamic>.from(agent['skill_ids'] as List)
        : <dynamic>[];
    final runnable = agent['runnable'] == true;
    return SizedBox(
      width: width,
      child: _SectionCard(
        title: _roleLabels[role] ?? role,
        subtitle: '${agent['agent_id'] ?? ''}',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                _StatusChip(
                    label: runnable ? 'RUNNABLE' : 'NOT READY', good: runnable),
                _StatusChip(
                    label: '${agent['authority_status'] ?? 'UNKNOWN'}',
                    good: true),
              ],
            ),
            const SizedBox(height: 12),
            _TruthRow(
                label: 'Runtime',
                value: '${agent['runtime_profile_id'] ?? 'UNKNOWN'}'),
            _TruthRow(
                label: 'Filesystem',
                value: '${agent['filesystem_scope'] ?? 'UNKNOWN'}'),
            const SizedBox(height: 8),
            Text('المهارات (${skills.length})',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            Text(
                skills.isEmpty
                    ? 'لا توجد مهارات معلنة'
                    : skills.take(4).join('\n'),
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white70, height: 1.45)),
          ],
        ),
      ),
    );
  }
}

class _ProviderCard extends StatelessWidget {
  const _ProviderCard({required this.title, required this.data});
  final String title;
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final healthy = data['healthy'] == true;
    final models = data['models'];
    return _SectionCard(
      title: title,
      subtitle: '${data['provider_id'] ?? title}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
              alignment: Alignment.centerRight,
              child: _StatusChip(
                  label: healthy ? 'HEALTHY' : 'NOT READY', good: healthy)),
          const SizedBox(height: 10),
          if (data['version_output'] != null)
            _TruthRow(label: 'Version', value: '${data['version_output']}'),
          if (data['certification'] != null)
            _TruthRow(
                label: 'Certification', value: '${data['certification']}'),
          if (data['latency_ms'] != null)
            _TruthRow(label: 'Latency', value: '${data['latency_ms']} ms'),
          if (models is List)
            _TruthRow(label: 'Models', value: '${models.length}'),
          if (data['_error'] != null)
            _TruthRow(label: 'Read error', value: '${data['_error']}'),
        ],
      ),
    );
  }
}

class _KeyValueGrid extends StatelessWidget {
  const _KeyValueGrid({required this.data});
  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: data.entries.map((entry) {
        return Container(
          constraints: const BoxConstraints(minWidth: 220),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: Colors.white.withAlpha(10),
              borderRadius: BorderRadius.circular(12)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(entry.key,
                  style: const TextStyle(color: Colors.white54, fontSize: 12)),
              const SizedBox(height: 4),
              Text('${entry.value}',
                  style: const TextStyle(fontWeight: FontWeight.w700))
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _PageScroll extends StatelessWidget {
  const _PageScroll({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Scrollbar(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(22),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1440),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: children),
          ),
        ),
      ),
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.title, required this.subtitle});
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 6),
        Text(subtitle,
            style: const TextStyle(color: Colors.white60, height: 1.5))
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard(
      {required this.title, required this.subtitle, required this.child});
  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF111C25),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white12),
        boxShadow: const [
          BoxShadow(
              color: Color(0x30000000), blurRadius: 22, offset: Offset(0, 10))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(subtitle,
              style: const TextStyle(color: Colors.white54, height: 1.4)),
          const SizedBox(height: 16),
          child,
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard(
      {required this.width,
      required this.label,
      required this.value,
      required this.detail,
      required this.icon,
      required this.onTap});
  final double width;
  final String label;
  final String value;
  final String detail;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: Material(
        color: const Color(0xFF111C25),
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: Colors.white12)),
            child: Row(
              children: [
                Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                        color: const Color(0xFF1B527C),
                        borderRadius: BorderRadius.circular(14)),
                    child: Icon(icon)),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(label,
                          style: const TextStyle(color: Colors.white60)),
                      const SizedBox(height: 2),
                      Text(value,
                          style: Theme.of(context).textTheme.headlineMedium),
                      Text(detail,
                          style: const TextStyle(
                              color: Colors.white54, fontSize: 12))
                    ],
                  ),
                ),
                const Icon(Icons.chevron_left_rounded, color: Colors.white38),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TruthRow extends StatelessWidget {
  const _TruthRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
              child:
                  Text(label, style: const TextStyle(color: Colors.white60))),
          const SizedBox(width: 12),
          Flexible(
              child: Text(value,
                  textAlign: TextAlign.left,
                  style: const TextStyle(fontWeight: FontWeight.w700)))
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton(
      {required this.label, required this.icon, required this.onTap});
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
        onPressed: onTap, icon: Icon(icon), label: Text(label));
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.good});
  final String label;
  final bool good;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: good ? const Color(0xFF123C32) : const Color(0xFF4A2E1A),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
            color: good ? const Color(0xFF2F8C70) : const Color(0xFF9A6639)),
      ),
      child: Text(label,
          style: const TextStyle(
              fontSize: 11, fontWeight: FontWeight.w800, letterSpacing: .2)),
    );
  }
}

class _SystemStatus extends StatelessWidget {
  const _SystemStatus({required this.snapshot});
  final DashboardSnapshot? snapshot;

  @override
  Widget build(BuildContext context) {
    if (snapshot == null) {
      return const _StatusChip(label: 'LOADING', good: false);
    }
    final healthy = snapshot!.coreHealthy &&
        snapshot!.learningHealthy &&
        !snapshot!.hasEndpointErrors;
    return _StatusChip(
        label: healthy ? 'SYSTEM HEALTHY' : 'SYSTEM PARTIAL', good: healthy);
  }
}

class _HealthDot extends StatelessWidget {
  const _HealthDot({required this.snapshot});
  final DashboardSnapshot? snapshot;

  @override
  Widget build(BuildContext context) {
    final healthy = snapshot != null &&
        snapshot!.coreHealthy &&
        snapshot!.learningHealthy &&
        !snapshot!.hasEndpointErrors;
    return Tooltip(
        message: healthy ? 'SYSTEM HEALTHY' : 'SYSTEM PARTIAL',
        child: Icon(Icons.circle,
            size: 12,
            color:
                healthy ? const Color(0xFF49C59B) : const Color(0xFFE0A35B)));
  }
}

class _ConnectionMiniCard extends StatelessWidget {
  const _ConnectionMiniCard({required this.snapshot});
  final DashboardSnapshot? snapshot;

  @override
  Widget build(BuildContext context) {
    final healthy = snapshot != null &&
        snapshot!.coreHealthy &&
        snapshot!.learningHealthy &&
        !snapshot!.hasEndpointErrors;
    return SizedBox(
      width: 220,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: Colors.white.withAlpha(9),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.white10)),
        child: Row(children: [
          Icon(Icons.circle,
              size: 10,
              color:
                  healthy ? const Color(0xFF49C59B) : const Color(0xFFE0A35B)),
          const SizedBox(width: 8),
          Expanded(
              child: Text(healthy ? 'النظام متصل' : 'اتصال جزئي',
                  style: const TextStyle(fontSize: 12)))
        ]),
      ),
    );
  }
}

class _BrandTitle extends StatelessWidget {
  const _BrandTitle({required this.compact});
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return const Text('PalWakf Agentic AI', overflow: TextOverflow.ellipsis);
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                gradient: const LinearGradient(
                    colors: [Color(0xFF4C9AD0), Color(0xFF285C89)])),
            child: const Icon(Icons.auto_awesome_rounded, size: 20)),
        const SizedBox(width: 10),
        const Flexible(
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
              Text('PalWakf Agentic AI',
                  style: TextStyle(fontWeight: FontWeight.w800)),
              Text('Command Center',
                  style: TextStyle(fontSize: 11, color: Colors.white54))
            ])),
      ],
    );
  }
}

class _RefreshButton extends StatelessWidget {
  const _RefreshButton({required this.onPressed});
  final VoidCallback onPressed;
  @override
  Widget build(BuildContext context) =>
      IconButton(onPressed: onPressed, icon: const Icon(Icons.refresh_rounded));
}

class _PipelineNode extends StatelessWidget {
  const _PipelineNode({required this.label, required this.icon});
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
          color: const Color(0xFF0D2738),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFF2A5B7E))),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 18),
        const SizedBox(width: 7),
        Text(label, style: const TextStyle(fontWeight: FontWeight.w700))
      ]),
    );
  }
}

class _RulePill extends StatelessWidget {
  const _RulePill(this.label, this.icon);
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
          color: const Color(0xFF14222C),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white12)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 17),
        const SizedBox(width: 7),
        Text(label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))
      ]),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState(
      {required this.icon,
      required this.title,
      required this.body,
      this.action});
  final IconData icon;
  final String title;
  final String body;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 46, color: Colors.white38),
          const SizedBox(height: 12),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(body,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white60)),
          if (action != null) ...[const SizedBox(height: 16), action!]
        ]),
      ),
    );
  }
}

class _NavItem {
  const _NavItem(this.label, this.icon);
  final String label;
  final IconData icon;
}

String _formatTime(DateTime value) {
  final h = value.hour.toString().padLeft(2, '0');
  final m = value.minute.toString().padLeft(2, '0');
  final s = value.second.toString().padLeft(2, '0');
  return '$h:$m:$s';
}
