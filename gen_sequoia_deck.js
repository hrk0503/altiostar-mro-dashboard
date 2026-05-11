const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        AlignmentType, BorderStyle, WidthType, ShadingType,
        Header, Footer, PageNumber, PageBreak, PageOrientation,
        SectionType } = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "333333" };
const borders = { top: border, bottom: border, left: border, right: border };
const cm = { top: 50, bottom: 50, left: 80, right: 80 };

function cell(text, opts = {}) {
  return new TableCell({
    borders: opts.noBorder ? { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } } : borders,
    margins: cm,
    width: { size: opts.width || 1000, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Segoe UI", size: opts.size || 18, bold: opts.bold, color: opts.color, italics: opts.italic })],
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { after: 0 },
    })],
  });
}

function title(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Segoe UI", size: 56, bold: true, color: "0077B6" })],
    spacing: { after: 200 },
  });
}

function subtitle(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Segoe UI", size: 28, color: "444444" })],
    spacing: { after: 300 },
  });
}

function bigNum(num, label) {
  return new Paragraph({
    children: [
      new TextRun({ text: num, font: "Segoe UI", size: 72, bold: true, color: "0077B6" }),
      new TextRun({ text: `  ${label}`, font: "Segoe UI", size: 28, color: "555555" }),
    ],
    spacing: { after: 200 },
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Segoe UI", size: opts.size || 24, color: opts.color || "333333", bold: opts.bold, italics: opts.italic })],
    spacing: { after: opts.after || 120 },
    alignment: opts.align,
  });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text: `•  ${text}`, font: "Segoe UI", size: opts.size || 24, color: opts.color || "333333", bold: opts.bold })],
    spacing: { after: opts.after || 100 },
    indent: { left: 400 },
  });
}

function spacer(h) {
  return new Paragraph({ children: [], spacing: { after: h || 200 } });
}

function pb() {
  return new Paragraph({ children: [new PageBreak()] });
}

function slideNum(n) {
  return new Paragraph({
    children: [new TextRun({ text: `${n} / 15`, font: "Segoe UI", size: 16, color: "BBBBBB" })],
    alignment: AlignmentType.RIGHT,
    spacing: { before: 400 },
  });
}

const pageProps = {
  page: {
    size: { width: 12240, height: 15840, orientation: PageOrientation.LANDSCAPE },
    margin: { top: 1000, right: 1200, bottom: 800, left: 1200 },
  },
};

const slides = [];

