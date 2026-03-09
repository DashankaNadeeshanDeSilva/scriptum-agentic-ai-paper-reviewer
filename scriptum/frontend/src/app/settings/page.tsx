"use client";

import { useEffect, useState } from "react";
import { useRef } from "react";
import {
  Bot,
  Globe,
  Key,
  Sliders,
  Wrench,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Save,
  Download,
  Upload,
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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useSettings } from "@/hooks/use-settings";
import type { TestConnectionRequest } from "@/lib/api/types";
import { PROVIDER_MODELS } from "@/lib/constants";
import { exportSettingsYaml, parseSettingsYaml, downloadYaml } from "@/lib/settings-yaml";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ProviderState {
  enabled: boolean;
  key: string;
  showKey: boolean;
  model: string;
  baseUrl?: string;
  testStatus: "idle" | "testing" | "success" | "error";
  testMessage?: string;
}

const tabs = [
  { value: "llm", label: "LLM", icon: Bot },
  { value: "mcp", label: "MCP", icon: Globe },
  { value: "apis", label: "APIs", icon: Key },
  { value: "preferences", label: "Preferences", icon: Sliders },
  { value: "advanced", label: "Advanced", icon: Wrench },
];

/* ------------------------------------------------------------------ */
/*  Safe config extraction helpers                                     */
/* ------------------------------------------------------------------ */

function getString(obj: Record<string, unknown>, key: string, fallback = ""): string {
  const val = obj[key];
  return typeof val === "string" ? val : fallback;
}

function getBool(obj: Record<string, unknown>, key: string, fallback = false): boolean {
  const val = obj[key];
  return typeof val === "boolean" ? val : fallback;
}

