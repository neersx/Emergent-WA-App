import { Link } from "react-router-dom";
import { MarketingNav, MarketingFooter } from "@/components/Marketing";
import { Button } from "@/components/ui/button";
import { Check } from "lucide-react";

const tiers = [
    {
        name: "Starter",
        price: "$0",
        period: "/mo",
        desc: "For evaluating the platform in mock mode.",
        features: [
            "1 tenant",
            "Mock Meta integration",
            "Template sends + idempotency",
            "Webhook simulation",
        ],
        cta: "Start free",
    },
    {
        name: "Pro",
        price: "$199",
        period: "/mo",
        desc: "For production rollouts with real Meta credentials.",
        features: [
            "Unlimited tenants",
            "Real Meta API",
            "Embedded Signup",
            "TOTP MFA + RBAC",
            "Encrypted token storage",
        ],
        cta: "Get Pro",
        popular: true,
    },
    {
        name: "Scale",
        price: "Custom",
        period: "",
        desc: "For Tech Providers running large fleets of WABAs.",
        features: [
            "Dedicated worker pool",
            "Custom rate limits",
            "SSO",
            "SLA + priority support",
        ],
        cta: "Contact sales",
    },
];

export default function PricingPage() {
    return (
        <div className="min-h-screen bg-background">
            <MarketingNav />
            <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
                <div className="max-w-2xl">
                    <div className="text-sm font-medium text-primary">Pricing</div>
                    <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
                        Simple, predictable pricing
                    </h1>
                    <p className="mt-3 text-muted-foreground">
                        Start in mock mode for free. Upgrade when you connect real Meta credentials.
                    </p>
                </div>
                <div className="mt-12 grid gap-6 lg:grid-cols-3">
                    {tiers.map((t) => (
                        <div
                            key={t.name}
                            data-testid="pricing-tier-card"
                            className={`relative rounded-2xl border bg-card p-6 ${
                                t.popular ? "ring-2 ring-primary/30 bg-primary/5" : ""
                            }`}
                        >
                            {t.popular && (
                                <div className="absolute -top-3 left-6 inline-flex items-center rounded-full bg-primary px-2.5 py-0.5 text-xs font-medium text-primary-foreground">
                                    Most popular
                                </div>
                            )}
                            <div className="text-sm font-semibold">{t.name}</div>
                            <div className="mt-3 text-4xl font-semibold tracking-tight">
                                {t.price}
                                <span className="text-base font-normal text-muted-foreground">{t.period}</span>
                            </div>
                            <p className="mt-2 text-sm text-muted-foreground">{t.desc}</p>
                            <ul className="mt-6 space-y-3 text-sm">
                                {t.features.map((f) => (
                                    <li key={f} className="flex items-start gap-2">
                                        <Check className="mt-0.5 h-4 w-4 text-primary" />
                                        <span>{f}</span>
                                    </li>
                                ))}
                            </ul>
                            <Button asChild className="mt-8 w-full" data-testid="pricing-tier-cta-button">
                                <Link to="/register">{t.cta}</Link>
                            </Button>
                        </div>
                    ))}
                </div>
            </section>
            <MarketingFooter />
        </div>
    );
}
