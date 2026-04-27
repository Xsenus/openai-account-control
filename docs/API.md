# API Контур

Ниже краткое описание backend API в текущем состоянии.

## 1. Публичные маршруты без логина

### `GET /api/health`

Возвращает:

- статус backend;
- имя приложения;
- текущий UTC timestamp.

### `GET /api/auth/session`

Возвращает:

- включена ли авторизация панели;
- аутентифицирован ли текущий браузер;
- `user_id`, `username`, `issued_at`, `expires_at`, если сессия есть.

### `POST /api/auth/login`

Логин в панель.

Пример:

```json
{
  "username": "admin",
  "password": "ChangeMe123!"
}
```

### `POST /api/auth/logout`

Удаляет текущую cookie-сессию.

## 2. Защищенные маршруты

Все остальные `/api/*` и `/evidence/*` требуют валидной panel-сессии.

Если нет логина, backend возвращает `401 Authentication required`.

## 3. Dashboard

### `GET /api/dashboard/summary`

Возвращает:

- `counters`;
- `latest_snapshots`;
- `latest_runs`.

## 4. Accounts

### `GET /api/accounts`

Список учеток.

### `POST /api/accounts`

Создание новой учетки.

Пример:

```json
{
  "label": "Sales team owner",
  "email_hint": "owner@example.com",
  "notes": "Основная рабочая учетка",
  "is_enabled": true
}
```

### `GET /api/accounts/{id}`

Одна учетка.

### `PUT /api/accounts/{id}`

Обновление учетки.

### `DELETE /api/accounts/{id}`

Удаление учетки, ее snapshots и scan history.

## 5. Session-state onboarding

### `POST /api/accounts/{id}/auth/import`

Импорт `storage_state`.

Ожидается именно Playwright `storage_state` с верхними полями `cookies` и `origins`.
JSON с `accessToken`, `sessionToken`, `user`, `account` и похожими полями backend теперь отклоняет с `400`.

Пример:

```json
{
  "storage_state": {
    "cookies": [],
    "origins": []
  }
}
```

### `POST /api/accounts/{id}/auth/browser-login`

Запуск локального интерактивного Playwright login job.

Пример:

```json
{
  "timeout_seconds": 900,
  "headless": false
}
```

### `GET /api/accounts/{id}/auth/browser-login/{job_id}`

Текущий статус auth job.

## 6. Snapshots и scan jobs

### `GET /api/accounts/{id}/snapshots`

История snapshots по одной учетке.

### `POST /api/accounts/{id}/scan`

Ручной scan выбранной учетки.

### `POST /api/scans/run-all`

Полный inventory scan всех включенных учеток.

### `GET /api/scans`

Список последних scan runs.

### `GET /api/scans/{run_id}`

Один scan run.

## 7. Runtime settings

### `GET /api/settings`

Текущие runtime settings.

### `PUT /api/settings`

Обновление runtime settings.

Пример:

```json
{
  "scan_interval_minutes": 180,
  "low_credits_threshold": 15,
  "low_usage_percent_threshold": 20
}
```

## 8. Access management

### `GET /api/settings/access/users`

Список операторов панели.

### `POST /api/settings/access/users`

Создание нового оператора.

Пример:

```json
{
  "username": "ops-team",
  "password": "StrongPassword123!",
  "is_active": true
}
```

### `PUT /api/settings/access/users/{user_id}`

Включение или отключение оператора.

Пример:

```json
{
  "is_active": false
}
```

Если это последний активный оператор, backend вернет `400`.

### `POST /api/settings/access/change-password`

Смена пароля текущего авторизованного оператора.

Пример:

```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword123!"
}
```

## 9. Примечания

- API рассчитан на локальное или private-сетевое использование.
- Ошибки валидации возвращаются стандартным форматом FastAPI.
- Долгие операции организованы как background jobs.
