"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpenText,
  Cloud,
  Server,
  Check,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Shield,
  Loader2,
  CheckCircle2,
  XCircle,
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useSettings } from "@/hooks/use-settings";
import { DEFAULT_MODELS } from "@/lib/constants";

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

const totalSteps = 5;

export default function SetupPage() {
  const router = useRouter();
  const { saveSettings, testConnection, isSaving } = useSettings();

  const [step, setStep] = useState(0);
  const [llmChoice, setLlmChoice] = useState("cloud");

  // API keys
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");

  // Research tools
  const [perplexityKey, setPerplexityKey] = useState("");
  const [googleSearchKey, setGoogleSearchKey] = useState("");

  // Test connection state
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [testMessage, setTestMessage] = useState("");

  const progress = ((step + 1) / totalSteps) * 100;

  async function handleTestConnection() {
    setTestStatus("testing");
    setTestMessage("");

    const provider = llmChoice === "cloud" ? "anthropic" : "ollama";
    const model = llmChoice === "cloud" ? DEFAULT_MODELS.anthropic : DEFAULT_MODELS.ollama;
    const apiKey = llmChoice === "cloud" ? anthropicKey : null;

    const result = await testConnection({
      provider,
      model,
      api_key: apiKey || null,
    });

    if (result.success) {
      setTestStatus("success");
      setTestMessage("Connection successful");
    } else {
      setTestStatus("error");
      setTestMessage(result.error ?? "Connection failed");
    }
  }

  async function handleComplete() {
    const isCloud = llmChoice === "cloud";
    const payload = {
      llm: {
        default_provider: isCloud ? "anthropic" : "ollama",
        anthropic: isCloud
          ? { enabled: true, api_key: anthropicKey, model: DEFAULT_MODELS.anthropic }
          : { enabled: false },
        openai: isCloud && openaiKey
          ? { enabled: true, api_key: openaiKey, model: DEFAULT_MODELS.openai }
          : { enabled: false },
        ollama: !isCloud
          ? { enabled: true, base_url: ollamaUrl, model: DEFAULT_MODELS.ollama }
          : { enabled: false },
      },
      mcp: {
        perplexity: perplexityKey
          ? { enabled: true, api_key: perplexityKey }
          : { enabled: false },
        google_search: googleSearchKey
          ? { enabled: true, api_key: googleSearchKey }
          : { enabled: false },
      },
    };

    try {
      await saveSettings(payload);
      router.push("/");
    } catch {
      // error shown via hook
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-8 sm:px-6">
      {/* Progress */}
      <div className="mb-8 space-y-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Step {step + 1} of {totalSteps}
          </span>
          <span>{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} className="h-1.5" />
      </div>

      {/* ── Step 0: Welcome ── */}
      {step === 0 && (
        <Card className="border-primary/15">
          <CardContent className="flex flex-col items-center gap-6 py-10 text-center">
            <div className="rounded-full bg-primary/10 p-4">
              <BookOpenText className="h-10 w-10 text-primary" />
            </div>
            <div className="space-y-2">
              <h1 className="font-heading text-2xl font-bold tracking-tight">
                Welcome to SCRIPTUM
              </h1>
              <p className="text-muted-foreground">
                AI-powered academic paper review with multi-agent reviewers.
                Let&apos;s get you set up in a few minutes.
              </p>
            </div>
            <Alert className="text-left">
              <Shield className="h-4 w-4" />
              <AlertDescription>
                Your papers and API keys are processed locally and encrypted at
                rest. Nothing is shared without your consent.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* ── Step 1: LLM Provider ── */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Choose Your LLM Provider</CardTitle>
            <CardDescription>
              SCRIPTUM uses large language models to power its reviewers. Choose
              your preferred approach.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <RadioGroup
              value={llmChoice}
              onValueChange={setLlmChoice}
              className="space-y-3"
            >
              <label className="flex cursor-pointer items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50 has-[data-state=checked]:border-primary has-[data-state=checked]:bg-primary/5">
                <RadioGroupItem value="cloud" className="mt-1" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Cloud className="h-4 w-4 text-primary" />
                    <span className="font-medium">Cloud Provider</span>
                    <Badge variant="secondary" className="text-xs">
                      Recommended
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Use Anthropic (Claude) or OpenAI (GPT-4) for highest quality
                    reviews.
                  </p>
                </div>
              </label>

              <label className="flex cursor-pointer items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50 has-[data-state=checked]:border-primary has-[data-state=checked]:bg-primary/5">
                <RadioGroupItem value="local" className="mt-1" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-primary" />
                    <span className="font-medium">Local (Ollama)</span>
                    <Badge variant="outline" className="text-xs">
                      Maximum Privacy
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Run models locally. Requires Ollama installed with a
                    compatible model.
                  </p>
                </div>
              </label>
            </RadioGroup>
          </CardContent>
        </Card>
      )}

      {/* ── Step 2: API Keys ── */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
            <CardDescription>
              {llmChoice === "cloud"
                ? "Enter your API key for the chosen provider."
                : "Configure Ollama connection."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {llmChoice === "cloud" ? (
              <>
                <div className="space-y-2">
                  <Label>Anthropic API Key</Label>
                  <Input
                    type="password"
                    placeholder="sk-ant-..."
                    value={anthropicKey}
                    onChange={(e) => setAnthropicKey(e.target.value)}
                  />
                </div>
                <Separator />
                <div className="space-y-2">
                  <Label>
                    OpenAI API Key{" "}
                    <span className="text-muted-foreground">(optional)</span>
                  </Label>
                  <Input
                    type="password"
                    placeholder="sk-..."
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                  />
                </div>
              </>
            ) : (
              <div className="space-y-2">
                <Label>Ollama Base URL</Label>
                <Input
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Make sure Ollama is running with a model pulled.
                </p>
              </div>
            )}

            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestConnection}
                disabled={testStatus === "testing"}
                aria-busy={testStatus === "testing"}
              >
                {testStatus === "testing" && (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                )}
                Test Connection
              </Button>
              {testStatus === "success" && (
                <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Connected
                </Badge>
              )}
              {testStatus === "error" && (
                <Badge variant="outline" className="bg-destructive/10 text-destructive border-destructive/20">
                  <XCircle className="mr-1 h-3 w-3" />
                  {testMessage}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 3: MCP Config ── */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Research Tools</CardTitle>
            <CardDescription>
              Optional: configure search tools for richer literature analysis.
              You can skip this and add them later.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>
                Perplexity API Key{" "}
                <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                type="password"
                placeholder="pplx-..."
                value={perplexityKey}
                onChange={(e) => setPerplexityKey(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>
                Google Search API Key{" "}
                <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                type="password"
                placeholder="AIza..."
                value={googleSearchKey}
                onChange={(e) => setGoogleSearchKey(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Step 4: Summary ── */}
      {step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle>All Set!</CardTitle>
            <CardDescription>
              Here&apos;s a summary of your configuration.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-muted/50 p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">LLM Provider</span>
                <Badge variant="secondary" className="capitalize">
                  {llmChoice === "cloud" ? "Cloud (Anthropic)" : "Local (Ollama)"}
                </Badge>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">API Key</span>
                <span className="text-sm">
                  {llmChoice === "cloud"
                    ? anthropicKey ? "Configured" : "Not set"
                    : ollamaUrl}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Perplexity</span>
                <span className="text-sm">{perplexityKey ? "Configured" : "Skipped"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Google Search</span>
                <span className="text-sm">{googleSearchKey ? "Configured" : "Skipped"}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-muted-foreground">Config Location</span>
                <code className="font-mono text-xs">~/.scriptum/</code>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 0 || isSaving}
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        {step < totalSteps - 1 ? (
          <Button onClick={() => setStep((s) => s + 1)}>
            {step === 0 ? "Get Started" : "Next"}
            <ChevronRight className="ml-1 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleComplete} disabled={isSaving} aria-busy={isSaving} className="gap-2">
            {isSaving ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isSaving ? "Saving…" : "Complete Setup"}
          </Button>
        )}
      </div>
    </div>
  );
}
