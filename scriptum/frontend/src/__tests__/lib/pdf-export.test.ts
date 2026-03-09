import { describe, it, expect } from "vitest";
import { buildReportHtml } from "@/lib/pdf-export";
import type { ReviewReport } from "@/lib/api/types";

const mockReport: ReviewReport = {
  review_id: "test-123",
  recommendation: "minor_revision",
  confidence: "high",
  key_strengths: ["Strong methodology", "Clear writing"],
  key_weaknesses: ["Missing references", "Weak conclusion"],
  scores: [
    { category: "Originality", score: 7.5, reviewer_scores: {} },
    { category: "Clarity", score: 8.0, reviewer_scores: {} },
  ],
  detailed_feedback: {
    methodology: "The methodology is sound.",
    related_work: "Needs more citations.",
  },
  suggested_improvements: ["Add more references", "Strengthen conclusion"],
  individual_reviews: [],
  desk_check: null,
  created_at: "2026-03-06T00:00:00Z",
};

describe("buildReportHtml", () => {
  it("contains all report sections", () => {
    const html = buildReportHtml(mockReport);

    // Title
    expect(html).toContain("SCRIPTUM Review Report");
    // Review ID
    expect(html).toContain("test-123");
    // Recommendation
    expect(html).toContain("Minor Revision");
    // Confidence
    expect(html).toContain("high");
    // Strengths
    expect(html).toContain("Strong methodology");
    expect(html).toContain("Clear writing");
    // Weaknesses
    expect(html).toContain("Missing references");
    expect(html).toContain("Weak conclusion");
    // Scores
    expect(html).toContain("Originality");
    expect(html).toContain("7.5");
    expect(html).toContain("Clarity");
    expect(html).toContain("8.0");
    // Detailed feedback
    expect(html).toContain("methodology");
    expect(html).toContain("The methodology is sound.");
    // Improvements
    expect(html).toContain("Add more references");
    expect(html).toContain("Strengthen conclusion");
    // Valid HTML
    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("</html>");
  });

  it("escapes HTML entities to prevent XSS", () => {
    const xssReport: ReviewReport = {
      ...mockReport,
      key_strengths: ['<script>alert("xss")</script>'],
    };
    const html = buildReportHtml(xssReport);

    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
  });
});
