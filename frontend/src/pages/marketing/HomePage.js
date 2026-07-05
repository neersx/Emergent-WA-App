import { Link } from "react-router-dom";
import { MarketingNav, MarketingFooter } from "@/components/Marketing";
import { Button } from "@/components/ui/button";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion";
import {
    ArrowRight,
    ShieldCheck,
    Zap,
    Webhook,
    BarChart3,
    Lock,
    Building2,
    Sparkles,
    Plug,
    CheckCircle2,
} from "lucide-react";

const features = [
    {
        title: "Multi-tenant by design",
        desc: "One platform, many client businesses. Strict tenant isolation enforced server-side.",
        icon: Building2,
        span: "md:col-span-7",
    },
    {
        title: "Webhook ingestion that won't drop events",
        desc: "Sub-second ACK with signature verification + durable queue + idempotent worker projection.",
        icon: Webhook,
        span: "md:col-span-5",
    },
    {
        title: "Embedded Signup",
        desc: "Onboard clients in minutes with Meta's official flow.",
        icon: Plug,
        span: "md:col-span-4",
    },
    {
        title: "TOTP MFA + RBAC",
        desc: "Required for super-admins. Five roles out of the box.",
        icon: ShieldCheck,
        span: "md:col-span-4",
    },
    {
        title: "Encrypted at rest",
        desc: "Business tokens are Fernet-encrypted and never returned to the frontend.",
        icon: Lock,
        span: "md:col-span-4",
    },
];

const faqs = [
    {
        q: "Do I need real Meta credentials to evaluate?",
        a: "No. The platform ships with a mock mode that simulates the Embedded Signup exchange, outbound template sends, and webhook delivery events end-to-end.",
    },
    {
        q: "How is tenant isolation enforced?",
        a: "Every tenant-owned record carries a tenant_id and every query is filtered by the principal's tenant_id derived from the access token. Cross-tenant access returns 404.",
    },
    {
        q: "What happens if a webhook signature is invalid?",
        a: "The request is rejected with HTTP 401 and nothing is written to the database or the queue. Only signature-verified events are processed.",
    },
    {
        q: "How are duplicate sends prevented?",
        a: "Send requests accept an idempotency_key. Repeated sends with the same key return the original message instead of creating a duplicate.",
    },
    {
        q: "Is the worker process separate from the API?",
        a: "Yes. The worker runs as a dedicated asyncio task with its own job loop, claiming jobs from a durable MongoDB-backed queue with atomic visibility timeouts.",
    },
    {
        q: "Can I bring my own SMTP / Meta credentials later?",
        a: "Yes. Mock mode is a single config flag; turn it off and supply real META_APP_SECRET, META_APP_ID, embedded signup config id and a webhook verify token.",
    },
];

