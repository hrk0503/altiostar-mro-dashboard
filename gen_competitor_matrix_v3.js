const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType,
        Header, Footer, PageNumber, PageBreak, PageOrientation } = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cm = { top: 40, bottom: 40, left: 70, right: 70 };

function cell(text, opts = {}) {
  return new TableCell({
    borders, margins: cm,
    width: { size: opts.width || 1000, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Segoe UI", size: opts.size || 15, bold: opts.bold, color: opts.color, italics: opts.italic })],
      alignment: opts.align || AlignmentType.LEFT,
    })],
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    children: Array.isArray(text)
      ? text.map(t => new TextRun({ ...t, font: "Segoe UI", size: t.size || 20 }))
      : [new TextRun({ text, font: "Segoe UI", size: opts.size || 20, bold: opts.bold, color: opts.color, italics: opts.italic })],
    spacing: { after: opts.after !== undefined ? opts.after : 100, before: opts.before || 0 },
    alignment: opts.align,
  });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text: `•  ${text}`, font: "Segoe UI", size: opts.size || 20, bold: opts.bold, color: opts.color })],
    spacing: { after: 60 },
    indent: { left: 360 },
  });
}

function subBullet(text) {
  return new Paragraph({
    children: [new TextRun({ text: `–  ${text}`, font: "Segoe UI", size: 18, color: "555555" })],
    spacing: { after: 40 },
    indent: { left: 720 },
  });
}

// === PAGE 1: POSITIONING ===

