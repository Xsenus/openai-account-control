# GitHub и VPS deployment

Эта схема рассчитана на прямую установку на VPS через Python venv и systemd.

## Что публикуем в GitHub

В репозиторий можно отправлять код, документацию, `.env.example`, `.env.production.example`, systemd unit и deploy-скрипты.

Нельзя отправлять:

- `.env`;
- каталог `data/`;
- SQLite базу;
- Playwright browser profiles;
- `storage_state.json`;
- `frontend/node_modules`;
- локальные сборки `frontend/dist` и `backend/app/static`;
- `.venv`.

Это закрыто через `.gitignore`.

## Первый push в GitHub

```bash
git init
git add .
git commit -m "Prepare native VPS deployment"
git branch -M main
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

Перед `git add .` проверьте:

```bash
git status --short
```

В выводе не должно быть `.env`, `data/`, `.venv/`, `frontend/node_modules/`, базы или session-state файлов.

## Подготовка VPS

Нужны системные пакеты Python и библиотеки для Playwright Chromium.

Минимально для Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip curl ca-certificates
```

Node.js на VPS не обязателен: GitHub Actions собирает frontend заранее и загружает `frontend/dist` вместе с релизом.

## Production `.env`

На VPS создайте директорию проекта и `.env`:

```bash
sudo mkdir -p /opt/openai-account-control
sudo chown -R "$USER":"$USER" /opt/openai-account-control
cd /opt/openai-account-control
```

Можно взять шаблон из `.env.production.example`.

Обязательно заменить:

- `FRONTEND_PUBLIC_URL`;
- `ADMIN_PASSWORD`;
- `ENCRYPTION_KEY`;
- `PLAYWRIGHT_TIMEZONE_ID`;
- `SESSION_COOKIE_SECURE`, если нет HTTPS.

Ключ шифрования:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Важно: если потерять `ENCRYPTION_KEY`, старые сохраненные session-state нельзя будет расшифровать.

## GitHub Secrets

В GitHub откройте `Settings -> Secrets and variables -> Actions` и добавьте:

- `VPS_HOST` - IP или домен VPS;
- `VPS_USER` - SSH-пользователь;
- `VPS_SSH_KEY` - приватный SSH-ключ для деплоя;
- `VPS_PORT` - SSH-порт, обычно `22`;
- `VPS_DEPLOY_PATH` - путь проекта, например `/opt/openai-account-control`;
- `VPS_ENV_FILE` - опционально, полный production `.env`.

Если `VPS_ENV_FILE` не задан, workflow не перезаписывает `.env` на сервере.

## Автоматический деплой

Workflow `.github/workflows/deploy-vps.yml` запускается:

- автоматически при push в `main`;
- вручную через `workflow_dispatch`.

Он:

1. Собирает frontend в GitHub Actions.
2. Упаковывает проект без секретов и локальных данных.
3. Загружает архив на VPS.
4. Распаковывает код в `VPS_DEPLOY_PATH`.
5. Запускает `bash scripts/deploy-vps-native.sh`.
6. Обновляет Python venv, копирует frontend в `backend/app/static` и перезапускает systemd service.

Данные сохраняются в `/opt/openai-account-control/data` на VPS и не удаляются при деплое.

## Ручной запуск на VPS

```bash
cd /opt/openai-account-control
sudo bash scripts/deploy-vps-native.sh
```

Проверка:

```bash
systemctl status openai-account-control --no-pager
curl http://127.0.0.1:8000/api/health
```

## Reverse proxy и HTTPS

Приложение должно слушать `127.0.0.1:8000`, а внешний доступ лучше делать через FASTPANEL или reverse proxy на этот локальный адрес.

При HTTPS:

```env
FRONTEND_PUBLIC_URL=https://your-domain.com
SESSION_COOKIE_SECURE=true
```

Без HTTPS:

```env
FRONTEND_PUBLIC_URL=http://your-domain-or-ip:8000
SESSION_COOKIE_SECURE=false
```

## Бэкапы

Регулярно сохраняйте:

- `/opt/openai-account-control/.env`;
- `/opt/openai-account-control/data/`.

Без этих файлов восстановить аккаунты и сохраненные сессии нельзя.
