# Руководство по разработке и запуску

## 1. Требования к окружению

### Backend
- Python 3.11+
- pip
- Playwright
- Chromium browser через `playwright install chromium`

### Frontend
- Node.js 20+
- npm

## 2. Локальный запуск backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp ../.env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Windows PowerShell

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item ..\.env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 3. Локальный запуск frontend

```bash
cd frontend
npm install --prefer-offline --no-audit --no-fund
npm run dev
```

## 4. Первый запуск системы

1. Поднимите backend.
2. Поднимите frontend.
3. Перейдите на `http://localhost:5173`.
4. Создайте первый аккаунт во вкладке **Accounts**.
5. Нажмите **Начать вход**.
6. В открывшемся браузере Playwright выполните вход в ChatGPT.
7. После успешной авторизации нажмите **Сканировать сейчас**.

## 5. Как добавить ваши учетные записи

### Сценарий 1. Personal Plus/Pro

1. Создайте запись, например `Personal Plus`.
2. Укажите email hint.
3. Запустите login flow.
4. Войдите в личную учетную запись OpenAI.
5. После завершения входа запустите scan.
6. В таблице snapshots появится Personal workspace и найденные лимиты/кредиты.

### Сценарий 2. Личный аккаунт + Business workspace в том же логине

1. Создайте одну запись на логин, а не по одному workspace.
2. Выполните вход.
3. Scan сам попытается собрать все workspaces внутри одного логина.
4. В latest snapshots вы увидите отдельные строки:
   - Personal workspace;
   - Company A;
   - Company B и т. д.

### Сценарий 3. Разные логины OpenAI

1. Создайте несколько аккаунтов, по одному на каждый логин.
2. Для каждого выполните manual login.
3. После этого можно запускать `Сканировать все аккаунты` на Dashboard.

## 6. Как работает авторизация

Проект **не хранит пароль**. Логика такая:

1. Backend открывает браузер Chromium через Playwright.
2. Вы входите вручную.
3. После входа backend сохраняет только cookies/local storage/state в виде `storage_state`.
4. JSON состояния шифруется Fernet-ключом.
5. При каждом scan backend поднимает новый browser context с этим состоянием.

## 7. Что делать, если UI OpenAI изменился

### Наиболее вероятные места адаптации

- `backend/app/collectors/parser_rules.py`
- `backend/app/collectors/parser_helpers.py`
- `backend/app/collectors/openai_collector.py`

### Практический порядок действий

1. Запустить scan.
2. Открыть сохраненный screenshot из `data/evidence/<account_id>/`.
3. Посмотреть `raw_payload_json` в snapshot.
4. Добавить/исправить keywords в `parser_rules.py`.
5. Если проблема в навигации, расширить список selectors и text steps в `openai_collector.py`.

## 8. Как читать результаты

### Workspace state
- `active` — все хорошо;
- `deactivated` — workspace выключен или заблокирован;
- `auth_expired` — нужно снова пройти login flow;
- `partial_visibility` — роль в workspace ограничивает просмотр billing/credits;
- `merged` — personal workspace был слит в business;
- `unknown` — collector не нашел достаточно признаков.

### Credits balance
Если поле пустое, это может означать:
- credits отсутствуют;
- баланс не виден вашей роли;
- parser не смог однозначно извлечь сумму.

### Included limit text
Это диагностическое поле. В нем хранится текст фрагмента, похожего на описание лимита. Его не нужно трактовать как строгое число.

## 9. Как безопасно хранить данные

### Обязательно
- заменить `FERNET_KEY` в `.env`;
- не коммитить `data/` в git;
- не отдавать наружу папку `data/evidence/` без необходимости.

### Рекомендуется
- запускать backend только в доверенной сети;
- ограничить доступ к хосту/виртуалке;
- периодически делать re-login, если сессии протухают.

## 10. Unit-тесты

```bash
cd backend
pytest -q
```

## 11. Проверка кода на синтаксис

```bash
cd backend
python -m compileall app
```

## 12. Возможные улучшения после MVP

- Postgres и Alembic migration;
- Telegram-бот для уведомлений;
- CSV/Excel export;
- ручная калибровка selectors из интерфейса;
- Xvfb/noVNC login mode для удаленного сервера.
