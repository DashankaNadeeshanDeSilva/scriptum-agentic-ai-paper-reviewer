import type { ReviewReport } from "@/lib/api/types";

const REC_LABEL: Record<string, string> = {
  accept: "Accept",
  minor_revision: "Minor Revision",
  major_revision: "Major Revision",
  reject: "Reject",
};

/**
 * Build a printable HTML document from a ReviewReport.
 * Exported for testing.
 */
export function buildReportHtml(report: ReviewReport): string {
  const scoresRows = report.scores
    .map(
      (s) =>
        `<tr><td>${esc(s.category)}</td><td style="text-align:center;font-weight:bold">${s.score.toFixed(1)}</td></tr>`,
    )
    .join("");

  const strengths = report.key_strengths.map((s) => `<li>${esc(s)}</li>`).join("");
  const weaknesses = report.key_weaknesses.map((w) => `<li>${esc(w)}</li>`).join("");

  const feedbackSections = Object.entries(report.detailed_feedback)
    .map(
      ([cat, text]) =>
        `<h3 style="text-transform:capitalize">${esc(cat.replace(/_/g, " "))}</h3><p>${esc(text)}</p>`,
    )
    .join("");

  const improvements = report.suggested_improvements
    .map((imp) => `<li>${esc(imp)}</li>`)
    .join("");

  return `<!DOCTYPE html>
<html>
<head>
  <title>SCRIPTUM Review Report</title>
  <style>
    body { font-family: Georgia, serif; max-width: 800px; margin: 0 auto; padding: 40px; color: #1a1a1a; line-height: 1.6; }
    h1 { font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 8px; }
    h2 { font-size: 18px; margin-top: 24px; color: #333; }
    h3 { font-size: 14px; margin-top: 16px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }
    th { background: #f5f5f5; }
    ul, ol { padding-left: 20px; }
    li { margin-bottom: 4px; font-size: 14px; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; font-size: 14px; background: #f0f0f0; }
    .meta { color: #666; font-size: 13px; }
    @media print { body { padding: 20px; } }
  </style>
</head>
<body>
  <h1>SCRIPTUM Review Report</h1>
  <p class="meta">Review ID: ${esc(report.review_id)} | Generated: ${new Date(report.created_at).toLocaleDateString()}</p>
  <p><span class="badge">${esc(REC_LABEL[report.recommendation] ?? report.recommendation)}</span>
     &nbsp; Confidence: ${esc(report.confidence)}</p>

  <h2>Executive Summary</h2>
  <div style="display:flex;gap:32px">
    <div style="flex:1"><h3>Key Strengths</h3><ul>${strengths}</ul></div>
    <div style="flex:1"><h3>Key Weaknesses</h3><ul>${weaknesses}</ul></div>
  </div>

  <h2>Scores</h2>
  <table><thead><tr><th>Category</th><th style="text-align:center">Score</th></tr></thead><tbody>${scoresRows}</tbody></table>

  <h2>Detailed Feedback</h2>
  ${feedbackSections}

  ${improvements ? `<h2>Suggested Improvements</h2><ol>${improvements}</ol>` : ""}
</body>
</html>`;
}

/**
 * Open a print-ready window with the formatted report.
 * The user can save as PDF via the browser's print dialog.
 */
export function exportReportAsPdf(report: ReviewReport): void {
  const html = buildReportHtml(report);
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    alert("Please allow pop-ups to export the report as PDF.");
    return;
  }
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.onload = () => {
    printWindow.print();
  };
}

/** Escape HTML entities to prevent XSS in generated report. */
function esc(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