// ============================================================
// SLIDE 1: TITLE
// ============================================================
slides.push(
  spacer(1500),
  new Paragraph({
    children: [new TextRun({ text: "WINNIIO", font: "Segoe UI", size: 96, bold: true, color: "0077B6" })],
    alignment: AlignmentType.CENTER,
  }),
  spacer(200),
  new Paragraph({
    children: [new TextRun({ text: "Autonomous Physical AI for Open RAN", font: "Segoe UI", size: 36, color: "444444" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 200 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "The digital twin infrastructure layer for the world's wireless networks", font: "Segoe UI", size: 22, color: "888888", italics: true })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 400 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Confidential  |  May 2026", font: "Segoe UI", size: 18, color: "AAAAAA" })],
    alignment: AlignmentType.CENTER,
  }),
  slideNum(1),
);

// ============================================================
// SLIDE 2: PURPOSE
// ============================================================
slides.push(
  pb(),
  title("Company Purpose"),
  spacer(400),
  new Paragraph({
    children: [new TextRun({ text: "We eliminate guesswork from wireless network operations.", font: "Segoe UI", size: 44, bold: true, color: "0077B6" })],
    spacing: { after: 400 },
  }),
  body("WINNIIO creates physics-accurate digital twins of any city's wireless infrastructure — automatically — enabling operators to optimize, predict, and plan their networks without sending a single van.", { size: 26 }),
  spacer(300),
  body("$25/tower/month. Vendor-neutral. Works with any RAN.", { size: 28, bold: true, color: "0077B6" }),
  slideNum(2),
);

// ============================================================
// SLIDE 3: PROBLEM
// ============================================================
slides.push(
  pb(),
  title("The Problem"),
  subtitle("Wireless operators spend $15B/year optimizing networks the way they did in 2005"),
  bigNum("$1,500", "/day per drive-test vehicle"),
  bigNum("50–100", "vehicles per Tier-1 operator, 365 days/year"),
  bigNum("3–5%", "of all calls dropped due to handover failures"),
  spacer(100),
  bullet("5G makes it exponentially worse: 3x tower density, mmWave with 200m range, massive MIMO beam interactions"),
  bullet("RAN engineers manage 200–500 sites using Excel and tribal knowledge — they retire, the knowledge leaves"),
  bullet("Result: $27–55M/year per operator just to measure what's already broken"),
  slideNum(3),
);

// ============================================================
// SLIDE 4: SOLUTION
// ============================================================
slides.push(
  pb(),
  title("The Solution"),
  subtitle("A physics-accurate digital twin that replaces drive testing, predicts coverage, and auto-optimizes the RAN"),
  bullet("Real 3D city geometry — every building, every height, from government open data (PLATEAU, OSM, CityGML)"),
  bullet("GPU ray tracing — radio waves bounce off real surfaces with real materials, not statistical approximations"),
  bullet("Auto-generated — feed it a city name, it builds the twin in hours. Not months of manual setup."),
  bullet("Auto-discovers tower configurations from MDT traces — doesn't need the operator's spreadsheet"),
  bullet("AI optimization grounded in physics — trains on ray-traced simulations, not just historical KPI averages"),
  bullet("Open RAN native — vendor-neutral rApps on any RIC. Not locked to Nokia or Ericsson."),
  spacer(100),
  body("No van. No guy. No Excel. Continuous optimization, 24/7, from anywhere.", { bold: true, size: 26, color: "0077B6" }),
  slideNum(4),
);

// ============================================================
// SLIDE 5: WHY NOW
// ============================================================
slides.push(
  pb(),
  title("Why Now"),
  subtitle("Five forces converging in 2025–2027"),
  spacer(100),
  bullet("Open RAN adoption accelerating — $2.8B (2024) → $20.9B (2030), CAGR 39%. Operators want vendor choice.", { size: 26 }),
  bullet("NVIDIA open-sourced Sionna RT + AODT (Dec 2025) — GPU ray tracing is now free infrastructure, not a barrier.", { size: 26 }),
  bullet("Government 3D building data going global — Japan PLATEAU, EU CityGML, US OpenStreetMap. The geometry layer is free.", { size: 26 }),
  bullet("5G densification creating unsolvable complexity — manual optimization can't scale to millions of small cells.", { size: 26 }),
  bullet("AI-RAN mandate from operators — every Tier-1 has an AI network strategy now. They need the twin to train the AI.", { size: 26 }),
  spacer(100),
  body("The physics engine is free. The building data is free. The demand is mandatory. All that's missing is the integration layer. That's us.", { size: 24, italic: true, color: "555555" }),
  slideNum(5),
);

// ============================================================
// SLIDE 6: PRODUCT — HOW IT WORKS
// ============================================================
slides.push(
  pb(),
  title("How It Works"),
  subtitle("Reality Fabric: automatic digital twin creation from open data"),
  spacer(100),
  new Table({
    width: { size: 12000, type: WidthType.DXA },
    columnWidths: [2400, 2400, 2400, 2400, 2400],
    rows: [
      new TableRow({ children: [
        cell("1. INGEST", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2400, align: AlignmentType.CENTER, size: 16 }),
        cell("2. BUILD", { bold: true, shading: "00897B", color: "FFFFFF", width: 2400, align: AlignmentType.CENTER, size: 16 }),
        cell("3. SIMULATE", { bold: true, shading: "F57C00", color: "FFFFFF", width: 2400, align: AlignmentType.CENTER, size: 16 }),
        cell("4. OPTIMIZE", { bold: true, shading: "E91E63", color: "FFFFFF", width: 2400, align: AlignmentType.CENTER, size: 16 }),
        cell("5. DEPLOY", { bold: true, shading: "7B1FA2", color: "FFFFFF", width: 2400, align: AlignmentType.CENTER, size: 16 }),
      ]}),
      new TableRow({ children: [
        cell("Pull 3D buildings, terrain, tower registries, spectrum data from open sources", { width: 2400, size: 14 }),
        cell("Auto-generate physics-accurate 3D twin of the city with all RF elements", { width: 2400, size: 14 }),
        cell("GPU ray-trace coverage. Predict signal strength at every point. Detect holes.", { width: 2400, size: 14 }),
        cell("AI tunes HO parameters, tilt, power, CIO per cell pair per hour. Continuously.", { width: 2400, size: 14 }),
        cell("Push optimized config to RIC via O-RAN APIs. Closed-loop automation.", { width: 2400, size: 14 }),
      ]}),
    ],
  }),
  spacer(200),
  body("Time from city name to live twin: hours, not months.", { bold: true, size: 24, color: "0077B6" }),
  body("Nokia/Ericsson require months of manual setup, professional services, and their own RAN hardware.", { size: 22, color: "666666" }),
  slideNum(6),
);

