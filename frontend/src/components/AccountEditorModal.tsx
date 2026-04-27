import React, { useEffect, useState } from "react";

import type { Account, AccountDraft } from "../types";
import { Modal } from "./Modal";

type Props = {
  account: Account | null;
  busy: boolean;
  error: string;
  mode: "create" | "edit" | null;
  onClose: () => void;
  onSubmit: (payload: AccountDraft) => Promise<void>;
};

function draftFromAccount(account: Account | null): AccountDraft {
  return {
    label: account?.label ?? "",
    email_hint: account?.email_hint ?? null,
    notes: account?.notes ?? "",
    is_enabled: account?.is_enabled ?? true
  };
}

export function AccountEditorModal({ account, busy, error, mode, onClose, onSubmit }: Props) {
  const [draft, setDraft] = useState<AccountDraft>(() => draftFromAccount(account));

  useEffect(() => {
    setDraft(draftFromAccount(account));
  }, [account, mode]);

  if (!mode) {
    return null;
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      ...draft,
      label: draft.label.trim(),
      email_hint: draft.email_hint?.trim() ? draft.email_hint.trim() : null,
      notes: draft.notes.trim()
    });
  }

  return (
    <Modal
      open={Boolean(mode)}
      onClose={onClose}
      eyebrow="Account"
      title={mode === "create" ? "Новая учетная запись" : "Редактирование учетной записи"}
    >
      <form className="form-grid" onSubmit={handleSubmit}>
        <label className="field">
          <span>Название</span>
          <input
            value={draft.label}
            onChange={(event) => setDraft({ ...draft, label: event.target.value })}
            placeholder="Например: Sales team owner"
            required
          />
        </label>

        <label className="field">
          <span>Email hint</span>
          <input
            value={draft.email_hint ?? ""}
            onChange={(event) => setDraft({ ...draft, email_hint: event.target.value || null })}
            placeholder="owner@example.com"
          />
        </label>

        <label className="field">
          <span>Заметки</span>
          <textarea
            rows={5}
            value={draft.notes}
            onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
            placeholder="Для какого бизнеса используется, какие есть ограничения, кто отвечает за логин."
          />
        </label>

        <label className="checkbox-row">
          <input
            checked={draft.is_enabled}
            onChange={(event) => setDraft({ ...draft, is_enabled: event.target.checked })}
            type="checkbox"
          />
          <span>Участвует в автоматических scan-проверках</span>
        </label>

        {error ? <div className="alert error">{error}</div> : null}

        <div className="button-row">
          <button className="ghost-button" onClick={onClose} type="button">
            Отмена
          </button>
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Сохраняю..." : mode === "create" ? "Создать учетку" : "Сохранить изменения"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
