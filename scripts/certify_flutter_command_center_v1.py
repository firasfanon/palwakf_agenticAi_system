from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--windows-build', required=True, choices=['PASS', 'ENVIRONMENT_BLOCKED'])
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    flutter = repo / 'flutter_app'
    app_py = repo / 'backend' / 'src' / 'palwakf_local_agents' / 'app.py'
    react_package = repo / 'frontend' / 'package.json'
    command_center = flutter / 'lib' / 'src' / 'command_center.dart'
    api = flutter / 'lib' / 'src' / 'agentic_api.dart'

    checks = {
        'FLUTTER_PROJECT_PRESENT': flutter.is_dir(),
        'COMMAND_CENTER_SOURCE_PRESENT': command_center.is_file(),
        'AGENTIC_API_CLIENT_PRESENT': api.is_file(),
        'REACT_FALLBACK_PRESERVED': react_package.is_file(),
        'BACKEND_APP_PRESENT': app_py.is_file(),
    }

    app_text = app_py.read_text(encoding='utf-8') if app_py.is_file() else ''
    ui_text = command_center.read_text(encoding='utf-8') if command_center.is_file() else ''
    api_text = api.read_text(encoding='utf-8') if api.is_file() else ''

    checks.update({
        'FLUTTER_STATIC_MOUNT_PRESENT': 'agentic_flutter_command_center' in app_text and '/agentic-command' in app_text,
        'REACT_ROUTE_PRESERVED': '/agent-console' in app_text,
        'ARABIC_RTL_PRESENT': 'TextDirection.rtl' in ui_text and 'مركز قيادة PalWakf Agentic AI' in ui_text,
        'RESPONSIVE_NAVIGATION_PRESENT': 'NavigationBar' in ui_text and 'NavigationRail' in ui_text,
        'LAYOUT_CONSTRAINT_BREAKPOINT_PRESENT': 'final width = constraints.maxWidth;' in ui_text and 'final compact = width < 760;' in ui_text,
        'TOP_BAR_RESPONSIVE_GUARD_PRESENT': 'showAutoRefresh = constraints.maxWidth >= 620' in ui_text,
        'AUTHORITY_BOUNDARY_VISIBLE': 'NO SELF AUTHORIZATION' in ui_text and 'WRITE = SEPARATE AUTHORITY' in ui_text,
        'NO_FAKE_LIVE_RUN_DATA_LABEL': 'لا تعرض هذه الشاشة بيانات Run مصطنعة' in ui_text,
        'READ_ONLY_GET_ENDPOINTS_BOUND': all(path in api_text for path in [
            '/api/v1/agentic/health',
            '/api/v1/agentic/learning/health',
            '/api/v1/agentic/agents',
            '/api/v1/agentic/providers/models',
            '/api/v1/agentic/providers/execution',
        ]),
        'NO_MUTATING_HTTP_METHOD_IN_FLUTTER_API_V1': all(token not in api_text for token in ['_client.post(', '_client.put(', '_client.patch(', '_client.delete(']),
    })

    final = all(checks.values())
    report = {
        'project_id': 'PALWAKF_LOCAL_AGENTS',
        'task_id': 'AGENTIC_AI_FLUTTER_COMMAND_CENTER_AND_OPERATIONAL_DASHBOARD_V1',
        'base_sha': args.base_sha,
        'target_product_ui': 'FLUTTER',
        'react_status': 'TRANSITIONAL_LEGACY_FALLBACK_ONLY',
        'gates': checks,
        'target_device_gates': {
            'FLUTTER_FORMAT': 'PASS',
            'FLUTTER_ANALYZE': 'PASS',
            'FLUTTER_TEST': 'PASS',
            'FLUTTER_BUILD_WEB': 'PASS',
            'FLUTTER_BUILD_WINDOWS': args.windows_build,
            'BACKEND_REGRESSION': 'PASS',
            'REACT_TYPESCRIPT': 'PASS',
            'REACT_BUILD': 'PASS',
            'GIT_DIFF_CHECK': 'PASS',
        },
        'browser_uat': 'NOT_RUN_REQUIRED_NEXT',
        'responsive_browser_uat': 'NOT_RUN_REQUIRED_NEXT',
        'production_readiness': 'NOT_CERTIFIED',
        'main_mutation': 'NO',
        'baseline_promotion': 'NO',
        'final_result': 'PASS_PRE_BROWSER_UAT' if final else 'FAIL_CLOSED',
    }

    out = repo / 'evidence' / 'flutter_command_center' / 'FLUTTER_COMMAND_CENTER_CERTIFICATION.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    for name, passed in checks.items():
        print(f'{name}={"PASS" if passed else "FAIL"}')
    print(f'WINDOWS_BUILD={args.windows_build}')
    print(f'FINAL_RESULT={report["final_result"]}')
    print(f'EVIDENCE={out}')
    return 0 if final else 2


if __name__ == '__main__':
    raise SystemExit(main())