// ============================================================
// SLIDE 7: PRODUCT — DEMO
// ============================================================
slides.push(
  pb(),
  title("Product Demo"),
  subtitle("Tokyo MRO Digital Twin — live CesiumJS application"),
  spacer(100),
  bullet("21 towers with full sector configuration (azimuth, tilt, power, CIO, neighbor relations)"),
  bullet("PLATEAU LOD2 3D buildings — real Tokyo geometry tinted by signal strength via GPU CustomShader"),
  bullet("Sionna RT coverage — ray-traced propagation per band (n77/n78/n257) with real building obstruction"),
  bullet("1,000 simulated UE traces — pedestrians, trains, vehicles with handover events and failure detection"),
  bullet("Antenna beam visualization, coverage hole detection, handover boundary mapping"),
  bullet("First-person exploration — walk/fly through the network at street level"),
  bullet("Drag-and-drop import — operators can drop their own CSV/GeoJSON propagation data"),
  spacer(100),
  body("Live at localhost:8787. Deployable to any CDN as a single HTML file.", { size: 22, color: "888888", italic: true }),
  slideNum(7),
);

// ============================================================
// SLIDE 8: MARKET SIZE
// ============================================================
slides.push(
  pb(),
  title("Market Size"),
  spacer(100),
  new Table({
    width: { size: 10000, type: WidthType.DXA },
    columnWidths: [3000, 2000, 2000, 3000],
    rows: [
      new TableRow({ children: [
        cell("", { noBorder: true, width: 3000 }),
        cell("Towers", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2000, align: AlignmentType.CENTER }),
        cell("ARR at $25/mo", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2000, align: AlignmentType.CENTER }),
        cell("Segment", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3000 }),
      ]}),
      ...([
        ["SOM (Year 3)", "200K", "$60M", "Japan + 2 early adopters"],
        ["SAM", "1.5M", "$450M", "Top 20 global operators + tower cos"],
        ["TAM", "10M", "$3B", "All cell towers globally"],
      ].map((row, i) => new TableRow({ children: [
        cell(row[0], { bold: true, width: 3000, size: 20, color: "0077B6", noBorder: true }),
        cell(row[1], { width: 2000, align: AlignmentType.CENTER, size: 20 }),
        cell(row[2], { width: 2000, align: AlignmentType.CENTER, size: 20, bold: true, color: "00897B" }),
        cell(row[3], { width: 3000, size: 18, color: "666666" }),
      ]}))),
    ],
  }),
  spacer(200),
  body("Adjacent markets built on the platform:", { bold: true, size: 22 }),
  bullet("Private 5G planning-as-a-service: $100M+"),
  bullet("Spectrum marketplace / twin-validated trading: $1B+"),
  bullet("Tower company analytics (American Tower, Cellnex): $300M+"),
  bullet("Autonomous vehicle corridor certification: $500M+"),
  spacer(100),
  body("Telecom Network Digital Twin market: $2.7B (2026) → $5.9B (2031), CAGR 16.6%", { size: 20, color: "888888", italic: true }),
  slideNum(8),
);

