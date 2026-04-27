# Модульная карта проекта

Ниже перечислены все основные модули проекта, их ответственность и то, зачем каждый из них нужен.

## 1. Backend

## 1.1 `backend/app/main.py`
Назначение:
- создает экземпляр FastAPI;
- поднимает БД;
- поднимает scheduler;
- регистрирует роуты;
- монтирует evidence и frontend static.

Почему модуль выделен отдельно:
- это единственная точка сборки backend-приложения.

## 1.2 `backend/app/config.py`
Назначение:
- загрузка всех env-переменных;
- типизация конфигурации;
- единый источник настроек.

Ключевые поля:
- `DATABASE_URL`
- `ENCRYPTION_KEY`
- `SCAN_INTERVAL_MINUTES`
- `LOW_CREDITS_THRESHOLD`
- `LOW_USAGE_PERCENT_THRESHOLD`
- `PLAYWRIGHT_HEADLESS`
- `CHATGPT_BASE_URL`

## 1.3 `backend/app/db.py`
Назначение:
- engine;
- session factory;
- declarative base;
- инициализация таблиц.

## 1.4 `backend/app/models.py`
Назначение:
- описание SQLAlchemy-моделей.

Модели:
- `Account`
- `WorkspaceSnapshot`
- `ScanRun`
- `AppSetting`

## 1.5 `backend/app/schemas.py`
Назначение:
- DTO для API;
- валидация входящих/исходящих JSON.

## 1.6 `backend/app/enums.py`
Назначение:
- централизованный набор enum-значений;
- защита от "магических строк";
- единообразие backend и frontend модели.

## 1.7 `backend/app/selectors/phrases.py`
Назначение:
- собрать в одном месте все ключевые фразы UI ChatGPT;
- облегчить адаптацию при изменениях интерфейса.

Примеры:
- `Settings`
- `Billing`
- `Usage`
- `Workspaces`
- `Owner`, `Admin`, `Member`
- `deactivated`, `locked`

## 1.8 `backend/app/selectors/parser_patterns.py`
Назначение:
- regex для числовых значений;
- извлечение credits balance, spend limit, percent remaining.

## 1.9 `backend/app/services/encryption_service.py`
Назначение:
- шифровать и расшифровывать session-state.

Почему это отдельный сервис:
- безопасность должна быть изолирована от CRUD и scan-логики.

## 1.10 `backend/app/services/account_service.py`
Назначение:
- CRUD по учеткам;
- импорт session-state;
- дешифровка session-state по месту использования.

## 1.11 `backend/app/services/auth_job_service.py`
Назначение:
- запускать локальный браузерный onboarding;
- хранить состояние auth job в памяти.

Почему in-memory:
- для self-hosted single-instance MVP этого достаточно.

## 1.12 `backend/app/services/playwright_session_service.py`
Назначение:
- открывать Chromium с сохраненным session-state;
- делать интерактивный захват session-state;
- проверять, что пользователь действительно вошел.

## 1.13 `backend/app/services/parser_service.py`
Назначение:
- превращать сырые тексты из страниц в числовые и логические сигналы.

Что умеет:
- план;
- seat type;
- unit;
- credits balance;
- spend limit;
- auto top-up;
- included line;
- percent remaining.

## 1.14 `backend/app/services/openai_probe_service.py`
Назначение:
- это ядро интеграции с ChatGPT UI;
- обнаруживает workspaces;
- читает Settings/Billing/Usage;
- сохраняет screenshot и excerpts;
- отдает сырые `ProbeWorkspaceResult`.

Почему этот модуль ключевой:
- именно он делает из сохраненной сессии полезные операционные данные.

## 1.15 `backend/app/services/status_service.py`
Назначение:
- присвоить workspace итоговый операционный статус.

Вход:
- `ProbeWorkspaceResult`
- runtime settings

Выход:
- `OK`, `LOW`, `BLOCKED`, `PARTIAL`, `DEACTIVATED`, `UNKNOWN`

## 1.16 `backend/app/services/scan_service.py`
Назначение:
- orchestration scan jobs;
- очередь в фоне;
- запуск одной или всех учеток;
- сохранение результатов;
- фиксация metrics.

## 1.17 `backend/app/services/settings_service.py`
Назначение:
- чтение и обновление runtime settings в БД.

## 1.18 `backend/app/services/evidence_service.py`
Назначение:
- создавать каталоги evidence;
- сохранять text/json files;
- помогать анализировать изменения UI.

## 1.19 `backend/app/services/scheduler_service.py`
Назначение:
- запускать периодический inventory scan;
- подстраивать интервал под runtime settings.

## 1.20 `backend/app/api/routes/*.py`
Назначение:
- каждая группа endpoint-ов вынесена в свой файл:
  - `accounts.py`
  - `dashboard.py`
  - `scans.py`
  - `settings.py`
  - `system.py`

Причина:
- API-слой должен быть тонким и отделенным от domain logic.

## 1.21 `backend/tests/*.py`
Назначение:
- минимальный unit-test контур.

## 1.22 `backend/scripts/capture_session.py`
Назначение:
- удобный helper для захвата session-state на машине оператора.

## 1.23 `backend/scripts/import_state.py`
Назначение:
- загрузка уже готового JSON session-state в backend.

## 1.24 `backend/scripts/dev_seed.py`
Назначение:
- загрузка демо-данных.

---

## 2. Frontend

## 2.1 `frontend/src/App.tsx`
Назначение:
- определение маршрутов приложения.

## 2.2 `frontend/src/components/Layout.tsx`
Назначение:
- единый shell приложения: sidebar + main content.

## 2.3 `frontend/src/components/StatusBadge.tsx`
Назначение:
- единый способ визуально отрисовать статус.

## 2.4 `frontend/src/components/SummaryCards.tsx`
Назначение:
- summary cards на главной странице.

## 2.5 `frontend/src/components/SnapshotTable.tsx`
Назначение:
- таблица snapshots;
- переиспользуется и на dashboard, и на странице учеток.

## 2.6 `frontend/src/components/AccountForm.tsx`
Назначение:
- форма добавления новой учетки.

## 2.7 `frontend/src/pages/DashboardPage.tsx`
Назначение:
- сводка системы;
- запуск full scan;
- последние snapshots и runs.

## 2.8 `frontend/src/pages/AccountsPage.tsx`
Назначение:
- реестр учеток;
- onboarding;
- импорт session-state;
- локальный login;
- ручной scan;
- история snapshots по учетке.

## 2.9 `frontend/src/pages/HistoryPage.tsx`
Назначение:
- просмотр run history и ошибок.

## 2.10 `frontend/src/pages/SettingsPage.tsx`
Назначение:
- изменение thresholds и scheduler interval.

## 2.11 `frontend/src/api/client.ts`
Назначение:
- единая обертка над fetch;
- типизированный вызов endpoint-ов.

## 2.12 `frontend/src/types.ts`
Назначение:
- общие типы frontend-модели.

## 2.13 `frontend/src/styles.css`
Назначение:
- оформление приложения.

---

## 3. Служебные файлы

## 3.1 `.env.example`
Назначение:
- шаблон переменных окружения.

## 3.2 `Makefile`
Назначение:
- стандартные команды для запуска и разработки.

---

## 4. Почему такая модульность важна

Эта архитектура дает четыре критических преимущества:

1. код легко поддерживать;
2. probe можно обновлять независимо от UI и DB;
3. документация совпадает со структурой репозитория;
4. можно безопасно дорабатывать проект дальше без полной переписки.
