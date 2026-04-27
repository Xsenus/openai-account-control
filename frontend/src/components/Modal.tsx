import React, { useEffect } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
};

export function Modal({ title, eyebrow = "Dialog", open, onClose, children }: Props) {
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <section
        className="modal"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="modal-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2>{title}</h2>
          </div>
          <button className="ghost-button modal-close-button" aria-label="Закрыть" onClick={onClose} type="button">
            ×
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </section>
    </div>
  );
}
