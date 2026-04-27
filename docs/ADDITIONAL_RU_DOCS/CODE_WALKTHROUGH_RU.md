# Подробный разбор кода по модулям и функциям

Этот документ нужен для двух задач:

1. Быстро понять, где находится нужная логика.
2. Понять, зачем существует каждый модуль и каждая ключевая функция.

## 1. `backend/app/core/config.py`

### `Settings`
Главный конфигурационный класс. Он читает `.env`, приводит значения к нужным типам и хранит их в одном объекте.

### `cors_origins`
Свойство превращает CSV-строку `CORS_ORIGINS` в список строк для FastAPI CORS middleware.

### `ensure_directories()`
Создает каталоги `data/`, `evidence/`, `playwright_state/`, чтобы приложение не падало при первом старте.

### `get_settings()`
Возвращает singleton настроек и гарантирует подготовку каталогов.

## 2. `backend/app/core/security.py`

### `_get_fernet()`
Строит объект Fernet на основе ключа из конфигурации.

### `encrypt_text()`
Шифрует `storage_state` перед записью в БД.

### `decrypt_text()`
Расшифровывает `storage_state` перед scan job.

## 3. `backend/app/db/models.py`

### `Account`
Описание мониторимого логина.

### `BackgroundJob`
Фоновая задача login/scan.

### `WorkspaceSnapshot`
Снимок одного workspace с нормализованными полями.

### `AppSetting`
Таблица key-value настроек.

## 4. `backend/app/collectors/parser_helpers.py`

### `normalize_text(value)`
Приводит текст к lowercase и схлопывает пробелы. Это базовый preprocessing для всех парсеров.

### `_contains_any(text, values)`
Утилита проверки наличия хотя бы одного keyword.

### `infer_personal_plan(text)`
Пытается определить plan personal workspace.

### `infer_workspace_state(text, disabled_flag=False)`
Главный классификатор состояний workspace.

### `infer_workspace_kind(workspace_name, text)`
Определяет personal/business/unknown.

### `infer_role(text)`
Извлекает роль пользователя.

### `infer_seat_type(text)`
Определяет Codex seat или standard ChatGPT seat.

### `infer_limit_unit(text)`
Определяет messages/tokens/credits.

### `infer_auto_topup(text)`
Возвращает True/False/None для auto top-up.

### `extract_included_limit_text(text)`
Возвращает диагностический текстовый фрагмент про limit/usage.

### `extract_credit_balance(text)`
Ищет денежное значение `$xx.xx`.

### `compute_account_bucket(workspace_state, credits_balance, low_threshold)`
Сводит snapshot к bucket `ok/warning/critical`.

## 5. `backend/app/collectors/openai_collector.py`

### `WorkspaceCandidate`
Промежуточная структура, найденная в меню профиля.

### `OpenAICollector.collect(account_id, storage_state_json)`
Главная публичная функция collector-а. Делает всё: открывает браузер, проверяет логин, ищет workspaces, собирает payload и screenshots.

### `_is_logged_in(page)`
Проверяет, работает ли еще сессия.

### `_safe_page_text(page)`
Безопасно получает текст body.

### `_return_home(page)`
Возвращает браузер на главную страницу перед следующим действием.

### `_open_profile_menu(page)`
Пытается открыть меню профиля через набор candidate selectors.

### `_discover_workspaces(page)`
Собирает список workspaces из меню.

### `_switch_to_workspace(page, workspace_name)`
Переключает текущий workspace.

### `_click_first_text(page, texts)`
Кликает по первому элементу с одним из текстов.

### `_collect_workspace_payload(page, workspace)`
Считывает текст текущего workspace, пытается открыть settings/billing/usage и извлекает нормализованные поля.

### `_capture_screenshot(page, account_id, workspace_name)`
Сохраняет screenshot как evidence.

### `_build_auth_expired_snapshot()`
Возвращает служебный snapshot, если storage_state протух.

