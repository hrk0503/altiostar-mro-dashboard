# Seasonal Variation of LTE Handover KPIs — Research Basis

These datasets are not "the same data with a different month stamp." Each
season bends the realistic curves using **documented RF-propagation physics**,
and the effect is **climate- and band-specific**, so the three network
footprints (Kyiv, rural Nagano, downtown Tokyo) react differently to the same
season. That gives the MRO/RL agent four distinct, learnable regimes per site.

## The physical mechanisms (and how each is modelled)

| Mechanism | What happens | Which footprint/band | Modelled as |
|---|---|---|---|
| **Foliage attenuation** | Deciduous canopy in-leaf adds ~3–10 dB path loss at ~2 GHz vs bare winter (0.3–0.8 dB/m at 2 GHz, higher at 2.5 GHz); wet leaves far worse. Spring/summer hurt. | Vegetated areas (rural Japan forests, parks). Band 41 (2.5 GHz) > Band 1/3. | RSRP offset ↓ and failure-rate ↑ in spring/summer for `mountain` climate. |
| **Snow / ice accretion + cold** | Antenna icing, radome loss, electronics drift in continental & mountain winters → RSRP ↓, failures ↑. | Kyiv (continental), Nagano (mountain). Tokyo winter mild/dry → minimal. | Large winter `fail`×, RSRP −5 dB for continental/mountain; small for coastal. |
| **Tropospheric ducting** | Temperature-inversion co-channel interference, "predominately co-channel **TDD**", peaks summer/autumn over **coastal** water. Causes handovers to wrong/distant co-channel cells + ping-pong. | **Band 41 is TDD**; **Tokyo is coastal (Tokyo Bay)**. Inland Kyiv/Nagano largely spared. | `wrong_bias` (extra wrong-cell share) + high `pp`× in Tokyo summer/autumn only. |
| **Typhoon / rain + wind** | Wind-driven foliage fades (up to ~22 dB) and Band 41 rain fade in Japan's autumn typhoon season. | Rural Japan + Tokyo, autumn. | Elevated `fail`× in autumn for mountain/coastal. |
| **Traffic seasonality** | Demand swings: Tokyo summer tourism + rainy season; **Nagano winter ski crowds**; Kyiv mild summer. | All, direction differs. | `load`× per climate/season (Nagano winter load ↑, Tokyo summer load ↑↑). |

## Resulting learnable signatures

- **Rural Nagano** → failures dominated by **too-late HO** (wide-spaced cells,
  `late_bias=0.20`), worst in winter (snow + ski load) and autumn (typhoon).
- **Downtown Tokyo** → summer/autumn dominated by **wrong-cell + ping-pong**
  (Band 41 TDD ducting over Tokyo Bay); winter is the calm baseline.
- **Kyiv** → **high overall failure + low RSRP in winter** (snow/cold), mild
  otherwise; classic continental swing.

## Sources
- ITU-R Rec. P.833-7 — *Attenuation in vegetation*.
- MP Antenna — *Impact of Foliage and Seasonal Changes on RF and Wireless Networks*.
- RF Essentials — *How Vegetation Attenuation Affects RF Propagation*.
- Wikipedia — *Tropospheric propagation* / *Rain fade*.
- US Patent US11018784B2 — *Detecting tropospheric ducting interference in cellular networks*.
- arXiv:2404.05477 — *Large-Scale Attenuation Effects in a 26 GHz Urban Micro-Cell* (leaf-on 5.9 dB vs leaf-off 2.3 dB).

> Magnitudes are tuned for clearly-separable synthetic regimes, not calibrated
> to a specific measurement campaign. All data is synthetic and labelled as such.
