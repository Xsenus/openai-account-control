import React from "react";

import { Modal } from "./Modal";

type Props = {
  accountId: string;
  open: boolean;
  onClose: () => void;
};

const storageStateExample = `{
  "cookies": [],
  "origins": []
}`;

export function StorageStateHelpModal({ accountId, open, onClose }: Props) {
  const captureCommand = `powershell -ExecutionPolicy Bypass -File .\\scripts\\capture-storage-state.ps1 \`
  -AccountId ${accountId || "<ACCOUNT_ID>"} \`
  -BackendUrl http://127.0.0.1:8000 \`
  -PanelUsername admin \`
  -PanelPassword <PANEL_PASSWORD> \`
  -OutputPath .\\storage_state.json`;

  return (
    <Modal eyebrow="Session state" title="Как получить правильный JSON" open={open} onClose={onClose}>
      <div className="stack">
        <div className="note-card">
          <p>
            Панель принимает только Playwright <code>storage_state</code>. У файла должны быть верхние поля{" "}
            <code>cookies</code> и <code>origins</code>.
          </p>
        </div>

        <section className="stack">
          <div>
            <p className="eyebrow">Формат</p>
            <h3>Что импортируется</h3>
          </div>
          <pre className="code-block">{storageStateExample}</pre>
          <p className="muted">
            Это только форма файла. Для реальной рабочей сессии внутри должны быть актуальные cookies и localStorage.
            JSON с полями <code>accessToken</code>, <code>sessionToken</code>, <code>user</code> или <code>account</code>{" "}
            не подходит: это не Playwright storage_state.
          </p>
        </section>

        <section className="stack">
          <div>
            <p className="eyebrow">Локально</p>
            <h3>Если backend запущен на этом ПК</h3>
          </div>
          <ol className="steps-list">
            <li>
              Нажмите кнопку <code>Локальный вход</code> у нужной учетной записи.
            </li>
            <li>В открывшемся Chromium войдите в ChatGPT.</li>
            <li>Окно закроется только после того, как Playwright увидит реальный вход.</li>
          </ol>
        </section>

        <section className="stack">
          <div>
            <p className="eyebrow">VPS / Headless</p>
            <h3>Если панель живет на удаленном сервере</h3>
          </div>
          <p className="muted">
            Локальный вход на VPS неудобен, потому что браузер откроется на сервере. В этом случае снимайте{" "}
            <code>storage_state</code> у себя на ПК и отправляйте его в панель helper-скриптом.
          </p>
          <pre className="code-block">{captureCommand}</pre>
          <p className="muted">
            Скрипт откроет Chromium, попросит войти в нужный ChatGPT-аккаунт, сохранит файл{" "}
            <code>storage_state.json</code> и сразу отправит его в выбранную запись панели.
          </p>
        </section>
      </div>
    </Modal>
  );
}