// ============================================================
// SLIDE 9: COMPETITION
// ============================================================
slides.push(
  pb(),
  title("Competition"),
  subtitle("Nobody combines all capabilities. The market is fragmented by design."),
  spacer(50),
  new Table({
    width: { size: 12000, type: WidthType.DXA },
    columnWidths: [2000, 1200, 1200, 1200, 1200, 1200, 1200, 1200, 1200],
    rows: [
      new TableRow({ children: [
        cell("", { shading: "1A1A2E", color: "FFFFFF", width: 2000, size: 12 }),
        ...["WINNIIO","AirHop","Nokia","Ericsson","NVIDIA","VIAVI","Cellwize","Amdocs"].map((c,i) =>
          cell(c, { bold: true, shading: i===0?"00897B":"1A1A2E", color: "FFFFFF", width: 1200, align: AlignmentType.CENTER, size: 11 })),
      ]}),
      ...[
        ["3D Digital Twin",1,0,1,0,1,1,0,0],
        ["Ray Tracing",1,0,1,0,1,1,0,0],
        ["MRO/SON",1,1,1,1,0,0,1,1],
        ["Open RAN native",1,1,0,0,0,0,1,1],
        ["Auto DT creation",1,0,0,0,0,0,0,0],
        ["Auto config discovery",1,0,0,0,0,0,0,0],
        ["Physical AI",1,0,1,0,1,1,0,0],
        ["Vendor-neutral",1,1,0,0,1,0,1,1],
        ["Pricing",0,0,0,0,0,0,0,0],
      ].map((row, fi) => {
        if (fi === 8) {
          return new TableRow({ children: [
            cell("$/site/month", { bold: true, width: 2000, size: 12, shading: "F5F5F5" }),
            ...["$25","$30-80","$150-400","$100-300","$50-200","$200-500","$50-150","$50-150"].map((p,i) =>
              cell(p, { width: 1200, align: AlignmentType.CENTER, size: 11, bold: i===0, color: i===0?"00897B":undefined, shading: "F5F5F5" })),
          ]});
        }
        return new TableRow({ children: [
          cell(row[0], { bold: true, width: 2000, size: 12, shading: fi%2===0?"F0F7FA":undefined }),
          ...row.slice(1).map((v, ci) => cell(v?"✓":"–", {
            width: 1200, align: AlignmentType.CENTER,
            color: v?"00897B":"CCCCCC", bold: !!v, size: 14,
            shading: fi%2===0?"F0F7FA":undefined,
          })),
        ]});
      }),
    ],
  }),
  spacer(100),
  body("Nokia is the only 8/10 competitor — but requires Nokia RAN. For Open RAN operators, that's a non-starter.", { size: 20, italic: true, color: "666666" }),
  slideNum(9),
);

// ============================================================
// SLIDE 10: BUSINESS MODEL
// ============================================================
slides.push(
  pb(),
  title("Business Model"),
  subtitle("$25/tower/month — all inclusive"),
  spacer(200),
  new Table({
    width: { size: 10000, type: WidthType.DXA },
    columnWidths: [3500, 1500, 1500, 3500],
    rows: [
      new TableRow({ children: [
        cell("Customer", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3500, size: 16 }),
        cell("Towers", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, align: AlignmentType.CENTER, size: 16 }),
        cell("ARR", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, align: AlignmentType.CENTER, size: 16 }),
        cell("vs. Current Spend", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3500, size: 16 }),
      ]}),
      ...([
        ["Rakuten Japan", "45K", "$13.5M", "Replaces $30M+ drive testing → ROI month 1"],
        ["Tier-1 (e.g. DT, Vodafone)", "100K", "$30M", "vs. $55M+ drive test budget"],
        ["Tower company (e.g. Cellnex)", "50K", "$15M", "New revenue: RF analytics for tenants"],
        ["Regulator (e.g. MIC Japan)", "400K", "$120M", "Coverage verification, spectrum audit"],
      ].map((row, i) => new TableRow({ children: [
        cell(row[0], { bold: true, width: 3500, size: 16, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[1], { width: 1500, align: AlignmentType.CENTER, size: 16, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[2], { width: 1500, align: AlignmentType.CENTER, size: 16, bold: true, color: "00897B", shading: i%2===0?"F0F7FA":undefined }),
        cell(row[3], { width: 3500, size: 15, color: "555555", shading: i%2===0?"F0F7FA":undefined }),
      ]}))),
    ],
  }),
  spacer(200),
  body("Gross margins: 85%+ (software-only, no hardware). Infrastructure cost: GPU compute + CDN.", { size: 22 }),
  body("Expansion: platform fees on third-party rApps that query the Reality Fabric API (marketplace take rate).", { size: 22, color: "555555" }),
  slideNum(10),
);