function getRecord(obj: Record<string, unknown>, key: string): Record<string, unknown> {
  const val = obj[key];
  return typeof val === "object" && val !== null && !Array.isArray(val)
    ? (val as Record<string, unknown>)
    : {};
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  const {
    settings,
    isLoading,
    error,
    isSaving,
    fetchSettings,
    saveSettings,
    testConnection,
    fetchOllamaModels,
  } = useSettings();

  const [defaultProvider, setDefaultProvider] = useState("anthropic");
  const [providers, setProviders] = useState<Record<string, ProviderState>>({
    anthropic: { enabled: true, key: "", showKey: false, model: "claude-opus-4-6", testStatus: "idle" },
    openai: { enabled: false, key: "", showKey: false, model: "gpt-4-turbo", testStatus: "idle" },
    ollama: { enabled: false, key: "", showKey: false, model: "llama2", baseUrl: "http://localhost:11434", testStatus: "idle" },
  });

  // MCP state
  const [perplexityEnabled, setPerplexityEnabled] = useState(false);
  const [perplexityKey, setPerplexityKey] = useState("");
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [googleKey, setGoogleKey] = useState("");
  const [googleCx, setGoogleCx] = useState("");

  // APIs state
  const [semanticScholarKey, setSemanticScholarKey] = useState("");
  const [arxivEnabled, setArxivEnabled] = useState(true);
  const [crossrefEnabled, setCrossrefEnabled] = useState(true);

  const [ollamaModels, setOllamaModels] = useState<string[]>(PROVIDER_MODELS.ollama);
  const [isLoadingOllamaModels, setIsLoadingOllamaModels] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // YAML import/export
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState(false);

  // Populate state from loaded settings
  useEffect(() => {
    if (!settings) return;

    const llm = settings.llm ?? {};
    const dp = getString(llm, "default_provider", "anthropic");
    setDefaultProvider(dp);

    // Update provider states from settings (providers are nested under llm.providers)
    const providersMap = getRecord(llm, "providers");
    setProviders((prev) => {
      const next = { ...prev };
      for (const name of Object.keys(next)) {
        const provConf = getRecord(providersMap, name);
        next[name] = {
          ...next[name],
          enabled: getBool(provConf, "enabled", next[name].enabled),
          key: getString(provConf, "masked_key"),
          model: getString(provConf, "model", next[name].model),
          baseUrl: getString(provConf, "base_url", next[name].baseUrl ?? ""),
        };
      }
      return next;
    });

    // MCP
    const mcp = settings.mcp ?? {};
    const perplexity = getRecord(mcp, "perplexity");
    setPerplexityEnabled(getBool(perplexity, "enabled", false));
    setPerplexityKey(getString(perplexity, "api_key"));
    const google = getRecord(mcp, "google_search");
    setGoogleEnabled(getBool(google, "enabled", false));
    setGoogleKey(getString(google, "api_key"));
    setGoogleCx(getString(google, "cx"));

    // APIs
    const apis = settings.apis ?? {};
    setSemanticScholarKey(getString(getRecord(apis, "semantic_scholar"), "api_key"));
    setArxivEnabled(getBool(getRecord(apis, "arxiv"), "enabled", true));
    setCrossrefEnabled(getBool(getRecord(apis, "crossref"), "enabled", true));
  }, [settings]);

  // Fetch Ollama models when Ollama is enabled
  useEffect(() => {
    if (providers.ollama.enabled) {
      setIsLoadingOllamaModels(true);
      fetchOllamaModels().then((models) => {
        if (models.length > 0) setOllamaModels(models);
        setIsLoadingOllamaModels(false);
      });
    }
  }, [providers.ollama.enabled, fetchOllamaModels]);

  const updateProvider = (name: string, update: Partial<ProviderState>) => {
    setProviders((prev) => ({
      ...prev,
      [name]: { ...prev[name], ...update },
    }));
  };

  async function handleTestConnection(name: string) {
    const prov = providers[name];
    updateProvider(name, { testStatus: "testing", testMessage: undefined });

    const req: TestConnectionRequest = {
      provider: name,
      model: prov.model,
      api_key: name !== "ollama" ? prov.key || null : null,
    };

    const result = await testConnection(req);
    if (result.success) {
      updateProvider(name, { testStatus: "success", testMessage: undefined });
    } else {
      updateProvider(name, { testStatus: "error", testMessage: result.error ?? "Connection failed" });
    }
  }

  async function handleSave() {
    setSaveSuccess(false);
    const payload = {
      llm: {
        default_provider: defaultProvider,
        providers: {
          anthropic: { enabled: providers.anthropic.enabled, api_key: providers.anthropic.key, default_model: providers.anthropic.model },
          openai: { enabled: providers.openai.enabled, api_key: providers.openai.key, default_model: providers.openai.model },
          ollama: { enabled: providers.ollama.enabled, default_model: providers.ollama.model, base_url: providers.ollama.baseUrl },
        },
      },
      mcp: {
        perplexity: { enabled: perplexityEnabled, api_key: perplexityKey },
        google_search: { enabled: googleEnabled, api_key: googleKey, cx: googleCx },
      },
      apis: {
        semantic_scholar: { api_key: semanticScholarKey },
        arxiv: { enabled: arxivEnabled },
        crossref: { enabled: crossrefEnabled },
      },
    };
    try {
      await saveSettings(payload);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      // error is set in the hook
    }
  }

  function handleExportYaml() {
    const payload = {
      llm: {
        default_provider: defaultProvider,
        providers: {
          anthropic: { enabled: providers.anthropic.enabled, api_key: providers.anthropic.key, default_model: providers.anthropic.model },
          openai: { enabled: providers.openai.enabled, api_key: providers.openai.key, default_model: providers.openai.model },
          ollama: { enabled: providers.ollama.enabled, default_model: providers.ollama.model, base_url: providers.ollama.baseUrl },
        },
      },
      mcp: {
        perplexity: { enabled: perplexityEnabled, api_key: perplexityKey },
        google_search: { enabled: googleEnabled, api_key: googleKey, cx: googleCx },
      },
      apis: {
        semantic_scholar: { api_key: semanticScholarKey },
        arxiv: { enabled: arxivEnabled },
        crossref: { enabled: crossrefEnabled },
      },
    };
    const yamlContent = exportSettingsYaml(payload);
    downloadYaml(yamlContent);
  }

  async function handleImportYaml(e: React.ChangeEvent<HTMLInputElement>) {
    setImportError(null);
    setImportSuccess(false);
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const content = await file.text();
      const parsed = parseSettingsYaml(content);
      await saveSettings(parsed);
      await fetchSettings();
      setImportSuccess(true);
      setTimeout(() => setImportSuccess(false), 3000);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Failed to import settings");
    } finally {
      // Reset file input so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 space-y-6">
        <Skeleton className="h-8 w-32" />
        <div className="flex gap-6">
          <Skeleton className="h-64 w-44" />
          <div className="flex-1 space-y-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <h1 className="font-heading mb-6 text-xl font-bold tracking-tight">
        Settings
      </h1>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={fetchSettings} className="gap-1">
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="llm" className="flex flex-col gap-6 sm:flex-row">
        {/* Sidebar tabs */}
        <TabsList className="flex h-auto flex-row justify-start gap-1 bg-transparent p-0 sm:flex-col sm:w-44">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="justify-start gap-2 data-[state=active]:bg-muted"
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <div className="flex-1">
          {/* ── LLM Tab ── */}
          <TabsContent value="llm" className="mt-0 space-y-6">
            <div>
              <Label className="text-sm font-medium">Default Provider</Label>
              <RadioGroup
                value={defaultProvider}
                onValueChange={setDefaultProvider}
                className="mt-2 flex gap-4"
              >
                {["anthropic", "openai", "ollama"].map((p) => (
                  <div key={p} className="flex items-center gap-2">
                    <RadioGroupItem value={p} id={`provider-${p}`} />
                    <Label htmlFor={`provider-${p}`} className="capitalize">
                      {p}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </div>

            <Separator />

            {Object.entries(providers).map(([name, prov]) => (
              <Card key={name}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base capitalize">
                      {name}
                    </CardTitle>
                    <Switch
                      checked={prov.enabled}
                      onCheckedChange={(v) =>
                        updateProvider(name, { enabled: v })
                      }
                    />
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {name !== "ollama" && (
                    <div className="space-y-2">
                      <Label>API Key</Label>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Input
                            type={prov.showKey ? "text" : "password"}
                            placeholder={`Enter ${name} API key`}
                            value={prov.key}
                            onChange={(e) =>
                              updateProvider(name, { key: e.target.value })
                            }
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                            onClick={() =>
                              updateProvider(name, {
                                showKey: !prov.showKey,
                              })
                            }
                          >
                            {prov.showKey ? (
                              <EyeOff className="h-3.5 w-3.5" />
                            ) : (
                              <Eye className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}

                  {name === "ollama" && (
                    <div className="space-y-2">
                      <Label>Base URL</Label>
                      <Input
                        value={prov.baseUrl ?? "http://localhost:11434"}
                        onChange={(e) =>
                          updateProvider(name, { baseUrl: e.target.value })
                        }
                      />
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label>Model</Label>
                    <Select
                      value={prov.model}
                      onValueChange={(v) =>
                        updateProvider(name, { model: v })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(name === "ollama" && ollamaModels.length > 0
                          ? ollamaModels
                          : PROVIDER_MODELS[name] ?? []
                        ).map((m) => (
                          <SelectItem key={m} value={m}>
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(name)}
                      disabled={prov.testStatus === "testing"}
                      aria-busy={prov.testStatus === "testing"}
                    >
                      {prov.testStatus === "testing" ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : null}
                      Test Connection
                    </Button>
                    {prov.testStatus === "success" && (
                      <Badge
                        variant="outline"
                        className="bg-success/10 text-success border-success/20"
                      >
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        Connected
                      </Badge>
                    )}
                    {prov.testStatus === "error" && (
                      <Badge
                        variant="outline"
                        className="bg-destructive/10 text-destructive border-destructive/20"
                      >
                        <XCircle className="mr-1 h-3 w-3" />
                        {prov.testMessage ?? "Failed"}
                      </Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* ── MCP Tab ── */}
          <TabsContent value="mcp" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Perplexity</CardTitle>
                <CardDescription>
                  Online search capabilities for literature discovery.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Enabled</Label>
                  <Switch checked={perplexityEnabled} onCheckedChange={setPerplexityEnabled} />
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    placeholder="pplx-..."
                    value={perplexityKey}
                    onChange={(e) => setPerplexityKey(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Google Search</CardTitle>
                <CardDescription>
                  Custom search for supplementary reference discovery.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Enabled</Label>
                  <Switch checked={googleEnabled} onCheckedChange={setGoogleEnabled} />
                </div>
                <div className="space-y-2">
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    placeholder="AIza..."
                    value={googleKey}
                    onChange={(e) => setGoogleKey(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Custom Search Engine ID (CX)</Label>
                  <Input
                    placeholder="cx-..."
                    value={googleCx}
                    onChange={(e) => setGoogleCx(e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── APIs Tab ── */}
          <TabsContent value="apis" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Semantic Scholar</CardTitle>
                <CardDescription>
                  Optional API key increases rate limits.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Input
                  type="password"
                  placeholder="API key (optional)"
                  value={semanticScholarKey}
                  onChange={(e) => setSemanticScholarKey(e.target.value)}
                />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">arXiv</p>
                  <p className="text-sm text-muted-foreground">
                    Open access preprint repository
                  </p>
                </div>
                <Switch checked={arxivEnabled} onCheckedChange={setArxivEnabled} />
              </CardContent>
            </Card>

            <Card>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">CrossRef</p>
                  <p className="text-sm text-muted-foreground">
                    DOI resolution and metadata
                  </p>
                </div>
                <Switch checked={crossrefEnabled} onCheckedChange={setCrossrefEnabled} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Preferences Tab ── */}
          <TabsContent value="preferences" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Defaults</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Default Journal Preset</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="None" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="ieee">IEEE TASLP</SelectItem>
                      <SelectItem value="nature">Nature</SelectItem>
                      <SelectItem value="neurips">NeurIPS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* ── Advanced Tab ── */}
          <TabsContent value="advanced" className="mt-0 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Configuration Management
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Separator />
                <div className="text-sm text-muted-foreground">
                  <p>
                    Config file:{" "}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                      ~/.scriptum/config.yaml
                    </code>
                  </p>
                  <p className="mt-1">
                    Encryption key:{" "}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                      ~/.scriptum/.key
                    </code>
                  </p>
                </div>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Environment Variables</p>
                  <div className="rounded-lg bg-muted/50 p-3 font-mono text-xs space-y-1">
                    <p>ANTHROPIC_API_KEY</p>
                    <p>OPENAI_API_KEY</p>
                    <p>OLLAMA_BASE_URL</p>
                    <p>PERPLEXITY_API_KEY</p>
                    <p>GOOGLE_SEARCH_API_KEY</p>
                    <p>SEMANTIC_SCHOLAR_API_KEY</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Import / Export</CardTitle>
                <CardDescription>
                  Export your settings as YAML (API keys are masked) or import from a YAML file.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  <Button variant="outline" size="sm" className="gap-2" onClick={handleExportYaml}>
                    <Download className="h-3.5 w-3.5" />
                    Export YAML
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="h-3.5 w-3.5" />
                    Import YAML
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".yaml,.yml"
                    className="hidden"
                    onChange={handleImportYaml}
                  />
                </div>
                {importSuccess && (
                  <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                    <CheckCircle2 className="mr-1 h-3 w-3" />
                    Settings imported successfully
                  </Badge>
                )}
                {importError && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{importError}</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </div>
      </Tabs>

      {/* Save button */}
      <div className="mt-8 flex items-center justify-end gap-3">
        {saveSuccess && (
          <Badge variant="outline" className="bg-success/10 text-success border-success/20">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Saved
          </Badge>
        )}
        <Button onClick={handleSave} disabled={isSaving} aria-busy={isSaving} className="gap-2">
          {isSaving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
