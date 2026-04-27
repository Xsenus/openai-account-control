# API Reference

## Health

### `GET /api/health`
Проверка доступности backend.

**Ответ:**
```json
{
  "status": "ok"
}
```

## Accounts

### `GET /api/accounts`
Возвращает список аккаунтов.

### `POST /api/accounts`
Создает аккаунт.

**Пример body:**
```json
{
  "label": "Personal Plus",
  "email_hint": "me@gmail.com",
  "notes": "Мой личный аккаунт",
  "is_enabled": true
}
```

### `GET /api/accounts/{account_id}`
Возвращает один аккаунт.

### `PUT /api/accounts/{account_id}`
Обновляет аккаунт.

### `DELETE /api/accounts/{account_id}`
Удаляет аккаунт.

### `POST /api/accounts/{account_id}/login/start`
Создает фоновую задачу login flow.

**Ответ:**
```json
{
  "id": "job-id",
  "account_id": "account-id",
  "kind": "login",
  "status": "pending",
  "message": "Создана задача авторизации",
  "payload_json": null,
  "started_at": null,
  "finished_at": null,
  "created_at": "2026-04-08T10:00:00"
}
```

### `POST /api/accounts/{account_id}/scan/start`
Создает фоновую задачу scan.

### `GET /api/accounts/{account_id}/snapshots`
Возвращает latest snapshots по выбранному аккаунту.

## Jobs

### `GET /api/jobs`
Список последних фоновых задач.

### `GET /api/jobs/{job_id}`
Возвращает одну задачу.

## Dashboard

### `GET /api/dashboard/summary`
Возвращает summary по всем аккаунтам.

### `POST /api/dashboard/scan-all`
Создает scan jobs для всех включенных аккаунтов.

## Settings

### `GET /api/settings`
Возвращает runtime settings.

### `PUT /api/settings`
Обновляет runtime settings.

**Пример body:**
```json
{
  "auto_scan_enabled": true,
  "default_scan_interval_minutes": 60,
  "low_credits_threshold": 10,
  "webhook_enabled": false,
  "webhook_url": null
}
```