// ============================================================
// SLIDE 11: GO-TO-MARKET
// ============================================================
slides.push(
  pb(),
  title("Go-to-Market"),
  subtitle("The trojan horse: $25/tower demo → platform lock-in"),
  spacer(100),
  new Table({
    width: { size: 12000, type: WidthType.DXA },
    columnWidths: [1500, 2500, 3000, 2500, 2500],
    rows: [
      new TableRow({ children: [
        cell("Phase", { bold: true, shading: "0077B6", color: "FFFFFF", width: 1500, size: 14 }),
        cell("Action", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2500, size: 14 }),
        cell("Target", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3000, size: 14 }),
        cell("Revenue", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2500, align: AlignmentType.CENTER, size: 14 }),
        cell("Timeline", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2500, align: AlignmentType.CENTER, size: 14 }),
      ]}),
      ...([
        ["1. Prove", "Workshop + POC", "Altiostar / Rakuten Symphony", "EUR 25K pilot", "Q2-Q3 2026"],
        ["2. Land", "City-scale deployment", "Rakuten Japan (Tokyo, Osaka)", "$2-5M ARR", "Q4 2026"],
        ["3. Expand", "Multi-market rollout", "Rakuten + 2 more Open RAN ops", "$10-15M ARR", "2027"],
        ["4. Platform", "Reality Fabric API launch", "rApp developers, tower cos, regulators", "$30-60M ARR", "2028"],
      ].map((row, i) => new TableRow({ children: [
        cell(row[0], { bold: true, width: 1500, size: 14, color: "0077B6", shading: i%2===0?"F0F7FA":undefined }),
        cell(row[1], { width: 2500, size: 14, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[2], { width: 3000, size: 14, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[3], { width: 2500, align: AlignmentType.CENTER, size: 14, bold: true, color: "00897B", shading: i%2===0?"F0F7FA":undefined }),
        cell(row[4], { width: 2500, align: AlignmentType.CENTER, size: 14, shading: i%2===0?"F0F7FA":undefined }),
      ]}))),
    ],
  }),
  spacer(200),
  body("First customer is already engaged: Altiostar/Rakuten Symphony pre-workshop call scheduled week of May 5, 2026.", { bold: true, size: 22 }),
  slideNum(11),
);

// ============================================================
// SLIDE 12: KEYSTONE ADVANTAGE
// ============================================================
slides.push(
  pb(),
  title("The Keystone Advantage"),
  subtitle("WINNIIO as infrastructure — the AWS of wireless network intelligence"),
  spacer(100),
  bullet("Creates more value than it captures — $25/site enables $100s of operator savings", { size: 24 }),
  bullet("Makes the ecosystem healthier — rApp devs get spatial awareness, RAN vendors get validation, operators get choice", { size: 24 }),
  bullet("Becomes hard to remove — once the twin is the system of record for RF reality, every player depends on it", { size: 24 }),
  bullet("Network effects compound — more operators = more MDT data = better physics AI = better twin = more operators", { size: 24 }),
  spacer(150),
  body("The Moat Stack:", { bold: true, size: 24, color: "0077B6" }),
  bullet("Data gravity — years of RF history don't transfer to competitors"),
  bullet("Reality Fabric API — third-party rApps build on our spatial API. Switching = rewriting their apps."),
  bullet("Physics accuracy compounds — ray tracing improves with every building update. Statistics don't compound."),
  bullet("Multi-operator insight — cross-network interference data nobody else has"),
  bullet("Global auto-generation — any city in hours. Competitors need months. Speed = market capture."),
  slideNum(12),
);

// ============================================================
// SLIDE 13: KPIs / IMPACT
// ============================================================
slides.push(
  pb(),
  title("Operator Impact"),
  subtitle("Measured outcomes at $25/tower/month"),
  spacer(100),
  new Table({
    width: { size: 10000, type: WidthType.DXA },
    columnWidths: [3000, 2000, 2000, 3000],
    rows: [
      new TableRow({ children: [
        cell("Metric", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3000, size: 16 }),
        cell("Before", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2000, align: AlignmentType.CENTER, size: 16 }),
        cell("After", { bold: true, shading: "0077B6", color: "FFFFFF", width: 2000, align: AlignmentType.CENTER, size: 16 }),
        cell("Impact", { bold: true, shading: "0077B6", color: "FFFFFF", width: 3000, align: AlignmentType.CENTER, size: 16 }),
      ]}),
      ...([
        ["Drive test cost", "$27–55M/yr", "Near zero", "95% reduction"],
        ["HO failure rate", "3–5%", "<1%", "$200–600M LTV saved"],
        ["Site deployment time", "6–8 weeks", "2–3 weeks", "60% faster"],
        ["Coverage hole detection", "Quarterly", "Real-time", "90x faster"],
        ["RAN engineer productivity", "300 sites/person", "3,000 sites", "10x leverage"],
        ["Energy optimization", "Manual", "Automated", "15–20% OPEX cut"],
        ["Failed deployments", "15–20%", "<3%", "$50–80K saved/site"],
      ].map((row, i) => new TableRow({ children: [
        cell(row[0], { bold: true, width: 3000, size: 16, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[1], { width: 2000, align: AlignmentType.CENTER, size: 16, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[2], { width: 2000, align: AlignmentType.CENTER, size: 16, shading: i%2===0?"F0F7FA":undefined }),
        cell(row[3], { width: 3000, align: AlignmentType.CENTER, size: 16, bold: true, color: "00897B", shading: i%2===0?"F0F7FA":undefined }),
      ]}))),
    ],
  }),
  slideNum(13),
);

