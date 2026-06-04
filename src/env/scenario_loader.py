"""Scenario Loader — Reads YAML scenario configs and applies environmental modifiers.

Each scenario represents a real-world network stress condition (rush hour congestion,
rain fade signal degradation, tower failure cascade). The loader validates configs,
applies multipliers/offsets to base PM data, and supports scenario composition.

Usage:
    loader = ScenarioLoader()
    modifiers = loader.load("rush_hour")
    modified_data = loader.apply(pm_data, "rush_hour")

Phase 2 deliverable — Gate G3 requirement: >= 3 distinct scenarios.
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

# ── Registry of supported modifier keys and their validation rules ──
_MODIFIER_SCHEMA: Dict[str, Dict[str, Any]] = {
    # Multipliers (must be > 0)
    "ue_multiplier": {"type": float, "min": 0.1, "max": 50.0, "default": 1.0},
    "ho_attempt_multiplier": {"type": float, "min": 0.1, "max": 50.0, "default": 1.0},
    "ho_failure_multiplier": {"type": float, "min": 0.1, "max": 50.0, "default": 1.0},
    "ho_attempt_spike": {"type": float, "min": 0.1, "max": 50.0, "default": 1.0},
    "neighbor_load_multiplier": {"type": float, "min": 0.1, "max": 50.0, "default": 1.0},
    # Offsets (can be negative)
    "rsrp_offset_db": {"type": float, "min": -30.0, "max": 30.0, "default": 0.0},
    "sinr_offset_db": {"type": float, "min": -20.0, "max": 20.0, "default": 0.0},
    # Floor / ceiling constraints
    "prb_floor": {"type": float, "min": 0.0, "max": 1.0, "default": 0.0},
    # Site failure (integer)
    "failed_sites": {"type": int, "min": 0, "max": 25, "default": 0},
}

# Columns that each modifier type affects in PM data
_MODIFIER_COLUMN_MAP: Dict[str, Dict[str, str]] = {
    "ue_multiplier": {"cell": "connected_ues", "relation": "ho_attempts"},
    "ho_attempt_multiplier": {"cell": "ho_attempt", "relation": "ho_attempts"},
    "ho_failure_multiplier": {"cell": "ho_failure_intra", "relation": "ho_failures"},
    "rsrp_offset_db": {"cell": "rsrp_dbm", "relation": "rsrp_dbm"},
    "sinr_offset_db": {"cell": "sinr_db", "relation": "sinr_db"},
    "prb_floor": {"cell": "prb_utilization_pct", "relation": "prb_utilization_pct"},
}


class ScenarioValidationError(ValueError):
    """Raised when a scenario YAML is malformed or has invalid values."""


class ScenarioLoader:
    """Load, validate, and apply network scenario configurations.

    Scenarios are YAML files in ``configs/scenarios/`` that describe how to
    perturb the base PM data to simulate real-world stress conditions.

    Parameters
    ----------
    scenarios_dir : str or Path, optional
        Directory containing scenario YAML files. Defaults to
        ``<project_root>/configs/scenarios/``.

    Examples
    --------
    >>> loader = ScenarioLoader()
    >>> loader.available()
    ['baseline', 'rain_fade', 'rush_hour', 'tower_failure']
    >>> mods = loader.load("rush_hour")
    >>> mods["name"]
    'rush_hour'
    >>> modified_df = loader.apply(pm_dataframe, "rain_fade")
    """

    def __init__(self, scenarios_dir: Optional[Union[str, Path]] = None) -> None:
        if scenarios_dir is None:
            self._dir = Path(__file__).resolve().parents[2] / "configs" / "scenarios"
        else:
            self._dir = Path(scenarios_dir)

        # Cache loaded scenarios
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Always register the baseline (no modifications)
        self._cache["baseline"] = {
            "name": "baseline",
            "description": "No modifications — original PM data as-is",
        }

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def available(self) -> List[str]:
        """Return sorted list of all available scenario names.

        Scans the scenarios directory for YAML files and always includes
        'baseline'.
        """
        names = {"baseline"}
        if self._dir.exists():
            for f in self._dir.glob("*.yaml"):
                names.add(f.stem)
            for f in self._dir.glob("*.yml"):
                names.add(f.stem)
        return sorted(names)

    def load(self, scenario_name: str) -> Dict[str, Any]:
        """Load and validate a scenario configuration by name.

        Parameters
        ----------
        scenario_name : str
            Name of the scenario (e.g., ``"rush_hour"``). Use ``"baseline"``
            for no modifications.

        Returns
        -------
        dict
            Validated scenario configuration with keys:
            ``name``, ``description``, and modifier-specific keys.

        Raises
        ------
        FileNotFoundError
            If the scenario YAML file does not exist.
        ScenarioValidationError
            If the YAML is malformed or contains invalid values.
        """
        if scenario_name in self._cache:
            return copy.deepcopy(self._cache[scenario_name])

        yaml_path = self._dir / f"{scenario_name}.yaml"
        if not yaml_path.exists():
            yml_path = self._dir / f"{scenario_name}.yml"
            if yml_path.exists():
                yaml_path = yml_path
            else:
                raise FileNotFoundError(
                    f"Scenario '{scenario_name}' not found. "
                    f"Looked in: {self._dir}. "
                    f"Available: {self.available()}"
                )

        try:
            with open(yaml_path) as f:
                raw = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ScenarioValidationError(
                f"Invalid YAML in {yaml_path}: {e}"
            ) from e

        if raw is None or not isinstance(raw, dict):
            raise ScenarioValidationError(
                f"Scenario file {yaml_path} is empty or not a valid mapping."
            )

        # Extract the scenario section (support both top-level and nested)
        if "scenario" in raw:
            config = raw["scenario"]
        else:
            config = raw

        validated = self._validate(config, scenario_name)
        self._cache[scenario_name] = validated
        logger.info("Loaded scenario '%s': %s", scenario_name, validated.get("description", ""))
        return copy.deepcopy(validated)

    def apply(
        self,
        pm_data: pd.DataFrame,
        scenario_name: str,
        *,
        mode: str = "auto",
        rng: Optional[np.random.Generator] = None,
    ) -> pd.DataFrame:
        """Apply scenario modifiers to a copy of PM data.

        Parameters
        ----------
        pm_data : pd.DataFrame
            Base PM data (cell-level or relation-level).
        scenario_name : str
            Scenario to apply. Use ``"baseline"`` for no changes.
        mode : str
            ``"cell"``, ``"relation"``, or ``"auto"`` (detect from columns).
        rng : np.random.Generator, optional
            Random generator for stochastic modifiers (e.g., tower failure
            site selection). Defaults to ``np.random.default_rng()``.

        Returns
        -------
        pd.DataFrame
            Modified copy of PM data with scenario effects applied.
        """
        if scenario_name == "baseline":
            return pm_data.copy()

        config = self.load(scenario_name)
        df = pm_data.copy()

        if rng is None:
            rng = np.random.default_rng()

        # Auto-detect mode
        if mode == "auto":
            mode = "relation" if "source_cell_id" in df.columns else "cell"

        # ── Apply each modifier ──
        df = self._apply_multipliers(df, config, mode)
        df = self._apply_offsets(df, config, mode)
        df = self._apply_floor_constraints(df, config, mode)
        df = self._apply_tower_failure(df, config, mode, rng)
        df = self._apply_ho_attempt_spike(df, config, mode)

        # Recalculate derived columns after modifications
        df = self._recalculate_derived(df, mode)

        return df

    def describe(self, scenario_name: str) -> str:
        """Return a human-readable description of a scenario's effects.

        Parameters
        ----------
        scenario_name : str
            Scenario name.

        Returns
        -------
        str
            Multi-line description of all modifiers and their effects.
        """
        config = self.load(scenario_name)
        lines = [
            f"Scenario: {config['name']}",
            f"Description: {config.get('description', 'N/A')}",
            "",
            "Modifiers:",
        ]

        effects = {
            "ue_multiplier": "UE count multiplied by {v}x",
            "ho_attempt_multiplier": "HO attempts multiplied by {v}x",
            "ho_failure_multiplier": "HO failures multiplied by {v}x",
            "ho_attempt_spike": "HO attempts spiked by {v}x (affected neighbors)",
            "neighbor_load_multiplier": "Neighbor load multiplied by {v}x",
            "rsrp_offset_db": "RSRP offset by {v} dB",
            "sinr_offset_db": "SINR offset by {v} dB",
            "prb_floor": "PRB utilization floor set to {v:.0%}",
            "failed_sites": "{v} site(s) removed from network",
        }

        has_modifiers = False
        for key, template in effects.items():
            if key in config:
                val = config[key]
                default = _MODIFIER_SCHEMA.get(key, {}).get("default")
                if val != default:
                    lines.append(f"  - {template.format(v=val)}")
                    has_modifiers = True

        if not has_modifiers:
            lines.append("  (none — baseline behavior)")

        return "\n".join(lines)

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Load all available scenarios and return as a dict.

        Returns
        -------
        dict
            Mapping of scenario name to validated config.
        """
        result = {}
        for name in self.available():
            result[name] = self.load(name)
        return result

    # ──────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────

    def _validate(self, config: Dict[str, Any], scenario_name: str) -> Dict[str, Any]:
        """Validate and normalize a scenario config dict."""
        validated: Dict[str, Any] = {
            "name": config.get("name", scenario_name),
            "description": config.get("description", ""),
        }

        for key, schema in _MODIFIER_SCHEMA.items():
            if key in config:
                raw_val = config[key]
                try:
                    val = schema["type"](raw_val)
                except (TypeError, ValueError) as e:
                    raise ScenarioValidationError(
                        f"Scenario '{scenario_name}': modifier '{key}' "
                        f"has invalid value '{raw_val}' (expected {schema['type'].__name__}). "
                        f"Error: {e}"
                    ) from e

                if val < schema["min"] or val > schema["max"]:
                    raise ScenarioValidationError(
                        f"Scenario '{scenario_name}': modifier '{key}' = {val} "
                        f"is out of range [{schema['min']}, {schema['max']}]."
                    )

                validated[key] = val

        # Warn about unknown keys (but don't fail — forward compatibility)
        known_keys = set(_MODIFIER_SCHEMA.keys()) | {"name", "description"}
        unknown = set(config.keys()) - known_keys
        if unknown:
            logger.warning(
                "Scenario '%s' has unknown keys: %s (ignored)",
                scenario_name,
                unknown,
            )

        return validated

    # ──────────────────────────────────────────────────────────────────
    # Modifier application methods
    # ──────────────────────────────────────────────────────────────────

    def _apply_multipliers(
        self, df: pd.DataFrame, config: Dict[str, Any], mode: str
    ) -> pd.DataFrame:
        """Apply multiplicative modifiers (ue_multiplier, ho_attempt_multiplier, etc.)."""
        multiplier_keys = [
            "ue_multiplier",
            "ho_attempt_multiplier",
            "ho_failure_multiplier",
            "neighbor_load_multiplier",
        ]

        for key in multiplier_keys:
            if key not in config:
                continue
            factor = config[key]
            if factor == 1.0:
                continue

            col_map = _MODIFIER_COLUMN_MAP.get(key, {})
            col_name = col_map.get(mode)

            if col_name and col_name in df.columns:
                df[col_name] = (df[col_name] * factor).round().astype(df[col_name].dtype)
                logger.debug("Applied %s=%.2f to column '%s'", key, factor, col_name)
            elif key == "neighbor_load_multiplier":
                # Apply to multiple load-related columns
                load_cols = [
                    c for c in df.columns
                    if any(s in c for s in ["ho_attempts", "ho_attempt", "connected_ues"])
                ]
                for col in load_cols:
                    df[col] = (df[col] * factor).round().astype(df[col].dtype)
                logger.debug("Applied %s=%.2f to load columns: %s", key, factor, load_cols)

        return df

    def _apply_offsets(
        self, df: pd.DataFrame, config: Dict[str, Any], mode: str
    ) -> pd.DataFrame:
        """Apply additive offsets (rsrp_offset_db, sinr_offset_db)."""
        offset_keys = ["rsrp_offset_db", "sinr_offset_db"]

        for key in offset_keys:
            if key not in config:
                continue
            offset = config[key]
            if offset == 0.0:
                continue

            col_map = _MODIFIER_COLUMN_MAP.get(key, {})
            col_name = col_map.get(mode)

            if col_name and col_name in df.columns:
                df[col_name] = df[col_name] + offset
                logger.debug("Applied %s=%.1f to column '%s'", key, offset, col_name)
            else:
                # Try common column name variants
                variants = {
                    "rsrp_offset_db": ["avg_rsrp_dBm", "rsrp_mean", "rsrp_dbm"],
                    "sinr_offset_db": ["avg_sinr_dB", "sinr_mean", "sinr_db"],
                }
                for alt_col in variants.get(key, []):
                    if alt_col in df.columns:
                        df[alt_col] = df[alt_col] + offset
                        logger.debug("Applied %s=%.1f to column '%s'", key, offset, alt_col)
                        break

        return df

    def _apply_floor_constraints(
        self, df: pd.DataFrame, config: Dict[str, Any], mode: str
    ) -> pd.DataFrame:
        """Apply floor constraints (prb_floor)."""
        if "prb_floor" not in config:
            return df

        floor_pct = config["prb_floor"] * 100.0  # Convert 0.7 → 70%

        prb_cols = [
            c for c in df.columns
            if "prb" in c.lower() and "pct" in c.lower()
        ]
        for col in prb_cols:
            df[col] = df[col].clip(lower=floor_pct)
            logger.debug("Applied prb_floor=%.1f%% to column '%s'", floor_pct, col)

        return df

    def _apply_tower_failure(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        mode: str,
        rng: np.random.Generator,
    ) -> pd.DataFrame:
        """Simulate tower failure — remove cells from failed sites.

        For relation-level data: removes all relations involving failed site's cells.
        For cell-level data: zeros out metrics for failed cells.
        """
        n_failed = config.get("failed_sites", 0)
        if n_failed == 0:
            return df

        if mode == "relation" and "source_cell_id" in df.columns:
            # Extract unique sites from cell IDs (site = cell_id without sector suffix)
            all_cells = pd.concat([
                df["source_cell_id"], df["target_cell_id"]
            ]).unique()
            # Site ID = cell_id with last character (sector) stripped
            sites = list({str(c)[:-1] for c in all_cells})

            if len(sites) <= n_failed:
                logger.warning(
                    "Cannot fail %d sites — only %d available. Failing %d.",
                    n_failed, len(sites), len(sites) - 1,
                )
                n_failed = max(len(sites) - 1, 0)

            failed_sites = list(rng.choice(sites, size=n_failed, replace=False))
            failed_cells = {
                c for c in all_cells
                if any(str(c).startswith(s) for s in failed_sites)
            }
            logger.info(
                "Tower failure: sites=%s, cells removed=%s",
                failed_sites, failed_cells,
            )

            # Remove relations involving failed cells
            mask = ~(
                df["source_cell_id"].isin(failed_cells)
                | df["target_cell_id"].isin(failed_cells)
            )
            df = df[mask].reset_index(drop=True)

        elif mode == "cell" and "cell_id" in df.columns:
            all_cells = df["cell_id"].unique()
            sites = list({str(c)[:-1] for c in all_cells})

            if len(sites) <= n_failed:
                n_failed = max(len(sites) - 1, 0)

            failed_sites = list(rng.choice(sites, size=n_failed, replace=False))
            failed_cells = {
                c for c in all_cells
                if any(str(c).startswith(s) for s in failed_sites)
            }
            logger.info("Tower failure: removing cells %s", failed_cells)

            # Zero out metrics for failed cells (simulate offline)
            mask = df["cell_id"].isin(failed_cells)
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df.loc[mask, numeric_cols] = 0

        return df

    def _apply_ho_attempt_spike(
        self, df: pd.DataFrame, config: Dict[str, Any], mode: str
    ) -> pd.DataFrame:
        """Apply HO attempt spike for neighbors of failed sites.

        When a tower fails, neighboring cells absorb the load — their HO
        attempts spike dramatically.
        """
        spike = config.get("ho_attempt_spike", 1.0)
        n_failed = config.get("failed_sites", 0)

        if spike <= 1.0 or n_failed == 0:
            return df

        # Spike only applies to surviving cells (already applied tower_failure first)
        attempt_cols = [c for c in df.columns if "attempt" in c.lower()]
        for col in attempt_cols:
            # Apply spike factor to remaining (surviving) data
            df[col] = (df[col] * spike).round().astype(df[col].dtype)
            logger.debug("Applied ho_attempt_spike=%.1f to '%s'", spike, col)

        return df

    def _recalculate_derived(
        self, df: pd.DataFrame, mode: str
    ) -> pd.DataFrame:
        """Recalculate derived rate columns after modifiers change base counts."""
        if mode == "relation":
            if "ho_attempts" in df.columns and "ho_successes" in df.columns:
                safe_att = df["ho_attempts"].clip(lower=1)
                if "ho_success_rate" not in df.columns:
                    # Don't overwrite if not present — some schemas differ
                    pass
        elif mode == "cell":
            att_col = "ho_attempt" if "ho_attempt" in df.columns else "ho_attempts_intra"
            if att_col in df.columns:
                safe_att = df[att_col].clip(lower=1)
                succ_col = "ho_success_intra" if "ho_success_intra" in df.columns else None
                fail_col = "ho_failure_intra" if "ho_failure_intra" in df.columns else None

                if succ_col and succ_col in df.columns and "ho_success_rate_pct" in df.columns:
                    df["ho_success_rate_pct"] = (df[succ_col] / safe_att * 100.0).clip(0, 100)
                if fail_col and fail_col in df.columns and "ho_failure_rate_pct" in df.columns:
                    df["ho_failure_rate_pct"] = (df[fail_col] / safe_att * 100.0).clip(0, 100)

        return df


def load_scenario(
    scenario_name: str,
    scenarios_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Convenience function — load a single scenario config.

    Parameters
    ----------
    scenario_name : str
        Scenario name (e.g., ``"rush_hour"``).
    scenarios_dir : str or Path, optional
        Override scenarios directory.

    Returns
    -------
    dict
        Validated scenario config.

    Examples
    --------
    >>> config = load_scenario("rain_fade")
    >>> config["rsrp_offset_db"]
    -5.0
    """
    return ScenarioLoader(scenarios_dir).load(scenario_name)
