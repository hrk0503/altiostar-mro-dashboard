const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        Header, Footer, PageNumber, PageBreak } = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "444444" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function p(text, opts = {}) {
  const runs = [];
  if (typeof text === "string") {
    runs.push(new TextRun({ text, bold: opts.bold, italics: opts.italic, size: opts.size || 22, font: "Segoe UI", color: opts.color }));
  } else {
    text.forEach(t => runs.push(new TextRun({ ...t, font: "Segoe UI", size: t.size || 22 })));
  }
  return new Paragraph({
    children: runs,
    spacing: { after: opts.after !== undefined ? opts.after : 120, before: opts.before || 0 },
    alignment: opts.align,
    heading: opts.heading,
  });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text: `•  ${text}`, font: "Segoe UI", size: opts.size || 22, color: opts.color })],
    spacing: { after: 80 },
    indent: { left: 360 },
  });
}

function stageNote(text) {
  return p(text, { italic: true, color: "666666", size: 20, after: 60 });
}

function sectionTitle(text) {
  return p(text, { bold: true, size: 32, color: "0077B6", before: 300, after: 160 });
}

function cell(text, opts = {}) {
  return new TableCell({
    borders,
    margins: cellMargins,
    width: { size: opts.width || 1337, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    children: [new Paragraph({
      children: [new TextRun({ text, font: "Segoe UI", size: 20, bold: opts.bold, color: opts.color })],
      alignment: opts.align,
    })],
  });
}

const colWidths = [2200, 1800, 1800, 1800, 1760];

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Segoe UI", size: 22 } } },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1200, right: 1200, bottom: 1200, left: 1200 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "WINNIIO  ", font: "Segoe UI", size: 18, bold: true, color: "0077B6" }),
            new TextRun({ text: "|  Altiostar / Rakuten Symphony  |  Tokyo MRO Digital Twin  |  Demo Script", font: "Segoe UI", size: 16, color: "888888" }),
          ],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "0077B6", space: 6 } },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "Confidential  |  ", font: "Segoe UI", size: 16, color: "AAAAAA" }),
            new TextRun({ text: "Page ", font: "Segoe UI", size: 16, color: "AAAAAA" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Segoe UI", size: 16, color: "AAAAAA" }),
          ],
          alignment: AlignmentType.RIGHT,
        })],
      }),
    },
    children: [
      // TITLE
      p("Tokyo MRO Digital Twin", { bold: true, size: 48, color: "0077B6", after: 40 }),
      p("Demo Script & Value Proposition", { size: 28, color: "444444", after: 40 }),
      p("Altiostar / Rakuten Symphony Pre-Workshop", { size: 24, color: "888888", after: 300 }),

      // === SECTION 1 ===
      sectionTitle("THE WORLD TODAY"),
      stageNote("(Orbit view, towers visible)"),

      p([
        { text: "Right now, every operator in the world optimizes their network the same way they did in 2005. ", size: 22 },
        { text: "They send a guy in a van with an antenna on the roof. Drive testing.", size: 22, bold: true },
      ], { after: 160 }),

      bullet("$1,500/day per vehicle, per market"),
      bullet("A Tier-1 operator runs 50–100 vehicles, 365 days/year — that’s $27–55M/year just to measure what’s already broken"),
      bullet("Handover failures cause 3–5% of all dropped calls. Each dropped call is a churn signal. A 1% churn reduction on 100M subscribers at $50 ARPU = $600M lifetime value saved"),
      bullet("5G makes it worse: 3x tower density, mmWave with 200m range, massive MIMO beams that interact in ways nobody can predict from a spreadsheet"),
      bullet("The average RAN engineer manages 200–500 sites using Excel and tribal knowledge. They retire, the knowledge walks out the door"),

      p(""),
      p([
        { text: "The industry spends ", size: 22 },
        { text: "$15B/year", size: 22, bold: true },
        { text: " on RAN optimization globally. Most of it is manual.", size: 22 },
      ], { after: 200 }),

      // === SECTION 2 ===
      sectionTitle("THE WORLD TOMORROW"),
      stageNote("(Toggle Sionna RT ON — buildings glow green/yellow/red)"),

      p([
        { text: "This is what we replace it with. ", size: 22 },
        { text: "Every building in Tokyo — real geometry, real heights, from Japan’s PLATEAU open data — tinted by signal strength.", size: 22, bold: true },
        { text: " Not a heatmap on a flat map. A living digital twin.", size: 22 },
      ], { after: 160 }),

      stageNote("(Click a tower)"),
      bullet("Every tower: sectors, tilt, power, CIO, neighbor relations — all queryable"),
      stageNote("(Toggle UE Traces)"),
      bullet("1,000 simulated device journeys — pedestrians, trains, vehicles — with handover events, failures, ping-pong detection"),
      stageNote("(Toggle Beams)"),
      bullet("Antenna beam sectors visualized in 3D at actual height and azimuth"),
      stageNote("(Toggle Coverage Holes)"),
      bullet("Coverage holes detected automatically, not by a guy driving past"),
      stageNote("(Fly mode into street level)"),
      bullet("Walk through the network at street level. See what the subscriber sees"),

      p(""),
      p("No van. No guy. No Excel. Continuous optimization, 24/7, from anywhere.", { bold: true, after: 200 }),

      // === SECTION 3 ===
      new Paragraph({ children: [new PageBreak()] }),
      sectionTitle("THE WORLD IN 5 YEARS"),
      stageNote("(Overview, all layers on)"),

      p("In 5 years, no operator will deploy a single small cell without simulating it first in a twin like this.", { after: 160 }),

      bullet("Pre-deployment: Ray-trace coverage before you mount the antenna. Save $50–80K per failed site"),
      bullet("Continuous MDT: Every device is a sensor. Millions of traces per day, not 50 vans"),
      bullet("AI-driven MRO: Handover parameters auto-tuned per cell pair, per hour, per traffic pattern"),
      bullet("Spectrum planning: Simulate n77 vs n78 vs n257 deployment scenarios in minutes, not months"),
      bullet("Energy optimization: Identify towers to power-down during low traffic — 15–20% energy savings"),
      bullet("Open RAN native: Altiostar’s disaggregated architecture means the twin talks directly to the RIC"),

      p(""),
      p("This becomes the operating system for the RAN.", { bold: true, after: 200 }),

      // === KPI TABLE ===
      sectionTitle("KPIs & ROI"),
      stageNote("(Pause on overview)"),
      p(""),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: colWidths,
        rows: [
          new TableRow({
            children: [
              cell("Metric", { bold: true, shading: "0077B6", color: "FFFFFF", width: colWidths[0] }),
              cell("Before", { bold: true, shading: "0077B6", color: "FFFFFF", width: colWidths[1], align: AlignmentType.CENTER }),
              cell("After", { bold: true, shading: "0077B6", color: "FFFFFF", width: colWidths[2], align: AlignmentType.CENTER }),
              cell("Impact", { bold: true, shading: "0077B6", color: "FFFFFF", width: colWidths[3], align: AlignmentType.CENTER }),
            ],
          }),
          ...([
            ["Drive test cost", "$27–55M/yr", "Near zero", "95% reduction"],
            ["HO failure rate", "3–5%", "<1%", "$200–600M LTV saved"],
            ["Site deployment", "6–8 weeks", "2–3 weeks", "60% faster"],
            ["Coverage hole detection", "Quarterly", "Real-time", "90x faster"],
            ["RAN engineer productivity", "300 sites/person", "3,000 sites/person", "10x"],
            ["Energy optimization", "Manual/none", "Automated", "15–20% OPEX cut"],
            ["Failed site deployments", "15–20%", "<3%", "$50–80K saved/site"],
          ].map((row, i) => new TableRow({
            children: row.map((val, j) => cell(val, {
              width: colWidths[j],
              bold: j === 0,
              shading: i % 2 === 0 ? "F0F7FA" : undefined,
              align: j > 0 ? AlignmentType.CENTER : undefined,
            })),
          }))),
        ],
      }),

      // === THE MATH ===
      p(""),
      sectionTitle("THE MATH"),
      stageNote("(Land the pricing)"),

      p([
        { text: "We charge ", size: 24 },
        { text: "$25/tower/month", size: 28, bold: true, color: "0077B6" },
        { text: ". That’s it.", size: 24 },
      ], { after: 160 }),

      bullet("Rakuten Japan, ~45K towers: $13.5M/year"),
      bullet("A Tier-1 with 100K towers: $30M/year — against $55M+ in drive tests alone. ROI in month one."),
      bullet("Japan total (~400K towers): $120M/year"),
      bullet("Global TAM (~10M towers): $3B/year"),

      p(""),
      p("Payback period: under 90 days. Not a cost center — a profit center from day one.", { bold: true, after: 200 }),

      // === PLATFORM ===
      sectionTitle("WHAT GETS BUILT ON TOP"),

      p("Once the twin exists, it’s a platform. These companies get built:", { after: 160 }),

      bullet("Network-as-a-Service planning — enterprise customers simulate their own private 5G coverage"),
      bullet("Insurance/SLA verification — prove coverage commitments with digital evidence, not contracts"),
      bullet("Urban planning integration — city planners see RF impact before approving construction permits"),
      bullet("Autonomous vehicle corridors — certify continuous coverage along specific routes"),
      bullet("Emergency services — first responders see real-time coverage during disasters"),
      bullet("Spectrum marketplace — buy/sell/lease spectrum based on verified digital twin valuations"),
      bullet("Tower company analytics — American Tower, SBA, Cellnex use twins for valuation and M&A"),

      p(""),
      p([
        { text: "Each of those is a ", size: 22 },
        { text: "$100M–$1B", size: 22, bold: true },
        { text: " vertical built on our platform layer.", size: 22 },
      ], { after: 200 }),

      // === CLOSE ===
      sectionTitle("CLOSE"),

      p([
        { text: "We’re not selling software. We’re selling the elimination of guesswork from a $15B/year problem. At $25/tower/month, the question isn’t whether you can afford this. ", size: 22 },
        { text: "It’s whether you can afford to keep sending vans.", size: 24, bold: true, color: "0077B6" },
      ]),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = "C:/Users/ceo/OneDrive/Altiostar_Tokyo_MRO_Demo_Script.docx";
  fs.writeFileSync(out, buf);
  console.log("Saved:", out, `(${(buf.length/1024).toFixed(0)} KB)`);
});
