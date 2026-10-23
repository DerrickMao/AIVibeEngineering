const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const { FaSitemap, FaProjectDiagram, FaSyncAlt, FaChartLine } = require("react-icons/fa");
const { applyTheme } = require("/root/.claude/skills/synced/b902f260-a8cc-4b15-a220-995a60c3abdc_46a34f03-e23b-4c56-bfec-6cd39f513e7e/pptx/scripts/apply_theme.js");

const THEME = {
  name: "INF Financial Agent",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: "0F1B3D", lt1: "FFFFFF", dk2: "4A5578", lt2: "F2F5FB",
    accent1: "2F6BFF", accent2: "EE0000", accent3: "8FB3FF",
    accent4: "1D3478", accent5: "5B6B8F", accent6: "00B3A4",
    hlink: "2F6BFF", folHlink: "5B6B8F",
  },
};

async function icon(Comp, color) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: 256 }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "AI Solution - Financial Agents on Red Hat OpenShift";
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "TITLE_ONLY",
    background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.4, w: 8, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 3, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.7, w: 12.1, h: 0.7, fontSize: 34, bold: true, color: C.text1, margin: 0, valign: "middle", align: "left" }, text: "" } },
      { placeholder: { options: { name: "subtitle", type: "body", x: 0.6, y: 1.42, w: 12.1, h: 0.5, fontSize: 15, color: C.text2, margin: 0, valign: "top" }, text: "" } },
    ],
  });

  pres.addSection({ title: "AI Solution" });
  const s = pres.addSlide({ masterName: "TITLE_ONLY", sectionTitle: "AI Solution" });
  s.addText("AI SOLUTION", { placeholder: "kicker" });
  s.addText("Financial Agents on Red Hat OpenShift", { placeholder: "title" });
  s.addText("Financial expertise from INF Managed Agent, cloud-native delivery from OpenShift", { placeholder: "subtitle" });

  // ---------- Left: architecture panel ----------
  const PX = 0.6, PY = 2.25, PW = 6.1, PH = 4.65;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: PX, y: PY, w: PW, h: PH, rectRadius: 0.12, fill: { color: C.text1 }, line: { type: "none" }, objectName: "Architecture panel" });
  const IX = PX + 0.2, IW = PW - 0.4;

  s.addText("BUSINESS SCENARIOS", { x: IX, y: PY + 0.2, w: IW, h: 0.3, fontSize: 11, bold: true, color: C.accent3, charSpacing: 2, margin: 0, isTextBox: true });
  const chips = [["Compliance & Risk", 1.55], ["KYC", 0.65], ["Credit Analysis", 1.35], ["Wealth Management", 1.65]];
  const gap = (IW - chips.reduce((a, c) => a + c[1], 0)) / (chips.length - 1);
  let cx = IX;
  for (const [label, w] of chips) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: PY + 0.58, w, h: 0.42, rectRadius: 0.21, fill: { color: C.background1, transparency: 88 }, line: { color: C.accent3, width: 0.75 }, objectName: "Chip " + label });
    s.addText(label, { x: cx, y: PY + 0.58, w, h: 0.42, fontSize: 11, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    cx += w + gap;
  }

  // layer blocks
  function layer(y, fill, name, items, subColor) {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: IX, y, w: IW, h: 1.3, rectRadius: 0.08, fill: { color: fill }, line: { type: "none" }, objectName: name + " layer" });
    s.addText(name, { x: IX + 0.2, y: y + 0.14, w: IW - 0.4, h: 0.38, fontSize: 17, bold: true, color: C.background1, margin: 0, isTextBox: true });
    const n = items.length, g = 0.12, w = (IW - 0.4 - g * (n - 1)) / n;
    items.forEach((t, i) => {
      const x = IX + 0.2 + i * (w + g);
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: y + 0.62, w, h: 0.5, rectRadius: 0.06, fill: { color: C.background1, transparency: 82 }, line: { type: "none" }, objectName: name + " - " + t });
      s.addText(t, { x, y: y + 0.62, w, h: 0.5, fontSize: 11, color: subColor, align: "center", valign: "middle", margin: 0.05, isTextBox: true });
    });
  }
  const L1 = PY + 1.3, L2 = L1 + 1.3 + 0.35;
  // connector arrow from scenarios to agent layer
  s.addShape(pres.shapes.DOWN_ARROW, { x: PX + PW / 2 - 0.12, y: PY + 1.06, w: 0.24, h: 0.2, fill: { color: C.accent3 }, line: { type: "none" }, objectName: "Arrow down" });
  layer(L1, C.accent1, "INF Managed Agent", ["Financial Knowledge", "Task Orchestration", "Continuous Optimization"], C.background1);
  s.addText("+", { x: PX + PW / 2 - 0.2, y: L1 + 1.3, w: 0.4, h: 0.35, fontSize: 20, bold: true, color: C.accent3, align: "center", valign: "middle", margin: 0, isTextBox: true });
  layer(L2, C.accent2, "Red Hat OpenShift", ["Containerized Deployment", "Elastic Scaling", "Hybrid Cloud Management"], C.background1);

  s.addText("\u2192  Faster deployment & iteration, continuously upgraded financial AI", { x: IX, y: L2 + 1.38, w: IW, h: 0.28, fontSize: 12, bold: true, color: C.accent3, margin: 0, isTextBox: true });

  // ---------- Right: key advantages ----------
  const RX = 7.1, RW = 13.333 - 0.6 - RX;
  s.addText("KEY ADVANTAGES", { x: RX, y: PY, w: RW, h: 0.3, fontSize: 11, bold: true, color: C.accent1, charSpacing: 2, margin: 0, isTextBox: true });
  const adv = [
    [FaSitemap, "Financial Ontology", "Unified knowledge of financial entities, concepts, relations and business rules"],
    [FaProjectDiagram, "Controllable Workflow", "Configurable, traceable steps with rule guardrails and human review"],
    [FaSyncAlt, "Feedback Loop", "Benchmarks, case reviews and human feedback refine knowledge, prompts and flows"],
    [FaChartLine, "Continuous Improvement", "Ongoing evaluation and version regression for accuracy, efficiency and stability"],
  ];
  const top = PY + 0.45, rowGap = 0.12, rowH = (PY + PH - top - rowGap * 3) / 4;
  for (let i = 0; i < adv.length; i++) {
    const [Ic, t, d] = adv[i];
    const y = top + i * (rowH + rowGap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: RX, y, w: RW, h: rowH, rectRadius: 0.08, fill: { color: C.background2 }, line: { type: "none" }, objectName: "Advantage card " + (i + 1) });
    s.addShape(pres.shapes.OVAL, { x: RX + 0.2, y: y + (rowH - 0.56) / 2, w: 0.56, h: 0.56, fill: { color: C.accent1 }, line: { type: "none" }, objectName: "Icon circle " + (i + 1) });
    s.addImage({ data: await icon(Ic, "FFFFFF"), x: RX + 0.34, y: y + (rowH - 0.28) / 2, w: 0.28, h: 0.28, altText: t + " icon" });
    s.addText([
      { text: t, options: { fontSize: 15, bold: true, color: C.text1, breakLine: true } },
      { text: d, options: { fontSize: 12, color: C.text2 } },
    ], { x: RX + 0.95, y: y + 0.08, w: RW - 1.1, h: rowH - 0.16, valign: "middle", margin: 0, paraSpaceAfter: 2, isTextBox: true });
  }

  await pres.writeFile({ fileName: "INF_Financial_Agent_OpenShift.pptx" });
  await applyTheme("INF_Financial_Agent_OpenShift.pptx", THEME);
  console.log("done");
})();
