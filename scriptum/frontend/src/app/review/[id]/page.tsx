"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Circle,
  Loader2,
  FileText,
  XCircle,
  ArrowRight,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useReviewStatus, useCancelReview } from "@/hooks/use-reviews";
import { useReviewProgress } from "@/hooks/use-review-progress";
import type { StepProgress } from "@/hooks/use-review-progress";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const StatusIcon = ({ status }: { status: StepProgress["status"] }) => {
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
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function ReviewProgressPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);

  const { status: reviewStatus, isLoading: statusLoading } = useReviewStatus(id);
  const { steps, agents, overallProgress, isComplete, error: wsError } = useReviewProgress(id);
  const { cancelReview, isCancelling } = useCancelReview();

  const agentList = Object.values(agents);

  async function handleCancel() {
    try {
      await cancelReview(id);
      setCancelDialogOpen(false);
      router.push("/");
    } catch {
      // stay on page
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="mb-6 space-y-1">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-primary" />
          <h1 className="font-heading text-xl font-bold tracking-tight">
            Review Progress
          </h1>
        </div>
        <div className="flex items-center gap-2 pl-8 text-sm text-muted-foreground">
          {statusLoading ? (
            <Skeleton className="h-4 w-40" />
          ) : (
            <>
              <Badge variant="secondary">
                {isComplete ? "Completed" : reviewStatus?.status ?? "…"}
              </Badge>
              <span>&middot;</span>
              <span>Step: {reviewStatus?.current_step ?? "—"}</span>
              <span>&middot;</span>
              <span className="font-mono text-xs">{id}</span>
            </>
          )}
        </div>
      </div>

      {/* WebSocket error */}
      {wsError && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{wsError}</AlertDescription>
        </Alert>
      )}

      {/* Overall progress */}
      <Card className="mb-8">
        <CardContent className="py-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Overall Progress</span>
            {isComplete && (
              <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                Complete
              </Badge>
            )}
          </div>
          <Progress value={overallProgress} className="mt-2 h-2.5" />
          <p className="mt-1 text-right text-xs text-muted-foreground">
            {overallProgress}%
          </p>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="relative space-y-0">
        {steps.map((step, i) => (
          <div key={step.id} className="relative flex gap-4 pb-8 last:pb-0">
            {/* Vertical line */}
            {i < steps.length - 1 && (
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
                  {step.status === "failed" && (
                    <Badge
                      variant="outline"
                      className="bg-destructive/10 text-destructive border-destructive/20 text-xs"
                    >
                      Failed
                    </Badge>
                  )}
                </CollapsibleTrigger>

                <CollapsibleContent>
                  {step.message && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {step.message}
                    </p>
                  )}

                  {/* Agent sub-progress for the reviewing step */}
                  {step.id === "reviewing" && agentList.length > 0 && (
                    <Card className="mt-3">
                      <CardContent className="space-y-3 py-3">
                        {agentList.map((agent) => (
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
                            {agent.message && (
                              <p className="text-xs text-muted-foreground">
                                {agent.message}
                              </p>
                            )}
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
        <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
          <DialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive"
              disabled={isComplete}
            >
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
              <Button
                variant="destructive"
                onClick={handleCancel}
                disabled={isCancelling}
              >
                {isCancelling ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : null}
                Yes, cancel review
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Button asChild disabled={!isComplete}>
          <Link href={`/review/${id}/report`}>
            View Report
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </div>
  );
}
