import React, { useState } from "react";

type Props = {
  onSubmit: (payload: {
    label: string;
    email_hint: string | null;
    notes: string;
    is_enabled: boolean;
  }) => Promise<void>;
};

export function AccountForm({ onSubmit }: Props) {
  const [label, setLabel] = useState("");
  const [emailHint, setEmailHint] = useState("");
  const [notes, setNotes] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await onSubmit({
        label,
        email_hint: emailHint.trim() ? emailHint.trim() : null,
        notes,
        is_enabled: enabled
      });
      setLabel("");
      setEmailHint("");
      setNotes("");
      setEnabled(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel form-grid" onSubmit={handleSubmit}>
      <h3>Добавить учетную запись</h3>
      <label className="field">
        <span>Понятное имя</span>
        <input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Например: Личная Plus" required />
      </label>

      <label className="field">
        <span>Email hint</span>
        <input value={emailHint} onChange={(event) => setEmailHint(event.target.value)} placeholder="me@example.com" />
      </label>

      <label className="field">
        <span>Заметки</span>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} placeholder="Любые комментарии: где используется, чей workspace, нужен ли owner-доступ и т.д." />
      </label>

      <label className="checkbox-row">
        <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
        <span>Учетка активна и должна участвовать в автоматических проверках</span>
      </label>

      <button type="submit" className="primary-button" disabled={busy}>
        {busy ? "Сохраняю..." : "Добавить"}
      </button>
    </form>
  );
}