export default function HomePage() {
    return (
        <div className="min-h-screen bg-background">
            <MarketingNav />

            {/* Hero */}
            <section className="hero-gradient relative overflow-hidden">
                <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:px-8 lg:py-28">
                    <div>
                        <div className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
                            <Sparkles className="h-3.5 w-3.5 text-primary" />
                            Phase 1 MVP · Mock mode included
                        </div>
                        <h1
                            className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl"
                            data-testid="hero-title"
                        >
                            The control plane for the
                            <span className="block text-primary">WhatsApp Business Platform.</span>
                        </h1>
                        <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
                            Onboard businesses via Embedded Signup, manage their WABAs and phone
                            numbers, send templated messages, and ingest delivery webhooks—all
                            with multi-tenant isolation, MFA, and a durable async worker.
                        </p>
                        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                            <Button asChild size="lg" data-testid="hero-cta-get-started">
                                <Link to="/register">
                                    Get started <ArrowRight className="ml-2 h-4 w-4" />
                                </Link>
                            </Button>
                            <Button asChild size="lg" variant="outline" data-testid="hero-cta-signin">
                                <Link to="/login">Sign in</Link>
                            </Button>
                        </div>
                        <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                                <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> No card required
                            </div>
                            <div className="flex items-center gap-1.5">
                                <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Mock mode by default
                            </div>
                        </div>
                    </div>
                    {/* Preview card */}
                    <div className="relative">
                        <div className="rounded-2xl border bg-card p-5 shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]">
                            <div className="flex items-center justify-between">
                                <div className="text-xs font-medium text-muted-foreground">Message log</div>
                                <span className="rounded-full border bg-[hsl(38_92%_95%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(38_92%_28%)]">MOCK</span>
                            </div>
                            <div className="mt-4 divide-y">
                                {[
                                    { to: "+1 555 0101", template: "order_shipped", status: "delivered" },
                                    { to: "+1 555 0142", template: "otp_verify", status: "read" },
                                    { to: "+1 555 0177", template: "appointment_reminder", status: "sent" },
                                    { to: "+1 555 0198", template: "welcome_v2", status: "queued" },
                                ].map((m, i) => (
                                    <div key={i} className="flex items-center justify-between py-2.5 text-sm">
                                        <div>
                                            <div className="font-medium">{m.to}</div>
                                            <div className="text-xs text-muted-foreground">{m.template}</div>
                                        </div>
                                        <span className={
                                            "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize " +
                                            ({
                                                queued: "bg-[hsl(215_20%_94%)] text-[hsl(215_25%_25%)] border-[hsl(215_18%_86%)]",
                                                sent: "bg-[hsl(199_95%_94%)] text-[hsl(199_80%_28%)] border-[hsl(199_70%_86%)]",
                                                delivered: "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]",
                                                read: "bg-[hsl(238_85%_95%)] text-[hsl(238_55%_35%)] border-[hsl(238_55%_88%)]",
                                            }[m.status])
                                        }>{m.status}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="absolute -right-4 top-6 hidden rounded-xl border bg-card p-3 text-xs shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)] lg:block">
                            <div className="flex items-center gap-2">
                                <Zap className="h-3.5 w-3.5 text-primary" />
                                Webhook ACK in <span className="font-semibold">&lt;1s</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features bento */}
            <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
                <div className="mb-10 max-w-2xl">
                    <div className="text-sm font-medium text-primary">Why this platform</div>
                    <h2 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                        Built for Tech Providers shipping at scale
                    </h2>
                    <p className="mt-3 text-muted-foreground">
                        Every piece of the pipeline is hardened: signature-verified ingestion,
                        idempotent sends, encrypted token storage, and strict tenant isolation.
                    </p>
                </div>
                <div className="grid gap-4 md:grid-cols-12">
                    {features.map((f) => {
                        const Icon = f.icon;
                        return (
                            <div
                                key={f.title}
                                className={`col-span-12 ${f.span} rounded-xl border bg-card p-6 shadow-[0_1px_0_hsl(214_20%_90%)_inset] transition-shadow hover:shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]`}
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

            {/* Stats */}
            <section className="border-y bg-card">
                <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-12 text-center sm:px-6 md:grid-cols-4 lg:px-8">
                    {[
                        { v: "<1s", k: "Webhook ACK target" },
                        { v: "5", k: "Built-in RBAC roles" },
                        { v: "100%", k: "Tenant-isolated queries" },
                        { v: "AES-128", k: "Token-at-rest encryption" },
                    ].map((s) => (
                        <div key={s.k}>
                            <div className="text-3xl font-semibold tracking-tight text-primary">{s.v}</div>
                            <div className="mt-1 text-xs text-muted-foreground">{s.k}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* FAQ preview */}
            <section className="mx-auto max-w-6xl px-4 py-20 sm:px-6 lg:px-8">
                <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">FAQ</h2>
                <div className="mt-8 grid gap-6 lg:grid-cols-2">
                    <Accordion type="multiple" className="space-y-3">
                        {faqs.slice(0, 3).map((f, i) => (
                            <AccordionItem
                                key={i}
                                value={`a-${i}`}
                                className="rounded-xl border bg-card px-4"
                                data-testid="faq-accordion-item"
                            >
                                <AccordionTrigger className="py-4 text-left text-sm font-medium">
                                    {f.q}
                                </AccordionTrigger>
                                <AccordionContent className="pb-4 text-sm text-muted-foreground">
                                    {f.a}
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                    <Accordion type="multiple" className="space-y-3">
                        {faqs.slice(3).map((f, i) => (
                            <AccordionItem
                                key={i}
                                value={`b-${i}`}
                                className="rounded-xl border bg-card px-4"
                                data-testid="faq-accordion-item"
                            >
                                <AccordionTrigger className="py-4 text-left text-sm font-medium">
                                    {f.q}
                                </AccordionTrigger>
                                <AccordionContent className="pb-4 text-sm text-muted-foreground">
                                    {f.a}
                                </AccordionContent>
                            </AccordionItem>
                        ))}
                    </Accordion>
                </div>
            </section>

            {/* Final CTA */}
            <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6 lg:px-8">
                <div className="hero-gradient flex flex-col items-center justify-between gap-6 rounded-2xl border bg-card p-10 text-center sm:flex-row sm:text-left">
                    <div>
                        <h3 className="text-2xl font-semibold tracking-tight">Ready to onboard your first business?</h3>
                        <p className="mt-1 text-muted-foreground">Spin up a tenant in mock mode and ship the full flow in minutes.</p>
                    </div>
                    <Button asChild size="lg" data-testid="home-final-cta">
                        <Link to="/register">
                            Create your tenant <ArrowRight className="ml-2 h-4 w-4" />
                        </Link>
                    </Button>
                </div>
            </section>

            <MarketingFooter />
        </div>
    );
}
