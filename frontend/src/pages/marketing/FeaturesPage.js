import { MarketingNav, MarketingFooter } from "@/components/Marketing";
import {
    ShieldCheck,
    Webhook,
    Plug,
    Lock,
    Building2,
    Send,
    Activity,
    KeyRound,
} from "lucide-react";

const features = [
    {
        icon: Building2,
        title: "Multi-tenancy",
        desc: "Strict tenant isolation enforced server-side. Every query is scoped to the authenticated principal's tenant.",
    },
    {
        icon: Plug,
        title: "Embedded Signup",
        desc: "Onboard businesses with Meta's official flow. Code-for-token exchange happens server-side and tokens are encrypted at rest.",
    },
    {
        icon: Webhook,
        title: "Webhook ingestion",
        desc: "HMAC-SHA256 verified, sub-second ACK, durable queue, async worker projection of statuses and inbound messages.",
    },
    {
        icon: Send,
        title: "Template messaging",
        desc: "Send templates with idempotency keys and per-phone-number rate limits. Status lifecycle: queued → sent → delivered/read/failed.",
    },
    {
        icon: ShieldCheck,
        title: "RBAC + TOTP MFA",
        desc: "Five roles built in (Super Admin, Tenant Owner, Tenant Admin, Agent, Viewer). TOTP MFA required for super-admins.",
    },
    {
        icon: Lock,
        title: "Encryption at rest",
        desc: "Business tokens encrypted with Fernet. Never logged, never returned to the frontend.",
    },
    {
        icon: KeyRound,
        title: "Rotating refresh tokens",
        desc: "httpOnly Secure SameSite cookies with rotation on every refresh. Tokens are revoked on password change.",
    },
    {
        icon: Activity,
        title: "Observability",
        desc: "Structured logs with trace IDs, Prometheus metrics, liveness + readiness probes.",
    },
];

export default function FeaturesPage() {
    return (
        <div className="min-h-screen bg-background">
            <MarketingNav />
            <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
                <div className="max-w-2xl">
                    <div className="text-sm font-medium text-primary">Features</div>
                    <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
                        Everything you need to run WhatsApp at scale
                    </h1>
                    <p className="mt-3 text-muted-foreground">
                        Phase 1 ships with the core pipeline production-hardened: ingestion,
                        outbound, multi-tenant identity, and observability.
                    </p>
                </div>
                <div className="mt-12 grid gap-6 md:grid-cols-2">
                    {features.map((f) => {
                        const Icon = f.icon;
                        return (
                            <div
                                key={f.title}
                                className="rounded-xl border bg-card p-6 shadow-[0_1px_0_hsl(214_20%_90%)_inset]"
                                data-testid="feature-card"
                            >
                                <Icon className="h-5 w-5 text-primary" />
                                <div className="mt-3 text-base font-semibold">{f.title}</div>
                                <div className="mt-1 text-sm text-muted-foreground">{f.desc}</div>
                            </div>
                        );
                    })}
                </div>
            </section>
            <MarketingFooter />
        </div>
    );
}
