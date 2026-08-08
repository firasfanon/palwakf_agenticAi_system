# Initial Operation Readiness & Blocked Capability Reassessment V1

الدفعة: `MEGA_BATCH_LOCAL_AGENTS_INITIAL_OPERATION_READINESS_AND_BLOCKED_CAPABILITY_REASSESSMENT_V1`

## الهدف

هذه الدفعة تنقل المشروع من تراكم صفحات التصميم والتحضير إلى **خطة تشغيل أولي قابلة للفحص**، مع إعادة تقييم القدرات التي كانت محجوبة سابقًا دون فتحها تلقائيًا.

## القرار الحاكم

التشغيل الأولي لا يعني تشغيل النموذج، ولا فتح Shell أو Git أو Code execution، ولا تمكين Self-Apply.

المطلوب الآن:

1. جرد ما أصبح مقبولًا.
2. تحديد ما يكفي لأول فحص تشغيلي.
3. تصنيف المحجوبات إلى: يبقى محجوبًا، Future Gate، Read-only، Prepare-only.
4. بناء خطة فحص أولي وقواعد إيقاف.

## ما أصبح جاهزًا الآن

- Operational UX.
- Goal Planner Productization.
- Task Draft Backend Prepare.
- Task Draft Review Flow.
- Project Reader GET-only.
- Project Charter.
- Project State Manager design.

## إعادة تقييم المحجوبات

| القدرة | القرار |
|---|---|
| Model execution | مؤجل إلى Local Model Runtime Readiness Gate |
| Pilot execution | مؤجل إلى Controlled Pilot Gate |
| Shell | يبقى محجوبًا |
| Git | يبقى محجوبًا |
| Code execution | يبقى محجوبًا |
| DB persistence | مؤجل إلى SQLite governed persistence |
| Web search | يبقى محجوبًا |
| Self-Apply | يبقى محجوبًا |
| Project Reader | مقبول Read-only |
| Task Draft Prepare | مقبول Prepare-only |

## خطة الفحص الأولي

1. فتح مركز العمل.
2. اختيار قالب هدف.
3. تحضير مسودات من الخطة.
4. مراجعة المسودة وقبولها كخطة.
5. قراءة بنية المشروع.
6. فتح صفحة جاهزية التشغيل الأولي.
7. التأكد سلبيًا من عدم وجود تنفيذ أو نموذج أو Git أو Shell.

## قواعد الإيقاف

- ظهور زر تنفيذ فعلي غير مصرح به.
- أي تشغيل Model/Pilot من الواجهة.
- أي Shell/Git/Code execution.
- أي حفظ دائم غير مصرح به.
- عودة ازدحام الحوكمة إلى الواجهة التشغيلية.
