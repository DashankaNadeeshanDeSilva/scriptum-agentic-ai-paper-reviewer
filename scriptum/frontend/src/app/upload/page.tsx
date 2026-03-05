"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Upload,
  FileText,
  FileCode,
  Check,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useFileUpload } from "@/hooks/use-file-upload";
import { useStartReview } from "@/hooks/use-reviews";
import { ApiError } from "@/lib/api/client";

/* ------------------------------------------------------------------ */
/*  Constants                                                         */
/* ------------------------------------------------------------------ */

const steps = ["Upload Files", "Journal", "Domain", "Confirm"];

const journals = [
  "IEEE TASLP",
  "Nature",
  "Nature Machine Intelligence",
  "ACM Computing Surveys",
  "AAAI",
  "NeurIPS",
  "ICML",
  "ACL",
  "CVPR",
  "ICLR",
];

const generalDomains = [
  "Computer Science",
  "Engineering",
  "Natural Sciences",
  "Medicine & Health",
  "Social Sciences",
];

const specificAreas: Record<string, string[]> = {
  "Computer Science": [
    "Machine Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Robotics",
    "Systems & Networking",
    "Security",
  ],
  Engineering: [
    "Electrical",
    "Mechanical",
    "Biomedical",
    "Chemical",
    "Civil",
  ],
  "Natural Sciences": ["Physics", "Chemistry", "Biology", "Mathematics"],
  "Medicine & Health": [
    "Clinical Research",
    "Public Health",
    "Neuroscience",
    "Genomics",
  ],
  "Social Sciences": ["Economics", "Psychology", "Sociology", "Political Science"],
};

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

