# Эксплуатация и Onboarding

## 1. Базовый сценарий работы

Обычный операционный цикл выглядит так:

1. Запустить backend и при необходимости frontend dev server.
2. Войти в панель оператором.
3. Добавить или выбрать учетку OpenAI.
4. Сохранить для нее Playwright session-state.
5. Запустить ручной `scan`.
6. Проверить dashboard, историю и snapshots.
7. Оставить scheduler включенным для фонового мониторинга.

## 2. Как запускать систему

### Backend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

Открывайте:

- `http://localhost:8000`

### Frontend dev server

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Открывайте:

- `http://localhost:5173`

### Оба сервиса сразу

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```

## 3. Как войти в панель

Первый вход делается bootstrap-оператором из `.env`:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

После этого в `Настройки -> Операторы панели` можно:

- создать новых операторов;
- отключать и включать операторов;
- менять пароль текущего пользователя.

Важно:
- если в базе уже есть активные операторы, вход идет по ним;
- bootstrap-оператор из `.env` автоматически создается или восстанавливается только если активных операторов в базе не осталось.

## 4. Как добавить новую учетку OpenAI

### Шаг 1. Создать карточку

Откройте `Учетки` и нажмите `Добавить учетку`.

Заполните:

- название;
- email hint;
- заметки;
- флаг участия в scheduler.

### Шаг 2. Подключить session-state

Есть два рабочих сценария.

#### Вариант A. Локальный вход

Используйте, если backend запущен на той же машине, где доступно браузерное окно:

1. Выберите учетку.
2. Нажмите `Локальный вход`.
3. Войдите в ChatGPT в открывшемся локальном Chrome/Edge с отдельным browser-profile.
4. Если появился Cloudflare, дождитесь завершения проверки в том же окне.
5. Не закрывайте окно вручную: панель больше не перезагружает вкладку в цикле и дождется реального входа в этом же окне.
6. Дождитесь завершения auth job.

#### Вариант B. Импорт JSON

Используйте, если backend крутится на удаленной машине или без GUI:

1. Снимите `storage_state` локально helper-скриптом.
2. Передайте в helper логин панели через `--panel-username` и `--panel-password`, если auth включен.
3. Загрузите JSON через `Импорт JSON` или отправьте его helper-скриптом напрямую.

Панель принимает только Playwright `storage_state` с верхними полями `cookies` и `origins`.
JSON с `accessToken`, `sessionToken`, `user`, `account` и похожими полями не подходит.
Локальный browser-profile хранится в `data/playwright-local-auth/<account-id>`, поэтому Cloudflare/browser trust сохраняются между повторными попытками для одной учетки.
Панель подключается к обычному локальному Chrome/Edge по CDP, а не стартует одноразовый Playwright Chromium с automation-флагами.

Упрощенный PowerShell-вариант:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\capture-storage-state.ps1 `
  -AccountId <ACCOUNT_ID> `
  -BackendUrl http://127.0.0.1:8000 `
  -PanelUsername admin `
  -PanelPassword ChangeMe123! `
  -OutputPath .\storage_state.json
```

## 5. Как понять, что onboarding прошел успешно

Проверьте у выбранной учетки:

- есть метка, что session сохранена;
- заполнен `last_auth_at`;
- после ручного `scan` появились snapshots;
- dashboard не показывает `auth_expired` сразу после входа.

## 6. Как запускать проверки

### Проверка одной учетки

На странице `Учетки` выберите запись и нажмите `Проверить`.

### Проверка всех учеток

На dashboard нажмите `Сканировать все`.

### Фоновая проверка

Scheduler делает полный inventory scan с интервалом из `Настроек`.

## 7. Как читать статусы

### `OK`

Проблем не видно, данные доступны, лимиты выше порога.

### `LOW`

Доступ есть, но credits или included usage близки к порогу.

### `BLOCKED`

Сессия истекла, доступ закрыт, или ресурсы закончились без автоматического восстановления.

### `PARTIAL`

Данные видны не полностью, обычно из-за ролей, прав или ограничений UI.

### `DEACTIVATED`

Workspace существует, но деактивирован или больше нерабочий.

## 8. Что делать после обновления проекта

1. Остановите backend и frontend.
2. Обновите файлы проекта.
3. Выполните:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -IncludeFrontend
```

4. Перезапустите backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

5. Проверьте:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000 -Username admin -Password ChangeMe123!
```

Если у вас уже есть другие активные операторы, можно проверить и их логином.

## 9. Что делать, если потерян доступ к панели

1. Остановите backend.
2. Проверьте bootstrap-данные в `.env`:
   - `AUTH_ENABLED=true`
   - `ADMIN_USERNAME=...`
   - `ADMIN_PASSWORD=...`
3. Убедитесь, что в базе не осталось активных операторов, либо отключите их вручную из резервной копии/служебного доступа.
4. Запустите backend снова.
5. Backend восстановит bootstrap-пользователя из `.env`, если активных операторов нет.

## 10. Резервные копии

Минимум, что нужно бэкапить:

- каталог `data/`;
- файл `.env`.

Без `ENCRYPTION_KEY` из `.env` зашифрованный `storage_state` не получится использовать после восстановления.
