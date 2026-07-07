import { useState, type FormEvent } from "react";
import { checkPassword, setAuthenticated } from "../lib/auth";
import {
  LOGIN_BUTTON,
  LOGIN_ERROR,
  LOGIN_GATE_NOTE,
  LOGIN_LABEL,
  LOGIN_PLACEHOLDER,
} from "../constants";

export function LoginGate({ onSuccess }: { onSuccess: () => void }) {
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (checkPassword(value)) {
      setAuthenticated();
      onSuccess();
    } else {
      setError(true);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--canvas-navy)",
      }}
    >
      <form
        onSubmit={handleSubmit}
        aria-label={LOGIN_LABEL}
        style={{
          background: "var(--canvas-panel)",
          padding: 32,
          borderRadius: 8,
          border: "1px solid var(--canvas-cyan)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
          minWidth: 280,
        }}
      >
        <h1 style={{ fontSize: 18, margin: 0 }}>{LOGIN_LABEL}</h1>
        <p style={{ fontSize: 12, opacity: 0.7, margin: 0 }}>{LOGIN_GATE_NOTE}</p>
        <label htmlFor="demo-password">{LOGIN_PLACEHOLDER}</label>
        <input
          id="demo-password"
          type="password"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setError(false);
          }}
          placeholder={LOGIN_PLACEHOLDER}
          style={{ padding: 8 }}
        />
        {error && (
          <p role="alert" style={{ color: "#dc3545", fontSize: 12, margin: 0 }}>
            {LOGIN_ERROR}
          </p>
        )}
        <button type="submit" style={{ padding: 10, background: "var(--canvas-cyan)", border: "none", borderRadius: 4, fontWeight: 600 }}>
          {LOGIN_BUTTON}
        </button>
      </form>
    </div>
  );
}