// ============================================================
// SLIDE 14: TEAM
// ============================================================
slides.push(
  pb(),
  title("Team"),
  spacer(200),
  body("Nicolas Waern — Founder & CEO", { bold: true, size: 28, color: "0077B6" }),
  bullet("15+ years in digital twins, AI, and enterprise architecture"),
  bullet("Co-chair, industry working groups with Fortune 500 CTOs (AstraZeneca, NTT Data, Ansys)"),
  bullet("Built Life Atlas — sovereign digital twin platform spanning health, manufacturing, telecom"),
  bullet("EU Expert Evaluator (Horizon Europe), published researcher (ORCID), patent holder"),
  bullet("Network: Rakuten/Altiostar (Soumyadeep Mukherjee), Nokia Bell Labs (Ryo Koblitz), Ansys (Marc Horner)"),
  spacer(200),
  body("Advisory Network", { bold: true, size: 24, color: "0077B6" }),
  bullet("Doug Kiehl — 31 yrs Eli Lilly, USP standards, Purdue. Regulatory strategy."),
  bullet("Jurgen Steinbacher — NTT Data Germany, ex-Kuka robotics. Manufacturing DT."),
  bullet("DPella AB — differential privacy (Chalmers/BU spinout). Data sovereignty."),
  spacer(100),
  body("Hiring: CTO (RAN/telecom domain), VP Sales (telecom enterprise), ML Engineer (Sionna/ray tracing)", { size: 20, color: "888888", italic: true }),
  slideNum(14),
);

// ============================================================
// SLIDE 15: THE ASK
// ============================================================
slides.push(
  pb(),
  title("The Ask"),
  spacer(200),
  new Paragraph({
    children: [new TextRun({ text: "EUR 1.5–2.5M Pre-Seed SAFE", font: "Segoe UI", size: 44, bold: true, color: "0077B6" })],
    spacing: { after: 300 },
  }),
  body("Use of funds (18 months):", { bold: true, size: 24 }),
  spacer(50),
  bullet("40% — Engineering: CTO hire, ML engineer, Sionna RT pipeline, Reality Fabric API productization", { size: 22 }),
  bullet("25% — Go-to-market: Rakuten POC delivery, 2 additional operator pilots, telecom sales hire", { size: 22 }),
  bullet("20% — Infrastructure: GPU compute (NVIDIA A100/H100), CDN, global building data pipeline", { size: 22 }),
  bullet("15% — Operations: legal (IP/patents), regulatory certifications, working capital", { size: 22 }),
  spacer(200),
  body("Milestones this capital unlocks:", { bold: true, size: 24 }),
  bullet("Rakuten Japan pilot live (Q3 2026)"),
  bullet("2 additional operator LOIs (Q4 2026)"),
  bullet("$2-5M ARR run rate (Q1 2027)"),
  bullet("Series A ready at $15-25M valuation"),
  spacer(200),
  new Paragraph({
    children: [new TextRun({ text: "$25/tower/month is the trojan horse. The platform is the castle.", font: "Segoe UI", size: 28, bold: true, color: "0077B6", italics: true })],
    alignment: AlignmentType.CENTER,
  }),
  spacer(100),
  new Paragraph({
    children: [new TextRun({ text: "nicolas@winniio.io  |  winniio.io", font: "Segoe UI", size: 20, color: "888888" })],
    alignment: AlignmentType.CENTER,
  }),
  slideNum(15),
);

const doc = new Document({
  styles: { default: { document: { run: { font: "Segoe UI", size: 24 } } } },
  sections: [{
    properties: pageProps,
    children: slides,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = "C:/Users/ceo/OneDrive/WINNIIO_Sequoia_Deck_May2026.docx";
  fs.writeFileSync(out, buf);
  console.log("Saved:", out, `(${(buf.length/1024).toFixed(0)} KB)`);
});
