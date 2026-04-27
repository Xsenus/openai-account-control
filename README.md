# OpenAI Account Control Center

Self-hosted панель для контроля нескольких OpenAI / ChatGPT-аккаунтов и связанных workspace-ов.

Что умеет:
- хранит реестр учеток OpenAI;
- сохраняет зашифрованный Playwright `storage_state`;
- запускает ручные и фоновые scan jobs;
- показывает dashboard по workspace-статусам;
- ведет историю проверок;
- защищает панель операторским логином и паролем.

## Быстрый старт

### Windows PowerShell

Подготовка окружения:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -IncludeFrontend
```

Запуск встроенного backend UI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

Открывайте:

- `http://localhost:8000`
- `http://127.0.0.1:8000`

Если нужен отдельный frontend dev server:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Открывайте:

- `http://localhost:5173`
- `http://127.0.0.1:5173`

Если хотите поднять backend и frontend сразу:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```

## Первый вход

По умолчанию проект использует bootstrap-доступ из [`.env`](.env):

- `ADMIN_USERNAME=admin`
- `ADMIN_PASSWORD=ChangeMe123!`

Важно:
- эти значения нужны для первого входа и аварийного восстановления доступа;
- после запуска можно создавать обычных операторов прямо в интерфейсе;
- если в базе уже есть активные операторы, панель использует их, а не старую схему "логин всегда только из .env";
- если все операторы отключены, backend на старте восстановит bootstrap-пользователя из `.env`.

Управление операторами находится в `Настройки -> Операторы панели`.

## Что лежит в `.env`

Ключевые параметры:

- `ENCRYPTION_KEY` — шифрует сохраненный `storage_state`;
- `AUTH_ENABLED=true` — включает login для панели;
- `ADMIN_USERNAME` и `ADMIN_PASSWORD` — bootstrap-доступ;
- `SESSION_COOKIE_NAME` и `SESSION_TTL_HOURS` — параметры cookie-сессии;
- `PLAYWRIGHT_LOCAL_AUTH_PROFILE_DIR` — каталог persistent browser-profile для локального входа;
- `PLAYWRIGHT_LOCAL_BROWSER_EXECUTABLE` — явный путь к локальному Chrome/Edge, если нужен фиксированный браузер;
- `PLAYWRIGHT_LOCALE` и `PLAYWRIGHT_TIMEZONE_ID` — locale/timezone локального browser-profile;
- `APP_HOST` и `APP_PORT` — адрес и порт backend.

## Как обновить проект

Если код проекта обновился:

1. Остановите старые процессы backend/frontend.
2. Обновите файлы проекта.
3. Выполните:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -IncludeFrontend
```

4. Перезапустите backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

5. Проверьте стенд:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000 -Username admin -Password ChangeMe123!
```

Если вы уже сменили bootstrap-пароль в `.env`, используйте новые значения. Если вход теперь идет через другого активного оператора из базы, проверяйте через его логин.

## GitHub и VPS

Для production-публикации подготовлены:

- `.env.production.example` — шаблон production-настроек без секретов;
- `deploy/openai-account-control.service` — systemd unit для запуска панели;
- `.github/workflows/deploy-vps.yml` — автоматический деплой на VPS по push в `main`;
- `scripts/deploy-vps-native.sh` — повторяемый запуск/обновление сервиса на сервере.

Подробная инструкция: [GitHub и VPS deployment](docs/DEPLOYMENT.md).

## Как добавить учетку OpenAI

Откройте страницу `Учетки`.

Рекомендуемый поток:

1. Нажмите `Добавить учетку`.
2. Заполните карточку в модальном окне.
3. Сохраните сессию одним из способов:
   - `Локальный вход` — backend откроет обычный локальный Chrome/Edge с отдельным profile-dir и подключится к нему по CDP;
   - `Импорт JSON` — загрузка готового `storage_state`.
4. Запустите `Проверить`.
5. Убедитесь, что snapshots появились на карточке выбранной учетки и на dashboard.

Важно:
- `Локальный вход` подходит только когда backend запущен на том же ПК, где оператор видит окно локального браузера.
- При локальном входе используется отдельный профиль `data/playwright-local-auth/<account-id>`, поэтому Cloudflare и browser trust сохраняются между попытками.
- Панель больше не перезагружает вкладку во время ожидания входа: Cloudflare-проверка должна завершаться в том же окне без циклических `goto()`.
- Для VPS или headless-сервера используйте helper-скрипт локально на своем компьютере.
- Панель принимает только Playwright `storage_state` с верхними полями `cookies` и `origins`.
- JSON с `accessToken`, `sessionToken`, `user`, `account` и похожими полями не подходит.

## Helper-скрипты для `storage_state`

Если панель защищена логином, helper-скриптам тоже надо передать доступ к панели.

### Захват новой сессии

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\capture-storage-state.ps1 `
  -AccountId <ACCOUNT_ID> `
  -BackendUrl http://127.0.0.1:8000 `
  -PanelUsername admin `
  -PanelPassword ChangeMe123! `
  -OutputPath .\storage_state.json
```

То же самое можно запустить напрямую через Python:

```powershell
.\.venv\Scripts\python.exe backend\scripts\capture_session.py `
  --backend-url http://127.0.0.1:8000 `
  --account-id <ACCOUNT_ID> `
  --panel-username admin `
  --panel-password ChangeMe123!
```

### Импорт готового JSON

```powershell
.\.venv\Scripts\python.exe backend\scripts\import_state.py `
  --backend-url http://127.0.0.1:8000 `
  --account-id <ACCOUNT_ID> `
  --file .\storage_state.json `
  --panel-username admin `
  --panel-password ChangeMe123!
```

Минимальный валидный формат файла:

```json
{
  "cookies": [],
  "origins": []
}
```

## Что проверять после запуска

- `http://localhost:8000/api/health` отвечает `ok`;
- страница входа открывается;
- логин проходит;
- dashboard загружается после входа;
- список учеток открывается;
- ручной `scan` запускается;
- при необходимости `smoke-test.ps1` проходит без ошибок.

## Документация

- [Короткий чеклист обновления](docs/UPDATE_CHECKLIST.md)
- [Эксплуатация и onboarding](docs/OPERATIONS.md)
- [Руководство разработчика](docs/DEVELOPMENT_GUIDE.md)
- [Описание API](docs/API.md)
- [Меры безопасности](docs/SECURITY.md)
- [GitHub и VPS deployment](docs/DEPLOYMENT.md)
