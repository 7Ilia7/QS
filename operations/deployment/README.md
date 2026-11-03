# QS Deployment: індекс передачі та runbook

## Чинна owner policy QS — 2 листопада 2026

Правки в окремій гілці → локальний перегляд власником → **явне схвалення
обраної версії** → релевантні QA/CI та merge/main → чинний full main build/AUTO
і серверний read-back. Цей порядок скасовує попередню широку merge/deploy authority.
Незалежний QA PASS потрібний у своєму scope, але не є visual owner approval.

Перед merge зберегти owner approval receipt/context із точним варіантом,
branch/commit або artifact digest та URL/path локального preview. Якщо показану
версію змінено, preview/approval має відповідати новим bytes. Не обирати варіант
замість власника; для тієї самої вже схваленої версії й scope не питати повторно.

Поточний owner scope — **три LOCAL visual options**, без push/PR/merge/deploy,
SSH/live checks або provider/settings/credential дій. Локальні commits дозволені.
Після майбутнього схвалення конкретної версії existing AUTO після main merge
лишається чинним: не вимикати workflow/readiness і не додавати environment reviewers
чи глобальний manual-approval gate. Межа поточної роботи — до merge, у локальних
інструкціях, не нова конфігурація провайдера.

Для кожного нового isolated preview worktree перенести актуальні `AGENTS.md`,
цей `operations/deployment/README.md` та `release-template.md` окремими локальними
змінами, не копіюючи dirty canonical product files і не роблячи `git add .`.
Shared `/Users/a1/.codex/skills/website-release/references/qs.md` не треба копіювати.
Історичні snapshots нижче та старі approvals не відновлюють скасовану authority.