function positioningPage() {
  return [
    p("Autonomous Physical AI for Open RAN", { bold: true, size: 40, color: "0077B6", after: 30 }),
    p("WINNIIO  |  Altiostar / Rakuten Symphony", { size: 24, color: "444444", after: 15 }),
    p("The arms dealer model: sell the twin to any operator, any RAN vendor, any market. $25/tower/month.", { size: 18, color: "888888", italic: true, after: 200 }),

    p("Category Definition", { bold: true, size: 26, color: "0077B6", after: 120 }),
    p("WINNIIO operates at the intersection of three spaces no competitor occupies together:", { after: 100 }),

    // 5 pillars table
    new Table({
      width: { size: 10000, type: WidthType.DXA },
      columnWidths: [2000, 8000],
      rows: [
        new TableRow({ children: [
          cell("Pillar", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2000, size: 14 }),
          cell("What It Means", { bold: true, shading: "0077B6", color: "FFFFFF", width: 8000, size: 14 }),
        ]}),
        ...[
          ["Open RAN Native", "Vendor-neutral, O-RAN RIC compliant. Works with Altiostar, Mavenir, any disaggregated RAN. Not locked to Nokia or Ericsson hardware. Lives on the RIC as rApps/xApps."],
          ["AI-RAN", "AI/ML optimization on the RIC (MRO, MLB, energy, anomaly detection) — but grounded in physics, not just statistical regression on historical KPIs."],
          ["True Digital Twin", "Real geometry (PLATEAU/CityGML/OSM), real propagation (GPU ray tracing via Sionna), real building materials. Not a dashboard with charts. A physics-accurate replica of the RF environment."],
          ["Reality Fabric", "Automatic DT creation from open data globally. Feed it a city → it pulls buildings, terrain, tower registries, spectrum allocations, weather, and generates the twin in hours. Nokia needs months of manual setup per market."],
          ["Physical AI", "LQMs over LLMs. AI trains on physics simulations (ray tracing, diffraction, reflection), not just CDR averages. Auto-discovers tower configurations from MDT + coverage patterns. Doesn't need the operator's config spreadsheet."],
        ].map((row, i) => new TableRow({ children: [
          cell(row[0], { bold: true, width: 2000, size: 14, color: "0077B6", shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[1], { width: 8000, size: 14, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
        ]})),
      ],
    }),

    p("", { after: 150 }),
    p("Why Nobody Else Occupies This Intersection", { bold: true, size: 24, color: "0077B6", after: 100 }),
    bullet("Nokia has Physical AI but is vendor-locked — won't work with Altiostar's Open RAN"),
    bullet("NVIDIA has the physics engine (Sionna/AODT) but no RAN operations layer — platform, not product"),
    bullet("AirHop has the RAN ops (MRO/MLB rApps) but zero spatial awareness — no DT, no ray tracing"),
    bullet("Ericsson has everything but won't share — closed ecosystem, won't optimize a competitor's RAN"),
    bullet("VIAVI has the DT + ray tracing but is test/measurement — not operational optimization"),
    bullet("Cellwize/Qualcomm has scale (3M sites) but is pure automation — no physics, no spatial intelligence"),

    p("", { after: 80 }),
    p([
      { text: "WINNIIO = ", size: 22, bold: true, color: "0077B6" },
      { text: "the only vendor-neutral, physics-based, auto-generating digital twin for Open RAN. ", size: 22, bold: true },
      { text: "At $25/tower/month — 4-16x cheaper than anyone scoring above 5/10 on capabilities.", size: 22 },
    ], { after: 0 }),
  ];
}

// === PAGE 2: COMPETITOR TABLE ===

const classData = [
  ["WINNIIO", "Autonomous Physical AI", "$25", "Pre-revenue (demo)", "0%", "New entrant", "10/10"],
  ["NVIDIA (AODT)", "TRUE DT (platform)", "$50–200 (est.)", "Partners deploy", "N/A", "Infra layer", "5/10"],
  ["Nokia RAN DT", "TRUE DT (locked)", "$150–400 (bundled)", "~2M sites", "~20%", "High", "9/10"],
  ["VIAVI", "TRUE DT (test)", "$200–500 (est.)", "<50K live sites", "<1%", "Niche", "6/10"],
  ["Siradel", "TRUE DT (planning)", "Project $100K–$1M", "100+ city models", "<1%", "Niche", "4/10"],
  ["Ericsson", "Hybrid (locked)", "$100–300 (bundled)", "~3.5M sites", "~35%", "Dominant", "7/10"],
  ["Amdocs", "Hybrid", "$50–150 (est.)", "350+ ops (RAN new)", "<1%", "Growing", "6/10"],
  ["AirHop", "AI/ML only", "$30–80 (est.)", "1.5M+ cells", "~15%", "Strong", "4/10"],
  ["Cellwize (QCOM)", "AI/ML only", "$50–150 (est.)", "3M sites, 40 ops", "~30%", "Dominant", "4/10"],
  ["Rimedo Labs", "AI/ML only", "$10–30 (est.)", "Pilot <5K sites", "<0.1%", "Early", "3/10"],
  ["DeepSig", "AI/ML only", "$20–50 (est.)", "DoD, <1K comm.", "<0.1%", "Early", "2/10"],
  ["Mavenir", "AI/ML only", "Bundled w/ RAN", "2 Tier-1 ops", "<1%", "Niche", "3/10"],
  ["Cohere Tech", "AI/ML only", "$15–40 (est.)", "Pilots only", "<0.1%", "Early", "1/10"],
  ["Forsk (Atoll)", "Legacy planning", "$50K–200K/seat/yr", "500+ operators", "~50% (plan)", "Legacy", "1/10"],
  ["Infovista (TEMS)", "Legacy test", "$20K–100K/device", "300+ operators", "~40% (test)", "Legacy", "1/10"],
];

const classW = [1400, 1600, 1200, 1500, 800, 900, 700];

function classRows() {
  const rows = [];
  rows.push(new TableRow({ children: [
    cell("Company", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[0], size: 13 }),
    cell("Category", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[1], align: AlignmentType.CENTER, size: 13 }),
    cell("$/Site/Mo", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[2], align: AlignmentType.CENTER, size: 13 }),
    cell("Deployment", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[3], align: AlignmentType.CENTER, size: 13 }),
    cell("Mkt %", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[4], align: AlignmentType.CENTER, size: 13 }),
    cell("Status", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[5], align: AlignmentType.CENTER, size: 13 }),
    cell("Score", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: classW[6], align: AlignmentType.CENTER, size: 13 }),
  ]}));
  classData.forEach((row, i) => {
    const isW = row[0] === "WINNIIO";
    const shade = isW ? "E0F2F1" : i % 2 === 0 ? "FAFAFA" : undefined;
    const scoreNum = parseInt(row[6]);
    const scoreColor = scoreNum >= 8 ? "00897B" : scoreNum >= 5 ? "F57C00" : "B0BEC5";
    rows.push(new TableRow({ children: [
      cell(row[0], { bold: true, width: classW[0], shading: shade, size: 13, color: isW ? "0077B6" : undefined }),
      cell(row[1], { width: classW[1], align: AlignmentType.CENTER, shading: shade, size: 12, bold: isW, color: isW ? "00897B" : undefined }),
      cell(row[2], { width: classW[2], align: AlignmentType.CENTER, shading: shade, size: 13, bold: isW, color: isW ? "00897B" : undefined }),
      cell(row[3], { width: classW[3], align: AlignmentType.CENTER, shading: shade, size: 12 }),
      cell(row[4], { width: classW[4], align: AlignmentType.CENTER, shading: shade, size: 12 }),
      cell(row[5], { width: classW[5], align: AlignmentType.CENTER, shading: shade, size: 12 }),
      cell(row[6], { width: classW[6], align: AlignmentType.CENTER, shading: shade, size: 14, bold: true, color: scoreColor }),
    ]}));
  });
  return rows;
}

