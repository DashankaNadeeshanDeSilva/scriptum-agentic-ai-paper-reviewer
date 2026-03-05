"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Download,
  MessageSquare,
  Star,
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api, ApiError } from "@/lib/api/client";
import type { ReviewReportResponse, FeedbackRequest } from "@/lib/api/types";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const recBadge: Record<string, { label: string; className: string }> = {
  accept: { label: "Accept", className: "bg-success/15 text-success border-success/25" },
  minor_revision: { label: "Minor Revision", className: "bg-amber/15 text-amber border-amber/25" },
  major_revision: { label: "Major Revision", className: "bg-warning/15 text-warning border-warning/25" },
  reject: { label: "Reject", className: "bg-destructive/15 text-destructive border-destructive/25" },
};

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  // Report data
  const [data, setData] = useState<ReviewReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.get<ReviewReportResponse>(`/reviews/${id}/report`);
      setData(resp);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load report");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Feedback dialog
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComments, setFeedbackComments] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  async function handleFeedbackSubmit() {
    setIsSubmittingFeedback(true);
    try {
      const payload: FeedbackRequest = {
        rating: feedbackRating,
        comments: feedbackComments || null,
      };
      await api.post(`/reviews/${id}/feedback`, payload);
      setFeedbackSubmitted(true);
      setFeedbackOpen(false);
    } catch {
      // silently fail, user can retry
    } finally {
      setIsSubmittingFeedback(false);
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 space-y-6">
        <Skeleton className="h-6 w-32" />
        <Card>
          <CardContent className="py-8 space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <div className="grid gap-4 md:grid-cols-2">
              <Skeleton className="h-32" />
              <Skeleton className="h-32" />
            </div>
          </CardContent>
        </Card>
        <Skeleton className="h-48" />
      </div>
    );
  }

  // Error state
  if (error || !data) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error ?? "Report not available"}</span>
            <Button variant="ghost" size="sm" onClick={fetchReport} className="gap-1">
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const report = data.report;
  const rec = recBadge[report.recommendation] ?? {
    label: report.recommendation,
    className: "",
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Back link */}
      <Link
        href={`/review/${id}`}
        className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to progress
      </Link>

      {/* ── Executive Summary ── */}
      <Card className="mb-8">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="font-heading text-xl">
              Review Report
            </CardTitle>
            <Badge variant="outline" className={rec.className + " text-sm px-3 py-1"}>
              {rec.label}
            </Badge>
          </div>
          <CardDescription>
            Confidence: <span className="font-medium capitalize">{report.confidence}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 md:grid-cols-2">
          {/* Strengths */}
          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-success">
              <ThumbsUp className="h-4 w-4" />
              Key Strengths
            </h3>
            <ul className="space-y-1.5 text-sm">
              {report.key_strengths.map((s, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-success" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
          {/* Weaknesses */}
          <div>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-destructive">
              <ThumbsDown className="h-4 w-4" />
              Key Weaknesses
            </h3>
            <ul className="space-y-1.5 text-sm">
              {report.key_weaknesses.map((w, i) => (
                <li key={i} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-destructive" />
                  {w}
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* ── Scores ── */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Category</TableHead>
                <TableHead className="text-center">Score</TableHead>
                {report.individual_reviews.map((r) => (
                  <TableHead key={r.reviewer_type} className="text-center capitalize">
                    {r.reviewer_type.replace(/_/g, " ")}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.scores.map((s) => (
                <TableRow key={s.category}>
                  <TableCell className="font-medium">{s.category}</TableCell>
                  <TableCell className="text-center">
                    <Tooltip>
                      <TooltipTrigger>
                        <span className="font-semibold">
                          {s.score.toFixed(1)}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>Aggregated from {report.individual_reviews.length} reviewers</TooltipContent>
                    </Tooltip>
                  </TableCell>
                  {report.individual_reviews.map((r) => (
                    <TableCell key={r.reviewer_type} className="text-center text-muted-foreground">
                      {s.reviewer_scores[r.reviewer_type]?.toFixed(1) ?? "—"}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* ── Tabbed content ── */}
      <Tabs defaultValue="feedback" className="mb-8">
        <TabsList>
          <TabsTrigger value="feedback">Detailed Feedback</TabsTrigger>
          <TabsTrigger value="individual">Individual Reviews</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
        </TabsList>

        <TabsContent value="feedback" className="mt-4">
          <Accordion type="multiple" defaultValue={Object.keys(report.detailed_feedback).slice(0, 1)}>
            {Object.entries(report.detailed_feedback).map(([category, content]) => (
              <AccordionItem key={category} value={category}>
                <AccordionTrigger className="text-sm font-medium capitalize">
                  {category.replace(/_/g, " ")}
                </AccordionTrigger>
                <AccordionContent className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {content}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </TabsContent>

        <TabsContent value="individual" className="mt-4 space-y-4">
          {report.individual_reviews.map((reviewer) => (
            <Card key={reviewer.reviewer_type}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm capitalize">
                  {reviewer.reviewer_type.replace(/_/g, " ")}
                </CardTitle>
                <CardDescription>
                  Recommendation:{" "}
                  <Badge variant="outline" className="text-xs">
                    {reviewer.recommendation}
                  </Badge>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {reviewer.strengths.length > 0 && (
                  <div>
                    <h4 className="mb-1 font-medium text-success">Strengths</h4>
                    <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                      {reviewer.strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {reviewer.weaknesses.length > 0 && (
                  <div>
                    <h4 className="mb-1 font-medium text-destructive">Weaknesses</h4>
                    <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                      {reviewer.weaknesses.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {Object.entries(reviewer.feedback).length > 0 && (
                  <div>
                    <h4 className="mb-1 font-medium">Detailed Feedback</h4>
                    {Object.entries(reviewer.feedback).map(([cat, text]) => (
                      <div key={cat} className="mb-2">
                        <span className="font-medium capitalize">{cat.replace(/_/g, " ")}:</span>
                        <p className="mt-0.5 text-muted-foreground whitespace-pre-wrap">{text}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="evidence" className="mt-4 space-y-4">
          {report.individual_reviews.some((r) => r.evidence.length > 0) ? (
            report.individual_reviews
              .filter((r) => r.evidence.length > 0)
              .map((reviewer) => (
                <Card key={reviewer.reviewer_type}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm capitalize">
                      {reviewer.reviewer_type.replace(/_/g, " ")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    <ul className="space-y-2">
                      {reviewer.evidence.map((ev, i) => (
                        <li key={i} className="rounded border p-2">
                          <pre className="whitespace-pre-wrap text-xs">
                            {JSON.stringify(ev, null, 2)}
                          </pre>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              ))
          ) : (
            <Card>
              <CardContent className="py-6 text-center text-sm text-muted-foreground">
                No evidence citations available for this review.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* ── Suggested Improvements ── */}
      {report.suggested_improvements.length > 0 && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-base">Suggested Improvements</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal space-y-2 pl-5 text-sm">
              {report.suggested_improvements.map((imp, i) => (
                <li key={i}>{imp}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      {/* ── Actions ── */}
      <div className="flex flex-wrap items-center gap-3">
        <Dialog open={feedbackOpen} onOpenChange={setFeedbackOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              className="gap-2"
              disabled={feedbackSubmitted}
            >
              <Star className="h-4 w-4" />
              {feedbackSubmitted ? "Feedback Submitted" : "Submit Feedback"}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Rate this review</DialogTitle>
              <DialogDescription>
                Your feedback helps us improve the review quality.
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-center gap-2 py-4">
              {[1, 2, 3, 4, 5].map((n) => (
                <Button
                  key={n}
                  variant={n <= feedbackRating ? "default" : "outline"}
                  size="icon"
                  onClick={() => setFeedbackRating(n)}
                >
                  <Star className="h-5 w-5" />
                </Button>
              ))}
            </div>
            <textarea
              className="w-full rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              placeholder="Optional comments…"
              value={feedbackComments}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFeedbackComments(e.target.value)}
              rows={3}
            />
            <DialogFooter>
              <Button
                onClick={handleFeedbackSubmit}
                disabled={feedbackRating === 0 || isSubmittingFeedback}
              >
                {isSubmittingFeedback && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
                Submit
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Button asChild className="ml-auto gap-2">
          <Link href="/upload">Start New Review</Link>
        </Button>
      </div>
    </div>
  );
}
