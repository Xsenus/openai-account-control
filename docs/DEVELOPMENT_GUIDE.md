# Руководство Разработчика

## 1. Требования к окружению

- Python 3.11+
- Node.js 22+
- npm 10+
- Chromium для Playwright

## 2. Подготовка проекта

### Рекомендуемый путь для Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -IncludeFrontend
```

Что делает скрипт:

- создает `.venv`, если его нет;
- обновляет `pip`;
- ставит зависимости backend;
- ставит зависимости frontend, если указан `-IncludeFrontend`;
- генерирует `ENCRYPTION_KEY` в `.env`, если там `CHANGE_ME`;
- устанавливает Chromium для Playwright, если не указан `-SkipPlaywright`.

## 3. Локальный запуск для разработки

### Только backend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

### Только frontend dev server

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

### Оба процесса

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```

`start-frontend.ps1` передает backend URL в `VITE_BACKEND_URL`, поэтому Vite проксирует `/api` и `/evidence` без ручной правки `API_BASE`.

## 4. Модель авторизации панели

### Bootstrap-уровень

Переменные `.env`:

- `AUTH_ENABLED`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SESSION_COOKIE_NAME`
- `SESSION_TTL_HOURS`

Они нужны не как постоянное хранилище всех операторов, а как bootstrap и recovery-механизм.

### Основной уровень

Операторы панели живут в таблице `panel_users`.

Реализация:

- модель: `backend/app/models.py`
- хэширование: `backend/app/services/password_service.py`
- CRUD операторов: `backend/app/services/panel_user_service.py`
- сессии панели: `backend/app/services/admin_auth_service.py`

Логика такая:

1. Backend на старте проверяет, есть ли активные операторы.
2. Если активных операторов нет, он создает или восстанавливает bootstrap-пользователя из `.env`.
3. После этого логин выполняется уже по пользователям из базы.

## 5. Где развивать код

### Backend

- routes: тонкий слой HTTP и DTO;
- services: бизнес-логика;
- models: SQLAlchemy-модели;
- schemas: Pydantic DTO.

### Frontend

- `pages/` — страницы и рабочие потоки;
- `components/` — повторно используемые UI-блоки;
- `api/client.ts` — вызовы backend API;
- `types.ts` — frontend DTO.

## 6. Как обновлять схему данных

Сейчас проект использует `create_all`, без Alembic.

Практическое правило:

1. Добавляете модель или колонку.
2. Обновляете `backend/app/models.py`.
3. Убеждаетесь, что `init_db()` импортирует новую модель.
4. Проверяете сценарий на новой или тестовой SQLite базе.

Для production-эволюции схемы стоит позже добавить Alembic.

## 7. Тесты

Запуск backend-тестов:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

Что сейчас проверяется:

- шифрование;
- статус-логика;
- auth routes;
- управление операторами и смена пароля.

## 8. Сборка frontend

```powershell
cd frontend
npm run build
```

После сборки `dist/` можно синхронизировать во встроенный backend UI.

## 9. Smoke-проверка после изменений

### Backend health + dashboard

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000 -Username admin -Password ChangeMe123!
```

### Ручной сценарий auth

Минимум проверьте:

1. Страница входа открывается.
2. Логин проходит.
3. Dashboard загружается.
4. `Настройки -> Операторы панели` показывает текущего пользователя.
5. Создание нового оператора и смена пароля работают.

## 10. Helper-скрипты и auth

Если панель защищена логином, helper-скрипты должны знать операторские креды.

Пример:

```powershell
.\.venv\Scripts\python.exe backend\scripts\capture_session.py `
  --backend-url http://127.0.0.1:8000 `
  --account-id <ACCOUNT_ID> `
  --panel-username admin `
  --panel-password ChangeMe123!
```

## 11. Что стоит сделать дальше

- добавить Alembic;
- ввести роли `owner/operator`;
- добавить аудит действий операторов;
- вынести job registry в Redis при росте нагрузки;
- добавить frontend E2E smoke tests.
