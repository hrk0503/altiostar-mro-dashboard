const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak, PageNumber, LevelFormat } = require("docx");

const DARK_BLUE = "1B3A5C";
const MEDIUM_BLUE = "2E75B6";
const DARK_RED = "8B0000";
const WHITE = "FFFFFF";
const LIGHT_GRAY = "F2F2F2";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function heading1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: DARK_BLUE })] });
}
function heading2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, size: 24, font: "Arial", color: MEDIUM_BLUE })] });
}
function heading3(text) {
  return new Paragraph({ spacing: { before: 200, after: 80 },
    children: [new TextRun({ text, bold: true, size: 22, font: "Arial", color: DARK_BLUE })] });
}
function bodyText(text) {
  return new Paragraph({ spacing: { after: 120 },
    children: [new TextRun({ text, size: 21, font: "Arial", color: "333333" })] });
}
function boldBody(bold, normal) {
  return new Paragraph({ spacing: { after: 120 },
    children: [
      new TextRun({ text: bold, bold: true, size: 21, font: "Arial", color: "333333" }),
      new TextRun({ text: normal, size: 21, font: "Arial", color: "333333" }),
    ] });
}
function spacer(pts = 120) {
  return new Paragraph({ spacing: { after: pts }, children: [] });
}

const bulletConfig = {
  reference: "bullets",
  levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
};
function bullet(text) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
    children: [new TextRun({ text, size: 21, font: "Arial", color: "333333" })] });
}
function bulletBold(bold, normal) {
  return new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 },
    children: [
      new TextRun({ text: bold, bold: true, size: 21, font: "Arial", color: "333333" }),
      new TextRun({ text: normal, size: 21, font: "Arial", color: "333333" }),
    ] });
}

function makeRow(cells, headerRow = false) {
  const bgColor = headerRow ? DARK_BLUE : null;
  const textColor = headerRow ? WHITE : "333333";
  return new TableRow({
    children: cells.map(({ text, width, bold }) =>
      new TableCell({
        borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
        shading: bgColor ? { fill: bgColor, type: ShadingType.CLEAR } : undefined,
        children: [new Paragraph({ children: [new TextRun({ text, bold: bold || headerRow, size: 18, font: "Arial", color: textColor })] })]
      })
    )
  });
}

function weekBlock(weekLabel, title, items) {
  return [
    heading3(`${weekLabel}: ${title}`),
    ...items.map(i => bullet(i)),
    spacer(60),
  ];
}

