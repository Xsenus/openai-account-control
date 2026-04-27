# Короткий Чеклист Обновления

Этот файл нужен для быстрого обновления уже установленной панели без чтения всей документации.

## 1. Остановить старые процессы

Остановите:

- backend на `8000`;
- frontend dev server на `5173`, если он был запущен.

## 2. Обновить файлы проекта

Замените код проекта на новую версию.

Если используете git, выполните свой обычный `pull` или обновление рабочей копии.

## 3. Обновить зависимости и окружение

Из корня проекта:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -IncludeFrontend
```

Что это сделает:

- проверит `.venv`;
- обновит Python-зависимости;
- обновит frontend-зависимости;
- проверит `.env`;
- при необходимости сгенерирует `ENCRYPTION_KEY`, если он не был настроен.

## 4. Проверить `.env`

Минимум убедитесь, что в [`.env`](../.env) корректны:

- `AUTH_ENABLED`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ENCRYPTION_KEY`
- `APP_PORT`

Важно:

- `ADMIN_USERNAME` и `ADMIN_PASSWORD` теперь нужны как bootstrap/recovery-доступ;
- если в базе уже есть активные операторы, обычный вход идет через них;
- если все операторы отключены, backend на старте восстановит bootstrap-пользователя из `.env`.

## 5. Запустить backend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

Открывайте:

- `http://localhost:8000`

## 6. Если нужен dev frontend

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-frontend.ps1
```

Открывайте:

- `http://localhost:5173`

Или одним запуском:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```

## 7. Прогнать быструю проверку

### Вариант A. Через bootstrap-пользователя

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000 -Username admin -Password ChangeMe123!
```

Подставьте свои значения из `.env`, если они отличаются.

### Вариант B. Через рабочего оператора из базы

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1 -BaseUrl http://127.0.0.1:8000 -Username <OPERATOR_LOGIN> -Password <OPERATOR_PASSWORD>
```

## 8. Что должно работать после обновления

- `GET /api/health` отвечает `ok`;
- страница логина открывается;
- вход проходит;
- dashboard загружается;
- `Настройки -> Операторы панели` открывается;
- `Учетки` и `История` открываются без ошибок.

## 9. Если после обновления не пускает в систему

Проверьте по порядку:

1. backend точно перезапущен;
2. `.env` содержит актуальные `ADMIN_USERNAME` и `ADMIN_PASSWORD`;
3. `AUTH_ENABLED=true`;
4. в базе не остались только отключенные операторы;
5. старые cookie в браузере не мешают.

Если совсем потеряли доступ:

1. остановите backend;
2. задайте корректные bootstrap-данные в `.env`;
3. запустите backend снова;
4. если активных операторов в базе нет, bootstrap-пользователь будет восстановлен автоматически.
