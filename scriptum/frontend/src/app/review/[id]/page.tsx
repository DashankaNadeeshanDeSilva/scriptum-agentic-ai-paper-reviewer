"use client";

import { use } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Circle,
  Loader2,
  FileText,
  XCircle,
  ArrowRight,
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
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/* ------------------------------------------------------------------ */
/*  Mock data — replaced by WebSocket hook in Phase 4                 */
/* ------------------------------------------------------------------ */

type StepStatus = "complete" | "active" | "pending" | "failed";

interface ReviewStep {
  label: string;
  status: StepStatus;
  detail?: string;
  agents?: { name: string; progress: number; task: string }[];
}

const mockSteps: ReviewStep[] = [
  {
    label: "Document Processing",
    status: "complete",
    detail: "PDF parsed via GROBID in 4.2 s",
  },
  {
    label: "Meta Reviewer Initialization",
    status: "complete",
    detail: "Reviewer roles assigned",
  },
  {
    label: "Desk Check",
    status: "complete",
    detail: "Passed — formatting confidence 0.92",
  },
  {
    label: "Independent Review",
    status: "active",
    agents: [
      { name: "Core Expert", progress: 78, task: "Analysing methodology" },
      {
        name: "Adjacent Domain",
        progress: 54,
        task: "Evaluating novelty claims",
      },
      {
        name: "Methods Specialist",
        progress: 31,
        task: "Checking reproducibility",
      },
    ],
  },
  { label: "Review Aggregation", status: "pending" },
  { label: "Report Generation", status: "pending" },
];

const overallProgress = 62;

const StatusIcon = ({ status }: { status: StepStatus }) => {
  switch (status) {
    case "complete":
      return <CheckCircle2 className="h-5 w-5 text-success" />;
    case "active":
      return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-destructive" />;
    default:
      return <Circle className="h-5 w-5 text-muted-foreground/40" />;
  }
};

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function ReviewProgressPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6 space-y-1">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-primary" />
          <h1 className="font-heading text-xl font-bold tracking-tight">
            Attention Mechanisms in Low-Resource NLP
          </h1>
        </div>
        <div className="flex items-center gap-2 pl-8 text-sm text-muted-foreground">
          <span>ACL 2025</span>
          <span>&middot;</span>
          <Badge variant="secondary">Reviewing</Badge>
          <span>&middot;</span>
          <span className="font-mono text-xs">{id}</span>
        </div>
      </div>

      {/* Overall progress */}
      <Card className="mb-8">
        <CardContent className="py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Overall Progress</span>
            <span className="text-muted-foreground">
              ~3 min remaining
            </span>
          </div>
          <Progress value={overallProgress} className="mt-2 h-2.5" />
          <p className="mt-1 text-right text-xs text-muted-foreground">
            {overallProgress}%
          </p>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="relative space-y-0">
        {mockSteps.map((step, i) => (
          <div key={step.label} className="relative flex gap-4 pb-8 last:pb-0">
            {/* Vertical line */}
            {i < mockSteps.length - 1 && (
              <div className="absolute left-[9px] top-7 h-full w-px bg-border" />
            )}

            {/* Icon */}
            <div className="relative z-10 mt-0.5 flex-shrink-0">
              <StatusIcon status={step.status} />
            </div>

            {/* Content */}
            <div className="flex-1 space-y-2">
              <Collapsible defaultOpen={step.status === "active"}>
                <CollapsibleTrigger className="flex w-full items-center justify-between">
                  <span
                    className={`text-sm font-medium ${
                      step.status === "pending"
                        ? "text-muted-foreground"
                        : ""
                    }`}
                  >
                    {step.label}
                  </span>
                  {step.status === "complete" && (
                    <Badge
                      variant="outline"
                      className="bg-success/10 text-success border-success/20 text-xs"
                    >
                      Done
                    </Badge>
                  )}
                </CollapsibleTrigger>

                <CollapsibleContent>
                  {step.detail && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {step.detail}
                    </p>
                  )}

                  {step.agents && (
                    <Card className="mt-3">
                      <CardContent className="space-y-3 py-3">
                        {step.agents.map((agent) => (
                          <div key={agent.name} className="space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="font-medium">{agent.name}</span>
                              <span className="text-xs text-muted-foreground">
                                {agent.progress}%
                              </span>
                            </div>
                            <Progress
                              value={agent.progress}
                              className="h-1.5"
                            />
                            <p className="text-xs text-muted-foreground">
                              {agent.task}
                            </p>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  )}
                </CollapsibleContent>
              </Collapsible>
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <Separator className="my-8" />
      <div className="flex items-center justify-between">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="text-destructive">
              Cancel Review
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Cancel this review?</DialogTitle>
              <DialogDescription>
                This action cannot be undone. All progress will be lost.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="destructive">Yes, cancel review</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Button asChild disabled={overallProgress < 100}>
          <Link href={`/review/${id}/report`}>
            View Report
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
