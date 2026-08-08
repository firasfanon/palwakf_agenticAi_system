# Changelog — 2026-07-04

## Added

- `legacy_write_authorization.py`: Boundary مشترك للفاعل/Workspace/Action/Actor declaration/Commercial Client context.
- Negative UAT موجه بـ25 حالة مع snapshot-based non-mutation proof.
- أدوات Windows Apply/Static Gate/Negative UAT/Rollback محكومة بـhash manifest.

## Changed

- `POST /api/tasks` أصبح disabled route 410.
- `governed_operations` و`local_agent_core` أصبحا يتطلبان authenticated actor للكتابة.
- `governed_capability_foundation` يمر عبر Boundary موحد.
- `package-lock.json` في source package يعكس Registry عام سبق قبوله في V7، وتضمين Runner HAR reconciliation المقبول مسبقًا.

## Not changed

- React write state.
- UI write actions.
- Model/Pilot execution.
- Config actor registry أو provisioning.
- Workspaces/audit/evidence data.
