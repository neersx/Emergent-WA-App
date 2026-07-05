import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import { Settings as SettingsIcon, AlertCircle, CheckCircle2 } from "lucide-react";

function ConfigRow({ label, value, sub }) {
    return (
        <div className="flex items-start justify-between border-b py-3 last:border-b-0">
            <div>
                <div className="text-sm font-medium">{label}</div>
                {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
            </div>
            <div className="text-right text-sm">{value}</div>
        </div>
    );
}

function Pill({ ok, children }) {
    return (
        <span
            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${ok ? "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]" : "bg-[hsl(38_92%_94%)] text-[hsl(38_92%_28%)] border-[hsl(38_92%_84%)]"}`}
        >
            {ok ? <CheckCircle2 className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />} {children}
        </span>
    );
}

export default function SettingsPage() {
    const [info, setInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const r = await api.get("/system/info");
                setInfo(r.data);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Settings</span>}
                title="Platform Settings"
                description="Connection mode, Meta credentials status, and runtime configuration."
            />
            {loading || !info ? (
                <div className="h-64 animate-pulse rounded-xl border bg-card" />
            ) : (
                <div className="grid gap-6 lg:grid-cols-2">
                    <div className="rounded-xl border bg-card p-6">
                        <div className="flex items-start gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                <SettingsIcon className="h-5 w-5" />
                            </div>
                            <div>
                                <div className="text-base font-semibold">Meta connection</div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    {info.mock_mode
                                        ? "All Meta Graph calls return stubbed responses. Switch to live mode by providing real credentials below and setting META_MOCK_MODE=false."
                                        : "Live mode is enabled. The app makes real Meta Graph calls."}
                                </p>
                            </div>
                        </div>
                        <div className="mt-5" data-testid="settings-meta-section">
                            <ConfigRow
                                label="Mode"
                                value={
                                    info.mock_mode ? (
                                        <Pill ok={false}>MOCK MODE</Pill>
                                    ) : (
                                        <Pill ok={true}>LIVE</Pill>
                                    )
                                }
                                sub="Toggle via META_MOCK_MODE env var."
                            />
                            <ConfigRow
                                label="Graph API version"
                                value={<span className="font-mono text-xs">{info.meta_graph_api_version}</span>}
                            />
                            <ConfigRow
                                label="META_APP_ID"
                                value={<Pill ok={info.meta_app_id_configured}>{info.meta_app_id_configured ? "Configured" : "Placeholder"}</Pill>}
                                sub="Required for live mode."
                            />
                            <ConfigRow
                                label="META_EMBEDDED_SIGNUP_CONFIG_ID"
                                value={<Pill ok={info.meta_embedded_signup_config_id_configured}>{info.meta_embedded_signup_config_id_configured ? "Configured" : "Placeholder"}</Pill>}
                                sub="Required for real embedded signup."
                            />
                            <ConfigRow
                                label="META_WEBHOOK_VERIFY_TOKEN"
                                value={<Pill ok={info.meta_webhook_verify_token_configured}>{info.meta_webhook_verify_token_configured ? "Configured" : "Placeholder"}</Pill>}
                                sub="Required for live webhook verification."
                            />
                        </div>
                    </div>
                    <div className="rounded-xl border bg-card p-6">
                        <div className="text-base font-semibold">Runtime</div>
                        <p className="mt-1 text-sm text-muted-foreground">Tunables loaded at startup from env.</p>
                        <div className="mt-5">
                            <ConfigRow label="App" value={`${info.app} v${info.version}`} />
                            <ConfigRow label="Worker" value={<Pill ok={info.worker_enabled}>{info.worker_enabled ? "Running" : "Disabled"}</Pill>} />
                            <ConfigRow label="Access token TTL" value={`${info.access_token_ttl_minutes} min`} />
                            <ConfigRow label="Refresh token TTL" value={`${info.refresh_token_ttl_days} days`} />
                            <ConfigRow label="Send rate limit" value={`${info.send_rate_limit_per_min} / min / phone`} />
                        </div>
                    </div>
                    <div className="rounded-xl border bg-[hsl(38_92%_96%)] p-6 lg:col-span-2">
                        <div className="flex items-start gap-3">
                            <AlertCircle className="mt-0.5 h-5 w-5 text-[hsl(38_92%_28%)]" />
                            <div className="text-sm text-[hsl(38_92%_28%)]">
                                <div className="font-semibold">Switching to live mode</div>
                                <ol className="mt-2 list-decimal space-y-1 pl-5">
                                    <li>Set <code className="font-mono">META_MOCK_MODE=false</code> in <code className="font-mono">/app/backend/.env</code>.</li>
                                    <li>Provide <code className="font-mono">META_APP_ID</code>, <code className="font-mono">META_APP_SECRET</code>, <code className="font-mono">META_EMBEDDED_SIGNUP_CONFIG_ID</code>, and <code className="font-mono">META_WEBHOOK_VERIFY_TOKEN</code>.</li>
                                    <li>Restart backend: <code className="font-mono">sudo supervisorctl restart backend</code>.</li>
                                    <li>Ensure your Meta app has <strong>Advanced Access</strong> for whatsapp_business_management and whatsapp_business_messaging.</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </AppShell>
    );
}
