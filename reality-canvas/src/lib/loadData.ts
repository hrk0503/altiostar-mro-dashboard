import type { RelationRecord, SceneManifestEntry, SiteRecord } from "../types";

export async function loadJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
  return (await res.json()) as T;
}

export async function loadSites(): Promise<SiteRecord[]> {
  return loadJson<SiteRecord[]>("/data/sites.json");
}

export async function loadRelations(): Promise<RelationRecord[]> {
  return loadJson<RelationRecord[]>("/data/relations.json");
}

export async function loadSceneManifest(): Promise<SceneManifestEntry[]> {
  return loadJson<SceneManifestEntry[]>("/data/scenes.json");
}

export async function loadCzml(file: string): Promise<unknown[]> {
  return loadJson<unknown[]>(`/data/${file}`);
}