export default function UploadPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [latexFile, setLatexFile] = useState<File | null>(null);
  const [journal, setJournal] = useState("");
  const [customJournal, setCustomJournal] = useState("");
  const [generalDomain, setGeneralDomain] = useState("");
  const [specificArea, setSpecificArea] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { uploadedFiles, isUploading, error: uploadError, uploadFiles } = useFileUpload();
  const { startReview, isSubmitting } = useStartReview();

  const fileIds = uploadedFiles.map((f) => f.file_id);

  const effectiveJournal = journal === "__custom" ? customJournal : journal;
  const canNext =
    (step === 0 && pdfFile && !isUploading && fileIds.length > 0) ||
    (step === 1 && effectiveJournal) ||
    (step === 2 && generalDomain && specificArea) ||
    step === 3;

  async function handleFileSelect(file: File, type: "pdf" | "latex") {
    if (type === "pdf") {
      setPdfFile(file);
    } else {
      setLatexFile(file);
    }
    try {
      await uploadFiles([file]);
    } catch {
      // error is already set in the hook
    }
  }

  async function handleStart() {
    setSubmitError(null);
    try {
      const response = await startReview({
        file_ids: fileIds,
        journal_name: effectiveJournal,
        domain_general: generalDomain,
        domain_specific: specificArea,
      });
      router.push(`/review/${response.review_id}`);
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Failed to start review";
      setSubmitError(msg);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      {/* Stepper */}
      <nav className="mb-8 flex items-center justify-center gap-2">
        {steps.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                i < step
                  ? "bg-primary text-primary-foreground"
                  : i === step
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
              }`}
            >
              {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
            </div>
            <span
              className={`hidden text-sm sm:inline ${
                i === step ? "font-medium" : "text-muted-foreground"
              }`}
            >
              {label}
            </span>
            {i < steps.length - 1 && (
              <Separator className="w-6" orientation="horizontal" />
            )}
          </div>
        ))}
      </nav>

      {/* Step 0 — File Upload */}
      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Upload Your Paper</CardTitle>
            <CardDescription>
              Upload a PDF of your manuscript. Optionally include LaTeX source
              for more accurate formatting analysis.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* PDF dropzone */}
            <label className="group flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed border-primary/30 bg-primary/5 p-8 transition-colors hover:border-primary/50 hover:bg-primary/10">
              {isUploading && !pdfFile ? (
                <>
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="font-medium">Uploading…</span>
                </>
              ) : pdfFile ? (
                <>
                  <FileText className="h-8 w-8 text-primary" />
                  <span className="font-medium">{pdfFile.name}</span>
                  <span className="text-sm text-muted-foreground">
                    {(pdfFile.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                  {isUploading && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </>
              ) : (
                <>
                  <Upload className="h-8 w-8 text-muted-foreground transition-colors group-hover:text-primary" />
                  <span className="font-medium">
                    Drop PDF here or click to browse
                  </span>
                  <span className="text-sm text-muted-foreground">
                    PDF up to 50 MB
                  </span>
                </>
              )}
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file, "pdf");
                }}
              />
            </label>

            {/* LaTeX optional */}
            <label className="group flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-muted-foreground/30 p-6 transition-colors hover:border-muted-foreground/50">
              {latexFile ? (
                <>
                  <FileCode className="h-6 w-6 text-muted-foreground" />
                  <span className="text-sm font-medium">{latexFile.name}</span>
                  {isUploading && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </>
              ) : (
                <>
                  <FileCode className="h-6 w-6 text-muted-foreground/60" />
                  <span className="text-sm text-muted-foreground">
                    Optional: Add LaTeX source (.tex)
                  </span>
                  <Badge variant="secondary" className="text-xs">
                    Recommended for better formatting analysis
                  </Badge>
                </>
              )}
              <input
                type="file"
                accept=".tex"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file, "latex");
                }}
              />
            </label>

            {/* Upload error */}
            {uploadError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{uploadError}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 1 — Journal Selection */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Target Journal</CardTitle>
            <CardDescription>
              Select the journal or conference you&apos;re targeting. This helps
              reviewers calibrate their expectations.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select value={journal} onValueChange={setJournal}>
              <SelectTrigger>
                <SelectValue placeholder="Select a journal or conference" />
              </SelectTrigger>
              <SelectContent>
                {journals.map((j) => (
                  <SelectItem key={j} value={j}>
                    {j}
                  </SelectItem>
                ))}
                <SelectItem value="__custom">Other (type below)</SelectItem>
              </SelectContent>
            </Select>
            {journal === "__custom" && (
              <Input
                placeholder="Enter journal or conference name"
                value={customJournal}
                onChange={(e) => setCustomJournal(e.target.value)}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* Step 2 — Domain Selection */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Research Domain</CardTitle>
            <CardDescription>
              Specify the general field and specific area so the reviewers bring
              the right expertise.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>General Domain</Label>
              <Select
                value={generalDomain}
                onValueChange={(v) => {
                  setGeneralDomain(v);
                  setSpecificArea("");
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select domain" />
                </SelectTrigger>
                <SelectContent>
                  {generalDomains.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Specific Area</Label>
              <Select
                value={specificArea}
                onValueChange={setSpecificArea}
                disabled={!generalDomain}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select area" />
                </SelectTrigger>
                <SelectContent>
                  {(specificAreas[generalDomain] ?? []).map((a) => (
                    <SelectItem key={a} value={a}>
                      {a}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3 — Confirmation */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Review Summary</CardTitle>
            <CardDescription>
              Confirm the details below, then start the review.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-muted/50 p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Paper</span>
                <span className="font-medium">{pdfFile?.name}</span>
              </div>
              {latexFile && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">LaTeX</span>
                  <span className="font-medium">{latexFile.name}</span>
                </div>
              )}
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Journal</span>
                <span className="font-medium">{effectiveJournal}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Domain</span>
                <span className="font-medium">
                  {generalDomain} &rarr; {specificArea}
                </span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">LLM Provider</span>
                <Badge variant="secondary">Default from settings</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit error */}
      {submitError && step === 3 && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{submitError}</AlertDescription>
        </Alert>
      )}

      {/* Navigation buttons */}
      <div className="mt-6 flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 0 || isSubmitting}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        {step < 3 ? (
          <Button onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
            Next
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleStart} disabled={isSubmitting} className="gap-2">
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isSubmitting ? "Starting…" : "Start Review"}
          </Button>
        )}
      </div>
    </div>
  );
}