const doc = new Document({
  numbering: { config: [bulletConfig] },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "INTERNAL — WINNIIO PLANNING DOCUMENT", size: 16, font: "Arial", color: DARK_RED, italic: true })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "CONFIDENTIAL — Page ", size: 16, font: "Arial", color: "999999" }),
          new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: "999999" })]
      })] })
    },
    children: [
      // TITLE
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "Altiostar / Rakuten Symphony", size: 36, bold: true, font: "Arial", color: DARK_BLUE })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "MRO Digital Twin — Internal Project Plan", size: 28, bold: true, font: "Arial", color: MEDIUM_BLUE })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "6-Month Reverse-Engineered Roadmap", size: 22, font: "Arial", color: "666666" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
        children: [new TextRun({ text: "April 29, 2026 — WINNIIO Internal Only", size: 20, font: "Arial", color: DARK_RED })] }),

      // OUTCOME TARGET
      heading1("6-Month Outcome Target"),
      bodyText("A functional MRO digital twin that trains reinforcement learning models on a specific Japanese coverage area, validates against historical KPIs, and deploys as an xApp on near-RT RIC in shadow mode."),
      spacer(60),
      boldBody("Success metric: ", "Measurable reduction in handover failure rate (shadow mode comparison vs. manual CIO tuning baseline)."),

      // TEAM
      heading1("Team Composition"),
      heading2("WINNIIO Side"),
      bulletBold("Nicolas Waern — ", "Project lead, SMILE methodology, stakeholder management, vendor vetting"),
      bulletBold("CityGML / Geospatial Specialist — ", "Via Lars Harrie network (Lund University) or DTC. PLATEAU data absorption, LOD quality assessment"),
      bulletBold("RF / Propagation Specialist — ", "Via Invite to Innovate (DTC Telecom WG). Coverage modeling, Sionna/Atoll integration"),
      bulletBold("ML / RL Engineer — ", "WINNIIO network. Reward function design, model training, PyTorch/Stable Baselines3"),
      bulletBold("3D / Spatial Developer — ", "Cesium/Omniverse specialist. Scene composition, USD pipeline, visualization"),

      heading2("Altiostar Side (They Bring)"),
      bulletBold("Soumyadeep Mukherjee — ", "Product Manager. Use case prioritization, KPI definition, internal champion"),
      bulletBold("RAN/RF Engineer — ", "CIO tuning expert. Mobility domain knowledge, current optimization workflow"),
      bulletBold("AI/ML Engineer — ", "Model architecture, training pipeline, integration with RCP"),
      bulletBold("Data Engineer — ", "E2/A1 data extraction, format documentation, pipeline setup"),
      bulletBold("Network Operations Contact — ", "KPI baselines, live network access, validation data"),
      bulletBold("RCP Platform Admin — ", "Sandbox access, xApp deployment documentation, compute allocation"),

      // ACCESS
      new Paragraph({ children: [new PageBreak()] }),
      heading1("Access Required from Altiostar / Rakuten"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3500, 5860],
        rows: [
          makeRow([{ text: "Data / Access", width: 3500 }, { text: "Details", width: 5860 }], true),
          ...[
            ["Site Database", "Tower lat/long, azimuth, tilt, height (anonymized region OK)"],
            ["Neighbor Cell Lists", "Current neighbor definitions + CIO values per cell"],
            ["UE Measurement Reports", "RSRP, RSRQ, SINR (historical, at least 3 months, anonymized)"],
            ["Handover Logs", "Success, failure, ping-pong events with timestamps"],
            ["Cell Load Data", "Per-sector load metrics, PRB utilization"],
            ["Propagation Model Params", "Atoll export or equivalent RF planning data"],
            ["KPI Baselines", "Current HO failure rate, ping-pong rate, per-cluster"],
            ["RCP Sandbox Access", "Platform documentation, API specs, xApp deployment guide"],
            ["Lab Compute", "GPU allocation for training (or cloud budget)"],
          ].map(([a, b], i) => makeRow([
            { text: a, width: 3500, bold: true },
            { text: b, width: 5860 }
          ]))
        ]
      }),

      // JAPAN CITYGML
      spacer(200),
      heading1("Japan CityGML — PLATEAU Project"),
      bodyText("Japan's MLIT (Ministry of Land, Infrastructure, Transport and Tourism) has released PLATEAU — one of the most sophisticated open CityGML datasets in the world. 250+ cities at LOD1-LOD3, open data, free commercial use."),
      bulletBold("Coverage: ", "Tokyo 23 wards, Osaka, Nagoya, Sendai, and 200+ more cities"),
      bulletBold("Data: ", "Building footprints, heights, roof shapes, terrain, roads, vegetation, land use"),
      bulletBold("Format: ", "CityGML 2.0, convertible to 3D Tiles (Cesium) or USD (Omniverse)"),
      bulletBold("Already on Cesium ion: ", "23 million buildings pre-tiled as 'Japan 3D Buildings' — API call, not custom build"),
      bulletBold("Lars Harrie (Lund University): ", "CityGML expert, led Swedish 3CIM national profile. Available for advisory on absorption pipeline"),
      spacer(60),
      boldBody("Key insight: ", "The CityGML absorption pipeline for the target coverage area is essentially a Cesium ion API call. This is a massive time saver for Phase 2."),

      // TECH STACK
      new Paragraph({ children: [new PageBreak()] }),
      heading1("Technology Stack"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2200, 2800, 4360],
        rows: [
          makeRow([{ text: "Layer", width: 2200 }, { text: "Tool", width: 2800 }, { text: "Why", width: 4360 }], true),
          ...[
            ["3D City Model", "PLATEAU CityGML", "Japan open LOD2/3 buildings, terrain, roads, vegetation"],
            ["Geospatial Canvas", "Cesium ion + 3D Tiles", "Stream massive city models, overlay tower data, web-native"],
            ["Scene Composition", "NVIDIA Omniverse", "Collaborative editing, USD pipeline, physics simulation"],
            ["RF Simulation", "NVIDIA Sionna", "Open-source, GPU-accelerated, differentiable ray tracing for RF"],
            ["Propagation Alt.", "Atoll export / Volcano", "RF coverage prediction from existing planning tools"],
            ["RL Training", "PyTorch + Stable Baselines3", "Reward: successful HO, penalty: failure/ping-pong"],
            ["Physics ML", "NVIDIA Modulus (optional)", "Physics-informed neural nets for RF propagation learning"],
            ["Mobility Sim", "SUMO / custom", "Synthetic UE paths: vehicles, pedestrians, Shinkansen"],
            ["Deployment", "xApp on near-RT RIC", "Shadow mode first, then closed-loop via E2/A1"],
            ["Compute", "GPU cluster (lab or cloud)", "Training + ray-tracing acceleration"],
          ].map(([a, b, c], i) => makeRow([
            { text: a, width: 2200, bold: true },
            { text: b, width: 2800 },
            { text: c, width: 4360 }
          ]))
        ]
      }),

      spacer(120),
      heading2("Key Links"),
      bulletBold("PLATEAU: ", "https://www.mlit.go.jp/plateau/en/"),
      bulletBold("PLATEAU on Cesium: ", "https://cesium.com/blog/2024/06/03/japan-3d-buildings/"),
      bulletBold("NVIDIA Sionna: ", "https://developer.nvidia.com/sionna (Apache 2.0, GitHub: NVlabs/sionna)"),
      bulletBold("NVIDIA AODT: ", "https://developer.nvidia.com/aerial-omniverse-digital-twin"),
      bulletBold("Lars Harrie: ", "https://www.gis.lu.se/lars-harrie"),
      bulletBold("CityGML to 3D Tiles: ", "https://github.com/njam/citygml-to-3dtiles"),

      // WEEK BY WEEK
      new Paragraph({ children: [new PageBreak()] }),
      heading1("Week-by-Week Plan (Reverse-Engineered from Month 6)"),

      ...weekBlock("Week 0", "SPIN Twinning Workshop (Half Day)", [
        "Map as-is: current MRO workflow, tools, data flows, pain points",
        "Define target coverage area (which Tokyo ward / cluster?)",
        "Agree on success KPI: reduce HO failure rate by X% in shadow mode",
        "Identify who from their side joins each phase",
        "Output: Reality Emulation Canvas (documented current state + target)",
      ]),

      ...weekBlock("Weeks 1-2", "Data Audit + PLATEAU Absorption", [
        "Week 1: Data audit — what do they have, what format, what is accessible",
        "Week 1: PLATEAU CityGML download for target area, load via Cesium ion",
        "Week 2: Invite to Innovate — reach out to DTC Telecom WG, Lars Harrie, NVIDIA Sionna team",
        "Week 2: Cesium prototype — tower locations on PLATEAU 3D city model, coverage cones",
      ]),

      ...weekBlock("Weeks 3-4", "Vendor Vetting + MVT Spec", [
        "Week 3: Evaluate Sionna vs. Atoll export vs. Volcano for propagation modeling",
        "Week 3: RCP platform assessment — how do xApps deploy, interface specs, latency constraints",
        "Week 4: MVT specification document — what gets built, what team, what cost, what timeline",
        "Output: Validated MVT spec, revised Phase 3 scope + budget, 6-month roadmap",
      ]),

      ...weekBlock("Weeks 5-8", "MVT Foundation (Phase 3 Starts)", [
        "Week 5: CityGML → USD pipeline operational, PLATEAU data loaded into Omniverse",
        "Week 6: Tower data overlay — site DB mapped onto 3D city model with real azimuths/tilts",
        "Week 7: RF propagation layer — Sionna ray-tracing on 3D model, or Atoll data import",
        "Week 8: First synthetic mobility — SUMO vehicle paths, handover trigger points identified",
        "Output: Visual MVT — towers, buildings, coverage, moving UEs in 3D",
      ]),

      ...weekBlock("Weeks 9-12", "Data Integration + RL Setup", [
        "Week 9: Historical data pipeline — ingest anonymized UE measurement reports into the twin",
        "Week 10: Handover event replay — map historical HO success/failure onto 3D environment",
        "Week 11: RL environment setup — OpenAI Gym wrapper around the twin, reward function defined",
        "Week 12: First RL training runs — agent learns on synthetic + historical data",
        "Output: Training pipeline operational, first model checkpoint",
      ]),

      ...weekBlock("Weeks 13-18", "Training + Validation", [
        "Weeks 13-14: Reward function tuning — balance HO success, ping-pong penalty, load distribution",
        "Weeks 15-16: Backtesting — train on months 1-6, predict month 7, compare to reality",
        "Week 17: Model refinement — iterate architecture, hyperparams, reward weighting",
        "Week 18: Validation report — measured improvement vs. baseline CIO tuning",
        "Output: Trained model + validation results + confidence metrics",
      ]),

      ...weekBlock("Weeks 19-24", "Shadow Mode + Handoff", [
        "Week 19: Package model as xApp for near-RT RIC",
        "Week 20: Deploy in shadow mode on RCP sandbox — model suggests, humans verify",
        "Weeks 21-22: Shadow mode monitoring — compare model vs. actual operator decisions",
        "Week 23: Results analysis — where does the model outperform manual, where does it fail",
        "Week 24: Handoff — trained model, documentation, technology transfer, Phase 4 roadmap",
        "Output: xApp in shadow mode, performance report, go/no-go for closed-loop",
      ]),

      // INVITE TO INNOVATE
      new Paragraph({ children: [new PageBreak()] }),
      heading1("Invite to Innovate — DTC Network"),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2500, 3000, 3860],
        rows: [
          makeRow([{ text: "Contact / Org", width: 2500 }, { text: "Expertise", width: 3000 }, { text: "How They Help", width: 3860 }], true),
          ...[
            ["Lars Harrie (Lund Uni)", "CityGML, 3D city models, Swedish GIS", "PLATEAU absorption pipeline, LOD quality assessment"],
            ["DTC Telecom WG", "5G digital twins, network sim", "Peer review of MVT architecture, RF modeling"],
            ["NVIDIA Sionna Team", "GPU-accelerated 5G simulation", "Ray-tracing propagation, channel modeling"],
            ["Dan Isaacs (DTC CTO)", "DT standards, methodology", "Credibility, architecture review, reference"],
            ["Cesium Team", "Geospatial streaming, 3D Tiles", "PLATEAU tiling, performance optimization"],
            ["RF Planning Specialists", "Propagation modeling, coverage", "Atoll integration, model calibration"],
          ].map(([a, b, c]) => makeRow([
            { text: a, width: 2500, bold: true },
            { text: b, width: 3000 },
            { text: c, width: 3860 }
          ]))
        ]
      }),

      // COST ESTIMATE
      spacer(200),
      heading1("Cost Estimate (Internal — Phase 3 Scoping)"),
      bodyText("This is for internal planning only. Not shared with Altiostar until Phase 1+2 output defines the actual scope."),
      bulletBold("WINNIIO project lead: ", "Included in advisory fee"),
      bulletBold("Geospatial/CityGML specialist: ", "~2-3 months part-time"),
      bulletBold("RL/ML engineer: ", "~4 months dedicated"),
      bulletBold("3D developer: ", "~3 months"),
      bulletBold("NVIDIA compute: ", "Omniverse license (free eval) + GPU cloud ~EUR 2-5K/month"),
      bulletBold("Cesium ion: ", "Free tier for prototype, ~$1K/month for production"),
      spacer(60),
      boldBody("Total Phase 3 estimate: ", "EUR 80,000-150,000 depending on team model (advisory vs. WINNIIO-led)."),
      spacer(60),
      bodyText("Note: Potential AWS MAP program — $100K cash + $100K cloud credits via SI partner. Internal only, not in client-facing materials."),

      // CONFLICT AWARENESS
      heading1("Conflict Awareness"),
      bulletBold("Nokia Bell Labs: ", "WINNIIO works with Nokia BL on Gaussian splatting. Rakuten/Altiostar competes with Nokia in RAN."),
      bulletBold("Mitigation: ", "Position around methodology + orchestration, not splatting technique. Joint Nokia BL IP needs field-of-use check before pitching same technique to Altiostar."),
      bulletBold("AWS: ", "Altiostar uses RCP — don't lead with AWS (signals hyperscaler dependency). Frame: AWS for simulation/dev only, cloud-agnostic for production."),
      bulletBold("Intel: ", "Altiostar RAN runs on Intel COTS. Acknowledge this — it is their core differentiator vs. proprietary ASIC vendors."),
    ]
  }]
});

const outPath = "C:/Users/ceo/OneDrive - Winniio AB/WINNIIO 2026/ALTIO STAR RAKUTEN/WINNIIO_Altiostar_Internal_ProjectPlan.docx";
const fallback = "C:/Users/ceo/WINNIIO_Altiostar_Internal_ProjectPlan.docx";

Packer.toBuffer(doc).then(buffer => {
  try {
    fs.writeFileSync(outPath, buffer);
    console.log(`DONE: ${outPath}`);
  } catch (e) {
    fs.writeFileSync(fallback, buffer);
    console.log(`DONE (fallback): ${fallback}`);
  }
  console.log(`Size: ${(buffer.length / 1024).toFixed(1)} KB`);
});
