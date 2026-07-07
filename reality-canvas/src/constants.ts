// All user-facing strings live here (vertical-agnostic rule — no hardcoded
// domain nouns scattered through components).

export const APP_TITLE = "WINNIIO Reality Canvas";
export const APP_SUBTITLE = "RAN digital twin — pre-generated synthetic scenes (live API in P2)";

export const LOGIN_LABEL = "Demo access";
export const LOGIN_GATE_NOTE = "demo gate — SSO in P3";
export const LOGIN_PLACEHOLDER = "Enter demo password";
export const LOGIN_BUTTON = "Enter";
export const LOGIN_ERROR = "Incorrect password";

export const LAYER_PANEL_TITLE = "Layers";
export const LAYER_SITES = "Sites";
export const LAYER_BEAMS = "Sector beams";
export const LAYER_RELATIONS = "Neighbor relations";
export const LAYER_UES = "UEs";
export const LAYER_HANDOVERS = "Handover markers";

export const SCENE_PANEL_TITLE = "Scene";
export const SCENE_UE_COUNT_LABEL = "UE count";
export const SCENE_SEED_LABEL = "Seed";
export const SCENE_REGENERATE_NOTE = "pre-generated scenes (live API in P2)";

export const RELATIONS_THRESHOLD_LABEL = "Hide relations above";

export const BASEMAP_DIM_LABEL = "Dim basemap";

export const STATS_SITES = "Sites";
export const STATS_CELLS = "Cells";
export const STATS_RELATIONS = "Relations";
export const STATS_UES = "UEs";
export const STATS_HANDOVERS = "Handovers";

export const ERROR_DATA_LOAD = "Data failed to load. Check your connection and reload.";
export const ERROR_BOUNDARY_TITLE = "Something went wrong rendering the canvas.";
export const ERROR_BOUNDARY_RETRY = "Reload";

export const DEMO_PASSWORD_DEFAULT = "Winniio-2019";
export const SESSION_STORAGE_KEY = "reality-canvas-auth";

// ── P4: live API mode ──
export const LIVE_MODE_LABEL = "Live API";
export const OFFLINE_MODE_LABEL = "Pre-generated (offline)";
export const SCENE_REGENERATE_NOTE_LIVE = "live scene generation via API";

export const SIMULATE_PANEL_TITLE = "MRO Optimization";
export const SIMULATE_BUTTON = "Run MRO Optimization (synthetic)";
export const SIMULATE_BUTTON_RUNNING = "Running…";
export const SIMULATE_ERROR = "Optimization run failed. Check the API connection and try again.";
export const SIMULATE_ERROR_OFFLINE = "MRO Optimization requires the live API — offline mode active.";
export const SIMULATE_RELATIONS_LABEL = "Relations optimized";
export const SIMULATE_AVG_LABEL = "Avg success rate";
export const SIMULATE_TOGGLE_BEFORE = "Show: Before";
export const SIMULATE_TOGGLE_AFTER = "Show: After";

export const API_HEALTH_ERROR = "Live API unreachable — using pre-generated scenes.";
