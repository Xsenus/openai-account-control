import React, { useEffect, useState } from "react";

import { Modal } from "./Modal";

type Props = {
  busy: boolean;
  error: string;
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: { username: string; password: string; is_active: boolean }) => Promise<void>;
};

export function OperatorEditorModal({ busy, error, open, onClose, onSubmit }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    if (!open) {
      setUsername("");
      setPassword("");
      setIsActive(true);
    }
  }, [open]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      username: username.trim(),
      password,
      is_active: isActive
    });
    setUsername("");
    setPassword("");
    setIsActive(true);
  }

  return (
    <Modal eyebrow="Access" onClose={onClose} open={open} title="Новый оператор панели">
      <form className="form-grid" onSubmit={handleSubmit}>
        <label className="field">
          <span>Логин оператора</span>
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="ops-team"
            required
          />
        </label>

        <label className="field">
          <span>Стартовый пароль</span>
          <input
            autoComplete="new-password"
            minLength={8}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Минимум 8 символов"
            required
          />
        </label>

        <label className="checkbox-row">
          <input checked={isActive} onChange={(event) => setIsActive(event.target.checked)} type="checkbox" />
          <span>Оператор активен и может входить в панель сразу после создания</span>
        </label>

        {error ? <div className="alert error">{error}</div> : null}

        <div className="button-row">
          <button className="ghost-button" disabled={busy} onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Создаю..." : "Создать оператора"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
