import Link from "next/link";
import {
  Upload,
  FileText,
  Clock,
  Star,
  ArrowRight,
  BookOpenText,
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

/* ------------------------------------------------------------------ */
/*  Mock data — replaced by API calls in Phase 4                      */
/* ------------------------------------------------------------------ */

const activeReviews = [
  {
    id: "r-001",
    title: "Attention Mechanisms in Low-Resource NLP",
    journal: "ACL 2025",
    status: "reviewing",
    progress: 62,
  },
  {
    id: "r-002",
    title: "Diffusion Models for Molecular Generation",
    journal: "Nature Machine Intelligence",
    status: "desk_check",
    progress: 18,
  },
];

const recentReviews = [
  {
    id: "r-100",
    title: "Graph Neural Networks for Drug Discovery",
    journal: "NeurIPS 2024",
    recommendation: "minor_revision",
    date: "2025-02-20",
  },
  {
    id: "r-101",
    title: "Federated Learning with Differential Privacy",
    journal: "IEEE TIFS",
    recommendation: "accept",
    date: "2025-02-18",
  },
  {
    id: "r-102",
    title: "Reinforcement Learning for Autonomous Driving",
    journal: "AAAI 2025",
    recommendation: "major_revision",
    date: "2025-02-15",
  },
];

const metrics = { total: 12, avgTime: "18 min", satisfaction: 4.2 };

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
  desk_check: "Desk Check",
  reviewing: "Reviewing",
  aggregating: "Aggregating",
  processing: "Processing",
};

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function DashboardPage() {
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

      <div className="grid gap-8 lg:grid-cols-3">
        {/* ── Left column: reviews ── */}
        <div className="space-y-8 lg:col-span-2">
          {/* Active Reviews */}
          <section>
            <h2 className="font-heading mb-4 text-lg font-semibold">
              Active Reviews
            </h2>
            {activeReviews.length === 0 ? (
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
                    key={review.id}
                    className="transition-shadow hover:shadow-md"
                  >
                    <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0 flex-1 space-y-1">
                        <p className="truncate font-medium">{review.title}</p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span>{review.journal}</span>
                          <span>&middot;</span>
                          <Badge variant="secondary" className="text-xs">
                            {statusLabel[review.status] ?? review.status}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="w-32 space-y-1">
                          <Progress value={review.progress} className="h-2" />
                          <p className="text-right text-xs text-muted-foreground">
                            {review.progress}%
                          </p>
                        </div>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/review/${review.id}`}>
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
            <div className="space-y-3">
              {recentReviews.map((review) => (
                <Card
                  key={review.id}
                  className="transition-shadow hover:shadow-md"
                >
                  <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className="truncate font-medium">{review.title}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{review.journal}</span>
                        <span>&middot;</span>
                        <span>{review.date}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge
                        variant="outline"
                        className={
                          recommendationColor[review.recommendation] ?? ""
                        }
                      >
                        {recommendationLabel[review.recommendation] ??
                          review.recommendation}
                      </Badge>
                      <Button variant="ghost" size="sm" asChild>
                        <Link href={`/review/${review.id}/report`}>
                          View Report
                        </Link>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
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
                  <span className="text-2xl font-bold">{metrics.total}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg. Completion</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-primary" />
                  <span className="text-2xl font-bold">{metrics.avgTime}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Satisfaction</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-accent" />
                  <span className="text-2xl font-bold">
                    {metrics.satisfaction}
                    <span className="text-sm font-normal text-muted-foreground">
                      /5
                    </span>
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </aside>
      </div>
    </div>
  );
}