// === PAGE 3: FEATURE MATRIX ===

const features = [
  "3D City Digital Twin", "Ray Tracing (physics)", "MRO/SON automation",
  "MDT / drive test replace", "Open RAN / RIC native", "AI/ML optimization",
  "Coverage prediction", "HO parameter tuning", "Energy management", "Real-time 3D viz",
  "Auto DT creation", "Auto config discovery", "Global (any city)", "Physical AI (not stats)", "Vendor-neutral"
];
const companies = ["WINNIIO", "AirHop", "Nokia", "VIAVI", "Ericsson", "NVIDIA", "Amdocs", "Cellwize"];
const matrix = [
  [1,0,1,1,0,1,0,0], // 3D DT
  [1,0,1,1,0,1,0,0], // Ray trace
  [1,1,1,0,1,0,1,1], // MRO
  [1,0,1,1,1,0,0,0], // MDT
  [1,1,0,0,0,0,1,1], // Open RAN
  [1,1,1,1,1,1,1,1], // AI/ML
  [1,0,1,1,1,1,0,0], // Coverage
  [1,1,1,0,1,0,1,1], // HO
  [1,1,1,0,1,0,1,0], // Energy
  [1,0,1,1,0,1,1,0], // Viz
  [1,0,0,0,0,0,0,0], // Auto DT creation
  [1,0,0,0,0,0,0,0], // Auto config
  [1,0,0,0,0,1,0,0], // Global
  [1,0,1,1,0,1,0,0], // Physical AI
  [1,1,0,0,0,1,1,1], // Vendor neutral
];
const scores = companies.map((_, ci) => matrix.reduce((s, row) => s + row[ci], 0));

const fColW = [2200, 900, 900, 900, 900, 900, 900, 900, 900];

