"use client";

import Link from "next/link";
import {
  Upload,
  FileText,
  Clock,
  Star,
  ArrowRight,
  BookOpenText,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useReviews } from "@/hooks/use-reviews";
import type { ReviewSummary } from "@/lib/api/types";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const recommendationColor: Record<string, string> = {
  accept: "bg-success/15 text-success border-success/25",
  minor_revision: "bg-amber/15 text-amber border-amber/25",
  major_revision: "bg-warning/15 text-warning border-warning/25",
  reject: "bg-destructive/15 text-destructive border-destructive/25",
};

const recommendationLabel: Record<string, string> = {
  accept: "Accept",
  minor_revision: "Minor Revision",
  major_revision: "Major Revision",
  reject: "Reject",
};

const statusLabel: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  desk_check: "Desk Check",
  reviewing: "Reviewing",
  aggregating: "Aggregating",
};

const ACTIVE_STATUSES = new Set([
  "pending",
  "processing",
  "desk_check",
  "reviewing",
  "aggregating",
]);

function isActive(review: ReviewSummary) {
  return ACTIVE_STATUSES.has(review.status);
}

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
  const { reviews, total, isLoading, error, refetch } = useReviews(0, 50);

  const activeReviews = reviews.filter(isActive);
  const recentReviews = reviews.filter((r) => !isActive(r));

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      {/* ── Hero ── */}
      <Card className="border-primary/15 bg-gradient-to-br from-primary/5 to-accent/5">
        <CardContent className="flex flex-col items-start gap-4 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <h1 className="font-heading text-2xl font-bold tracking-tight">
              Start a new paper review
            </h1>
            <p className="text-muted-foreground">
              Upload your manuscript and receive an AI-powered peer review in
              minutes.
            </p>
          </div>
          <Button asChild size="lg" className="gap-2">
            <Link href="/upload">
              <Upload className="h-4 w-4" />
              Upload Paper
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* ── Error state ── */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={refetch} className="gap-1">
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-8 lg:grid-cols-3">
        {/* ── Left column: reviews ── */}
        <div className="space-y-8 lg:col-span-2">
          {/* Active Reviews */}
          <section>
            <h2 className="font-heading mb-4 text-lg font-semibold">
              Active Reviews
            </h2>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <Card key={i}>
                    <CardContent className="py-4">
                      <div className="space-y-2">
                        <Skeleton className="h-5 w-3/4" />
                        <Skeleton className="h-4 w-1/2" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : activeReviews.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
                  <BookOpenText className="h-10 w-10 opacity-40" />
                  <p>No active reviews. Upload a paper to get started.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {activeReviews.map((review) => (
                  <Card
                    key={review.review_id}
                    className="transition-shadow hover:shadow-md"
                  >
                    <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-1">
                        <p className="truncate font-medium">
                          {review.paper_title ?? "Untitled Paper"}
                        </p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>{review.journal_name ?? "—"}</span>
                          <span>&middot;</span>
                          <Badge variant="secondary" className="text-xs">
                            {statusLabel[review.status] ?? review.status}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/review/${review.review_id}`}>
                            View
                            <ArrowRight className="ml-1 h-3 w-3" />
                          </Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          <Separator />

          {/* Recent Reviews */}
          <section>
            <h2 className="font-heading mb-4 text-lg font-semibold">
              Recent Reviews
            </h2>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Card key={i}>
                    <CardContent className="py-4">
                      <div className="space-y-2">
                        <Skeleton className="h-5 w-3/4" />
                        <Skeleton className="h-4 w-1/2" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : recentReviews.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-2 py-12 text-center text-muted-foreground">
                  <BookOpenText className="h-10 w-10 opacity-40" />
                  <p>No completed reviews yet.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {recentReviews.map((review) => (
                  <Card
                    key={review.review_id}
                    className="transition-shadow hover:shadow-md"
                  >
                    <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-1">
                        <p className="truncate font-medium">
                          {review.paper_title ?? "Untitled Paper"}
                        </p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>{review.journal_name ?? "—"}</span>
                          <span>&middot;</span>
                          <span>{formatDate(review.completed_at ?? review.created_at)}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {review.recommendation && (
                          <Badge
                            variant="outline"
                            className={
                              recommendationColor[review.recommendation] ?? ""
                            }
                          >
                            {recommendationLabel[review.recommendation] ??
                              review.recommendation}
                          </Badge>
                        )}
                        <Badge variant="secondary" className="text-xs">
                          {review.status === "failed" ? "Failed" : review.status === "cancelled" ? "Cancelled" : "Completed"}
                        </Badge>
                        {review.status === "completed" && (
                          <Button variant="ghost" size="sm" asChild>
                            <Link href={`/review/${review.review_id}/report`}>
                              View Report
                            </Link>
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </div>

        {/* ── Right column: metrics ── */}
        <aside className="space-y-4">
          <h2 className="font-heading text-lg font-semibold">Overview</h2>
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total Reviews</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  {isLoading ? (
                    <Skeleton className="h-8 w-12" />
                  ) : (
                    <span className="text-2xl font-bold">{total}</span>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Active</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  {isLoading ? (
                    <Skeleton className="h-8 w-12" />
                  ) : (
                    <span className="text-2xl font-bold">{activeReviews.length}</span>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Completed</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-accent" />
                  {isLoading ? (
                    <Skeleton className="h-8 w-12" />
                  ) : (
                    <span className="text-2xl font-bold">
                      {recentReviews.filter((r) => r.status === "completed").length}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </aside>
      </div>
    </div>
  );
}