## 6. `backend/app/services/login_service.py`

### `run_login_job(job_id, account_id)`
Фоновая процедура входа. Создает running state, открывает браузер, сохраняет результат, пишет success/failed.

### `_perform_interactive_login()`
Открывает Playwright Chromium и ждет ручного входа пользователя.

### `_wait_until_logged_in(page)`
Цикл ожидания завершения login flow с длинным таймаутом.

### `_looks_logged_in(url, text)`
Эвристика, что пользователь уже вошел.

## 7. `backend/app/services/scan_service.py`

### `run_scan_job(job_id, account_id)`
Запускает полный цикл сканирования одного аккаунта.

### `_persist_snapshots(db, job_id, account, payloads)`
Сохраняет список payload-словарей в таблицу snapshots.

### `_update_account_status(db, account, snapshots, low_credits_threshold)`
Пересчитывает итоговый статус аккаунта после скана.

### `build_dashboard_summary(db)`
Готовит summary для главного UI.

### `_get_latest_snapshots_for_account(db, account_id)`
Возвращает snapshots из последнего scan job.

### `list_latest_snapshots(db, account_id)`
Публичная обертка для router layer.

## 8. `backend/app/services/settings_service.py`

### `_get_value(db, key, default)`
Возвращает либо значение из БД, либо дефолт из env.

### `read(db)`
Читает полный снимок runtime settings.

### `update(db, payload)`
Сохраняет частичные изменения настроек.

## 9. `backend/app/services/scheduler_service.py`

### `start()`
Поднимает APScheduler и регистрирует periodic auto-scan.

### `shutdown()`
Останавливает scheduler.

### `_trigger_auto_scans()`
Создает scan jobs для всех включенных аккаунтов.

## 10. `backend/app/routers/accounts.py`

### `list_accounts()`
Отдает все аккаунты.

### `create_account()`
Создает новый аккаунт.

### `get_account()`
Отдает один аккаунт.

### `update_account()`
Обновляет аккаунт.

### `delete_account()`
Удаляет аккаунт.

### `start_login()`
Создает login job и запускает background task.

### `start_scan()`
Создает scan job и запускает background task.

### `latest_snapshots()`
Возвращает последние snapshots выбранного аккаунта.

## 11. `frontend/src/App.tsx`

### `loadInitialData()`
Единая первичная загрузка accounts/summary/jobs/settings.

### `loadSnapshots(accountId)`
Подтягивает latest snapshots текущего аккаунта.

### `handleCreateAccount(payload)`
Вызывает backend на создание аккаунта.

### `handleUpdateAccount(payload)`
Вызывает backend на обновление аккаунта.

### `handleDeleteAccount(accountId)`
Удаляет аккаунт.

### `handleStartLogin(accountId)`
Запускает login flow.

### `handleStartScan(accountId)`
Запускает scan job.

### `handleScanAll()`
Запускает массовое сканирование.

### `handleSaveSettings(payload)`
Сохраняет runtime settings.

## 12. `frontend/src/components/AccountForm.tsx`

### `handleSubmit(event)`
Собирает форму и передает payload родителю.

## 13. `frontend/src/components/WorkspaceTable.tsx`

Компонент отрисовывает снимки в виде плотной таблицы, где видны:
- workspace name;
- type;
- state;
- plan/seat;
- limit text;
- credits;
- auto top-up;
- confidence.

## 14. `frontend/src/pages/DashboardPage.tsx`

Вычисляет aggregate counts и показывает summary-таблицу по всем аккаунтам.

## 15. `frontend/src/pages/AccountsPage.tsx`

Компонент-сцена, объединяющий:
- список аккаунтов;
- карточку выбранного аккаунта;
- кнопки login/scan/delete;
- edit form;
- table snapshots.

## 16. `frontend/src/pages/SettingsPage.tsx`

Отвечает за редактирование runtime settings.