function featureRows() {
  const rows = [];
  rows.push(new TableRow({ children: [
    cell("Capability", { bold: true, shading: "0077B6", color: "FFFFFF", width: fColW[0], size: 13 }),
    ...companies.map((c, i) => cell(c, { bold: true, shading: i === 0 ? "00897B" : "0077B6", color: "FFFFFF", width: fColW[i+1], align: AlignmentType.CENTER, size: 12 })),
  ]}));
  features.forEach((feat, fi) => {
    const isNew = fi >= 10;
    rows.push(new TableRow({ children: [
      cell(isNew ? `★ ${feat}` : feat, { bold: true, width: fColW[0], size: 13, shading: fi % 2 === 0 ? "F0F7FA" : undefined, color: isNew ? "0077B6" : undefined }),
      ...companies.map((_, ci) => {
        const val = matrix[fi][ci];
        const txt = val === 1 ? "✓" : "–";
        const color = val === 1 ? "00897B" : "CCCCCC";
        return cell(txt, { width: fColW[ci+1], align: AlignmentType.CENTER, color, bold: val === 1, size: 16, shading: fi % 2 === 0 ? "F0F7FA" : undefined });
      }),
    ]}));
  });
  rows.push(new TableRow({ children: [
    cell("SCORE", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: fColW[0], size: 14 }),
    ...scores.map((s, i) => cell(`${s}/15`, { bold: true, shading: "1A1A2E", color: s >= 12 ? "00E676" : s >= 7 ? "FFD54F" : "FF8A80", width: fColW[i+1], align: AlignmentType.CENTER, size: 14 })),
  ]}));
  return rows;
}

// === PAGE 4: REVENUE ===

function revenuePage() {
  return [
    p("Revenue at Scale", { bold: true, size: 26, color: "0077B6", after: 120 }),
    new Table({
      width: { size: 8000, type: WidthType.DXA },
      columnWidths: [3500, 1500, 1500, 1500],
      rows: [
        new TableRow({ children: [
          cell("Scenario", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3500, size: 14 }),
          cell("Towers", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, align: AlignmentType.CENTER, size: 14 }),
          cell("$/Month", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, align: AlignmentType.CENTER, size: 14 }),
          cell("$/Year", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, align: AlignmentType.CENTER, size: 14 }),
        ]}),
        ...([
          ["Rakuten Japan", "45K", "$1.1M", "$13.5M"],
          ["Single Tier-1 operator", "100K", "$2.5M", "$30M"],
          ["Japan total", "400K", "$10M", "$120M"],
          ["Top 10 global operators", "1.5M", "$37.5M", "$450M"],
          ["Global TAM (all towers)", "10M", "$250M", "$3B"],
        ].map((row, i) => new TableRow({ children: [
          cell(row[0], { bold: true, width: 3500, size: 14, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[1], { width: 1500, align: AlignmentType.CENTER, size: 14, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[2], { width: 1500, align: AlignmentType.CENTER, size: 14, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[3], { width: 1500, align: AlignmentType.CENTER, size: 14, bold: true, color: "00897B", shading: i % 2 === 0 ? "F0F7FA" : undefined }),
        ]}))),
      ],
    }),

    p("", { after: 120 }),
    p("vs. Operator Current Spend", { bold: true, size: 22, color: "0077B6", after: 80 }),
    bullet("Drive testing: $27–55M/year per Tier-1 → WINNIIO replaces at $30M/year with 10x more data"),
    bullet("ROI: month 1. Payback: <90 days."),
    bullet("Energy savings alone (15–20% OPEX) typically exceeds the $25/site/mo cost"),

    p("", { after: 120 }),
    p("Platform Economics (what gets built on top)", { bold: true, size: 22, color: "0077B6", after: 80 }),
    bullet("Network-as-a-Service planning — enterprise private 5G simulation ($100M+ vertical)"),
    bullet("Insurance/SLA verification — digital coverage evidence ($200M+ vertical)"),
    bullet("Urban planning integration — RF impact in construction permits ($100M+ vertical)"),
    bullet("Autonomous vehicle corridors — certified continuous coverage ($500M+ vertical)"),
    bullet("Spectrum marketplace — twin-validated spectrum trading ($1B+ vertical)"),
    bullet("Tower company analytics — valuation and M&A for American Tower/Cellnex ($300M+ vertical)"),
  ];
}

// === PAGE 5: KEYSTONE ADVANTAGE ===

