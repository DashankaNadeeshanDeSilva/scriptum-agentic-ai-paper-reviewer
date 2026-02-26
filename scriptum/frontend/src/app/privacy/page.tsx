import {
  Shield,
  Lock,
  Eye,
  Key,
  Code,
  Scale,
  ExternalLink,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

/* ------------------------------------------------------------------ */
/*  Page                                                              */
/* ------------------------------------------------------------------ */

const sections = [
  {
    id: "data",
    icon: Eye,
    title: "Data Handling Overview",
    content:
      "SCRIPTUM processes your papers entirely within your local environment or through the LLM provider you configure. We do not collect, store, or transmit your papers to any third-party analytics service. All review data is stored in your local database (~/.scriptum/scriptum.db) and can be deleted at any time.",
  },
  {
    id: "confidentiality",
    icon: Lock,
    title: "Paper Confidentiality",
    content:
      "Your manuscripts are processed locally using GROBID for PDF parsing. When using cloud LLM providers (Anthropic, OpenAI), paper content is sent to their APIs for review generation. When using Ollama, all processing happens entirely on your machine. We recommend reviewing your chosen provider's data handling policies.",
  },
  {
    id: "providers",
    icon: Shield,
    title: "LLM Provider Policies",
    content:
      "Each LLM provider has their own data handling policies. Anthropic does not train on API inputs by default. OpenAI provides a data usage opt-out for API users. Ollama processes everything locally with zero data transmission. We recommend choosing a provider whose policies align with your institutional requirements.",
  },
  {
    id: "keys",
    icon: Key,
    title: "API Key Security",
    content:
      "API keys stored in ~/.scriptum/config.yaml are encrypted at rest using AES-256 (Fernet) encryption. The encryption key is stored at ~/.scriptum/.key with restricted file permissions (0600, owner-only). Keys are decrypted only in memory during runtime and are never logged or exposed in API responses (shown masked with last 4 characters only).",
  },
  {
    id: "opensource",
    icon: Code,
    title: "Open Source Transparency",
    content:
      "SCRIPTUM is fully open source. You can inspect every line of code, audit the data flow, and verify that no telemetry or tracking is included. Contributions and security audits are welcome. The source code is available on GitHub.",
  },
  {
    id: "gdpr",
    icon: Scale,
    title: "GDPR Compliance",
    content:
      "For EU users: SCRIPTUM stores all data locally by default. No personal data is transmitted to our servers (we don't have any). When using cloud LLM providers, data processing occurs under your agreement with that provider. You have full control to export or delete all your data at any time by managing the ~/.scriptum/ directory.",
  },
];

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="mb-8 space-y-2">
        <h1 className="font-heading text-xl font-bold tracking-tight">
          Privacy & Security
        </h1>
        <p className="text-muted-foreground">
          Transparency about how SCRIPTUM handles your data and protects your
          research.
        </p>
      </div>

      <Alert className="mb-8 border-primary/20 bg-primary/5">
        <Shield className="h-4 w-4 text-primary" />
        <AlertTitle>Your research stays yours</AlertTitle>
        <AlertDescription>
          SCRIPTUM is designed with privacy as a core principle. All processing
          is local-first, API keys are encrypted, and you retain full control of
          your data.
        </AlertDescription>
      </Alert>

      <Accordion type="multiple" defaultValue={["data", "keys"]} className="space-y-3">
        {sections.map((section) => (
          <AccordionItem
            key={section.id}
            value={section.id}
            className="rounded-lg border px-4"
          >
            <AccordionTrigger className="hover:no-underline">
              <div className="flex items-center gap-3">
                <section.icon className="h-4 w-4 text-primary" />
                <span className="text-sm font-medium">{section.title}</span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
              {section.content}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>

      <Card className="mt-8">
        <CardContent className="flex items-center justify-between py-4">
          <div>
            <p className="font-medium">Questions or concerns?</p>
            <p className="text-sm text-muted-foreground">
              Open an issue on GitHub or review the source code directly.
            </p>
          </div>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
          >
            GitHub
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
