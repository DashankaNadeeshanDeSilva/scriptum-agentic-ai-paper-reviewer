"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  Download,
  MessageSquare,
  Star,
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
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
import { Progress } from "@/components/ui/progress";

/* ------------------------------------------------------------------ */
/*  Mock report data — replaced by API in Phase 4                     */
/* ------------------------------------------------------------------ */

const report = {
  recommendation: "minor_revision" as const,
  confidence: "high",
  strengths: [
    "Novel application of attention mechanisms to extremely low-resource settings",
    "Comprehensive ablation study across 8 language families",
    "Clear and well-structured writing with excellent figures",
  ],
  weaknesses: [
    "Limited comparison with recent adapter-based methods (2024)",
    "Statistical significance tests not reported for all experiments",
    "Computational cost analysis is missing",
  ],
  scores: [
    { category: "Novelty", aggregated: 7.8, core: 8.0, adjacent: 7.5, methods: 8.0 },
    { category: "Methodology", aggregated: 7.2, core: 7.0, adjacent: 7.5, methods: 7.0 },
    { category: "Significance", aggregated: 7.5, core: 8.0, adjacent: 7.0, methods: 7.5 },
    { category: "Presentation", aggregated: 8.5, core: 8.5, adjacent: 8.5, methods: 8.5 },
    { category: "Reproducibility", aggregated: 6.8, core: 7.0, adjacent: 6.5, methods: 7.0 },
    { category: "Impact", aggregated: 7.0, core: 7.5, adjacent: 6.5, methods: 7.0 },
  ],
  improvements: [
    "Add comparison with LoRA and adapter-tuning baselines from 2024",
    "Include paired bootstrap significance tests for all language pairs",
    "Add a section on computational requirements and inference latency",
    "Discuss limitations of the approach for isolating languages",
  ],
};

const recBadge: Record<string, { label: string; className: string }> = {
  accept: { label: "Accept", className: "bg-success/15 text-success border-success/25" },
  minor_revision: { label: "Minor Revision", className: "bg-amber/15 text-amber border-amber/25" },
  major_revision: { label: "Major Revision", className: "bg-warning/15 text-warning border-warning/25" },
  reject: { label: "Reject", className: "bg-destructive/15 text-destructive border-destructive/25" },
};

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function ReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const rec = recBadge[report.recommendation];

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
              {report.strengths.map((s, i) => (
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
              {report.weaknesses.map((w, i) => (
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
                <TableHead className="text-center">Core</TableHead>
                <TableHead className="text-center">Adjacent</TableHead>
                <TableHead className="text-center">Methods</TableHead>
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
                          {s.aggregated.toFixed(1)}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>Aggregated from 3 reviewers</TooltipContent>
                    </Tooltip>
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {s.core.toFixed(1)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {s.adjacent.toFixed(1)}
                  </TableCell>
                  <TableCell className="text-center text-muted-foreground">
                    {s.methods.toFixed(1)}
                  </TableCell>
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
          <Accordion type="multiple" defaultValue={["methodology"]}>
            {["Novelty", "Methodology", "Significance", "Presentation"].map(
              (cat) => (
                <AccordionItem key={cat} value={cat.toLowerCase()}>
                  <AccordionTrigger className="text-sm font-medium">
                    {cat}
                  </AccordionTrigger>
                  <AccordionContent className="text-sm text-muted-foreground">
                    Detailed feedback for {cat.toLowerCase()} will be populated
                    from the API response. This includes specific observations,
                    cited evidence, and actionable suggestions from each
                    reviewer.
                  </AccordionContent>
                </AccordionItem>
              )
            )}
          </Accordion>
        </TabsContent>

        <TabsContent value="individual" className="mt-4 space-y-4">
          {["Core Expert", "Adjacent Domain", "Methods Specialist"].map(
            (reviewer) => (
              <Card key={reviewer}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{reviewer}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Full individual review from the {reviewer} will appear here,
                  including their scores, strengths, weaknesses, and
                  recommendation.
                </CardContent>
              </Card>
            )
          )}
        </TabsContent>

        <TabsContent value="evidence" className="mt-4">
          <Card>
            <CardContent className="py-6 text-center text-sm text-muted-foreground">
              Evidence citations and linked sources will be displayed here once
              the review agents populate them.
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Suggested Improvements ── */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Suggested Improvements</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {report.improvements.map((imp, i) => (
              <li key={i}>{imp}</li>
            ))}
          </ol>
        </CardContent>
      </Card>

      {/* ── Actions ── */}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" className="gap-2">
          <Download className="h-4 w-4" />
          Export PDF
        </Button>
        <Button variant="outline" className="gap-2">
          <MessageSquare className="h-4 w-4" />
          Ask Questions
        </Button>

        <Dialog open={feedbackOpen} onOpenChange={setFeedbackOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" className="gap-2">
              <Star className="h-4 w-4" />
              Submit Feedback
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
                <Button key={n} variant="outline" size="icon">
                  <Star className="h-5 w-5" />
                </Button>
              ))}
            </div>
            <DialogFooter>
              <Button onClick={() => setFeedbackOpen(false)}>
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