function keystonePage() {
  return [
    p("The Keystone Advantage", { bold: true, size: 32, color: "0077B6", after: 20 }),
    p("WINNIIO as the keystone species in the Open RAN ecosystem", { size: 20, color: "666666", italic: true, after: 150 }),

    p("Marketplace Position", { bold: true, size: 26, color: "0077B6", after: 100 }),
    p("The Open RAN ecosystem has three tiers of players. WINNIIO sits at the center:", { after: 80 }),

    new Table({
      width: { size: 10000, type: WidthType.DXA },
      columnWidths: [1800, 2200, 3000, 3000],
      rows: [
        new TableRow({ children: [
          cell("Tier", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: 1800, size: 14 }),
          cell("Players", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: 2200, size: 14 }),
          cell("What They Need", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: 3000, size: 14 }),
          cell("What WINNIIO Provides", { bold: true, shading: "1A1A2E", color: "FFFFFF", width: 3000, size: 14 }),
        ]}),
        ...([
          ["RAN Hardware", "Altiostar, Mavenir, Samsung, Fujitsu", "Proof their RAN works in real environments. Optimization that shows their hardware outperforms Nokia/Ericsson.", "Vendor-neutral DT that validates and optimizes their hardware. Marketing weapon: 'proven in digital twin.'"],
          ["RIC / SMO", "Amdocs, Juniper, VMware (Broadcom)", "Killer apps for their platform. rApps that drive adoption of their RIC.", "Physics-grounded rApps that are 10x better than statistical-only apps. The 'must-have' rApp suite."],
          ["rApp / xApp Devs", "AirHop, Rimedo, Cohere, DeepSig", "Spatial awareness they can't build themselves. Real RF environment data to train their AI.", "The Reality Fabric API. Third-party rApps query WINNIIO's twin for building data, coverage maps, propagation predictions."],
          ["Operators", "Rakuten, DISH, 1&1, Jio", "Vendor-neutral optimization. No more lock-in to Nokia/Ericsson. Operational cost reduction.", "$25/site/mo all-inclusive. Works with any RAN. 4-16x cheaper than incumbents. ROI in month 1."],
          ["Tower Companies", "American Tower, Cellnex, SBA, Crown Castle", "Asset valuation. RF performance data for M&A. Optimization proof for tenants.", "Twin-as-a-Service for portfolio valuation. Continuous coverage quality scoring per asset."],
          ["Regulators / Cities", "MIC Japan, FCC, Ofcom, municipalities", "Coverage verification. Spectrum efficiency evidence. Environmental impact assessment.", "Auditable, physics-based coverage maps. Digital evidence for spectrum compliance."],
        ].map((row, i) => new TableRow({ children: [
          cell(row[0], { bold: true, width: 1800, size: 13, color: "0077B6", shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[1], { width: 2200, size: 12, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[2], { width: 3000, size: 12, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[3], { width: 3000, size: 12, bold: true, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
        ]}))),
      ],
    }),

    p("", { after: 150 }),
    p("Why Keystone, Not Dominator", { bold: true, size: 24, color: "0077B6", after: 100 }),
    p("Nokia and Ericsson are dominators — they capture most of the value and crowd out the ecosystem. WINNIIO is a keystone:", { after: 80 }),

    bullet("Creates more value than it captures — $25/site/mo enables $100s of savings, not $100s of cost", { bold: true }),
    bullet("Makes the entire ecosystem healthier — rApp devs build better apps, RAN vendors prove their hardware, operators get vendor choice"),
    bullet("Becomes hard to remove — once the twin is the system of record for RF reality, every player depends on it"),
    bullet("Network effects compound — more operators = more MDT data = better AI = better twin = more operators"),

    p("", { after: 120 }),
    p("The Moat Stack", { bold: true, size: 24, color: "0077B6", after: 100 }),

    new Table({
      width: { size: 8000, type: WidthType.DXA },
      columnWidths: [2500, 5500],
      rows: [
        new TableRow({ children: [
          cell("Moat Layer", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2500, size: 14 }),
          cell("Why It Compounds", { bold: true, shading: "0077B6", color: "FFFFFF", width: 5500, size: 14 }),
        ]}),
        ...([
          ["Data gravity", "Every MDT trace, every coverage measurement, every HO event accumulates in the twin. Moving to a competitor means losing years of RF history."],
          ["Reality Fabric API", "Third-party rApps build on our spatial API. Switching cost = rewriting their apps. We become the 'S3 of RF data.'"],
          ["Physics accuracy", "Ray tracing improves with every building update, every material classification, every calibration. Statistical models don't compound — physics does."],
          ["Multi-operator insight", "Serving multiple operators in the same city gives us cross-network interference data nobody else has. Regulatory gold."],
          ["Global coverage", "Auto-DT creation means we can spin up any city in hours. Competitors need months of manual setup. Speed = market capture."],
          ["Ecosystem lock-in", "When AirHop/Rimedo/Cohere build rApps that query our twin, WINNIIO becomes infrastructure. Infrastructure doesn't get replaced."],
        ].map((row, i) => new TableRow({ children: [
          cell(row[0], { bold: true, width: 2500, size: 13, color: "0077B6", shading: i % 2 === 0 ? "F0F7FA" : undefined }),
          cell(row[1], { width: 5500, size: 13, shading: i % 2 === 0 ? "F0F7FA" : undefined }),
        ]}))),
      ],
    }),

    p("", { after: 120 }),
    p([
      { text: "End state: ", size: 22, bold: true, color: "0077B6" },
      { text: "WINNIIO is to Open RAN what AWS is to cloud — the invisible infrastructure layer that everything else runs on. ", size: 22 },
      { text: "$25/tower/month is the trojan horse. The platform is the castle.", size: 22, bold: true },
    ]),
  ];
}

const doc = new Document({
  styles: { default: { document: { run: { font: "Segoe UI", size: 20 } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE },
        margin: { top: 800, right: 800, bottom: 800, left: 800 },
      },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        children: [
          new TextRun({ text: "WINNIIO  ", font: "Segoe UI", size: 16, bold: true, color: "0077B6" }),
          new TextRun({ text: "|  Autonomous Physical AI for Open RAN  |  Competitive Landscape  |  Confidential", font: "Segoe UI", size: 14, color: "888888" }),
        ],
        border: { bottom: { style: BorderStyle.SINGLE, size: 3, color: "0077B6", space: 4 } },
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        children: [
          new TextRun({ text: "Pricing marked (est.) = industry estimates. Not confirmed. | Page ", font: "Segoe UI", size: 12, color: "AAAAAA" }),
          new TextRun({ children: [PageNumber.CURRENT], font: "Segoe UI", size: 12, color: "AAAAAA" }),
        ],
        alignment: AlignmentType.RIGHT,
      })] }),
    },
    children: [
      // Page 1: Positioning
      ...positioningPage(),

      new Paragraph({ children: [new PageBreak()] }),

      // Page 2: Competitor table
      p("Competitor Matrix — Pricing & Market Penetration", { bold: true, size: 26, color: "0077B6", after: 20 }),
      p("Market: Telecom Network DT $2.7B (2026) → $5.9B (2031) | Open RAN Automation $700M by 2027", { size: 16, color: "888888", after: 100 }),
      new Table({ width: { size: 8100, type: WidthType.DXA }, columnWidths: classW, rows: classRows() }),

      new Paragraph({ children: [new PageBreak()] }),

      // Page 3: Feature matrix (expanded to 15)
      p("Feature Matrix — 15 Capabilities (★ = WINNIIO differentiators)", { bold: true, size: 26, color: "0077B6", after: 100 }),
      new Table({ width: { size: 9400, type: WidthType.DXA }, columnWidths: fColW, rows: featureRows() }),

      new Paragraph({ children: [new PageBreak()] }),

      // Page 4: Revenue
      ...revenuePage(),

      new Paragraph({ children: [new PageBreak()] }),

      // Page 5: Keystone Advantage
      ...keystonePage(),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = "C:/Users/ceo/OneDrive/Altiostar_Competitive_Landscape.docx";
  fs.writeFileSync(out, buf);
  console.log("Saved:", out, `(${(buf.length/1024).toFixed(0)} KB)`);
});
