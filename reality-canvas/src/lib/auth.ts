import { DEMO_PASSWORD_DEFAULT, SESSION_STORAGE_KEY } from "../constants";

function expectedPassword(): string {
  return import.meta.env.VITE_DEMO_PASSWORD ?? DEMO_PASSWORD_DEFAULT;
}

export function checkPassword(input: string): boolean {
  return input === expectedPassword();
}

export function isAuthenticated(): boolean {
  if (typeof sessionStorage === "undefined") return false;
  return sessionStorage.getItem(SESSION_STORAGE_KEY) === "true";
}

export function setAuthenticated(): void {
  sessionStorage.setItem(SESSION_STORAGE_KEY, "true");
}
