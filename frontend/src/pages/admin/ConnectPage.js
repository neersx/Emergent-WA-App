import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Plug, ArrowRight, CheckCircle2, Loader2, AlertTriangle, ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

// Facebook JS SDK loader (idempotent)
function loadFbSdk() {
    return new Promise((resolve, reject) => {
        if (window.FB) return resolve(window.FB);
        window.fbAsyncInit = function () {
            resolve(window.FB);
        };
        // Load asynchronously
        const existing = document.getElementById("facebook-jssdk");
        if (existing) return; // Callback will resolve when the SDK finishes loading.
        const js = document.createElement("script");
        js.id = "facebook-jssdk";
        js.async = true;
        js.defer = true;
        js.crossOrigin = "anonymous";
        js.src = "https://connect.facebook.net/en_US/sdk.js";
        js.onerror = () => reject(new Error("Failed to load Facebook JS SDK"));
        document.body.appendChild(js);
    });
}

export default function ConnectPage() {
    const [launching, setLaunching] = useState(false);
    const [recent, setRecent] = useState([]);
    const [sys, setSys] = useState(null);
    const [sessionInfo, setSessionInfo] = useState(null);

    const refresh = async () => {
        try {
            const r = await api.get("/wabas");
            setRecent(r.data);
        } catch {}
    };

    useEffect(() => {
        (async () => {
            try {
                const [wr, sr] = await Promise.all([
                    api.get("/wabas"),
                    api.get("/system/info"),
                ]);
                setRecent(wr.data);
                setSys(sr.data);

                if (!sr.data.mock_mode && sr.data.meta_app_id_configured) {
                    // Initialise FB JS SDK now so the login popup is fast
                    try {
                        const FB = await loadFbSdk();
                        FB.init({
                            appId: sr.data.meta_app_id,
                            xfbml: false,
                            version: sr.data.meta_graph_api_version || "v21.0",
                        });
                        // Listen for Embedded Signup session events (contains waba_id + phone_number_id)
                        const onMessage = (event) => {
                            if (
                                event.origin !== "https://www.facebook.com" &&
                                event.origin !== "https://web.facebook.com"
                            )
                                return;
                            try {
                                const data = JSON.parse(event.data);
                                if (data.type === "WA_EMBEDDED_SIGNUP") {
                                    // eslint-disable-next-line no-console
                                    console.log("[embedded-signup event]", data);
                                    if (data.event === "FINISH" && data.data) {
                                        setSessionInfo(data.data);
                                    }
                                }
                            } catch (_) {}
                        };
                        window.addEventListener("message", onMessage);
                        return () => window.removeEventListener("message", onMessage);
                    } catch (e) {
                        console.warn("FB SDK init failed:", e);
                    }
                }
            } catch {}
        })();
    }, []);

    const launchSignupLive = () => {
        setLaunching(true);
        setSessionInfo(null);
        window.FB.login(
            (response) => {
                // response.authResponse.code is the short-lived server-side auth code
                if (response.authResponse && response.authResponse.code) {
                    const code = response.authResponse.code;
                    // Meta's Embedded Signup returns waba_id + phone_number_id via the
                    // postMessage event captured in `sessionInfo` (see the listener above).
                    // We wait a beat to make sure the message arrived.
                    setTimeout(async () => {
                        try {
                            const payload = { code };
                            const info = sessionInfo || {};
                            if (info.waba_id) payload.waba_id = info.waba_id;
                            if (info.phone_number_id)
                                payload.phone_number_id = info.phone_number_id;
                            if (info.business_id) payload.business_id = info.business_id;
                            const r = await api.post("/onboarding/exchange", payload);
                            toast.success(
                                `Connected WABA ${r.data.waba.waba_id} · phone ${r.data.phone_number.display_phone_number || r.data.phone_number.phone_number_id}`,
                            );
                            await refresh();
                        } catch (err) {
                            toast.error(
                                err?.response?.data?.detail ||
                                    "Onboarding failed. Ensure your Meta App has Advanced Access for whatsapp_business_management and whatsapp_business_messaging.",
                            );
                        } finally {
                            setLaunching(false);
                        }
                    }, 400);
                } else {
                    toast.error("Embedded Signup was cancelled or returned no auth code.");
                    setLaunching(false);
                }
            },
            {
                config_id: sys.meta_embedded_signup_config_id,
                response_type: "code",
                override_default_response_type: true,
                extras: { setup: {}, featureType: "", sessionInfoVersion: "3" },
            },
        );
    };

    const launchSignupMock = async () => {
        setLaunching(true);
        try {
            const code = `AUTHCODE_${Math.random().toString(36).slice(2, 10)}`;
            const r = await api.post("/onboarding/exchange", { code });
            toast.success(
                `Connected WABA ${r.data.waba.waba_id} · phone ${r.data.phone_number.display_phone_number}`,
            );
            await refresh();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Onboarding failed");
        } finally {
            setLaunching(false);
        }
    };

    const onLaunch = () => {
        if (!sys) {
            toast.error("System info not loaded yet");
            return;
        }
        if (sys.mock_mode) return launchSignupMock();
        if (!sys.meta_app_id_configured) {
            toast.error("META_APP_ID not configured — check Settings.");
            return;
        }
        if (!sys.meta_embedded_signup_config_id_configured) {
            toast.error("META_EMBEDDED_SIGNUP_CONFIG_ID not configured — check Settings.");
            return;
        }
        if (!window.FB) {
            toast.error("Facebook JS SDK not loaded yet. Refresh the page and try again.");
            return;
        }
        launchSignupLive();
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Connect WhatsApp</span>}
                title="Connect WhatsApp"
                description={
                    sys?.mock_mode
                        ? "Run the (mock) Meta Embedded Signup flow to attach a WhatsApp Business Account."
                        : "Launch the real Meta Embedded Signup dialog to attach a client's WhatsApp Business Account."
                }
            />
            <div className="grid gap-6 lg:grid-cols-2">
                <div className="rounded-xl border bg-card p-6">
                    <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <Plug className="h-5 w-5" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2 text-base font-semibold">
                                Embedded Signup
                                {sys && (
                                    <span
                                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${sys.mock_mode ? "bg-[hsl(38_92%_94%)] text-[hsl(38_92%_28%)]" : "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)]"}`}
                                    >
                                        {sys.mock_mode ? "MOCK" : "LIVE"}
                                    </span>
                                )}
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {sys?.mock_mode
                                    ? "In mock mode we skip the FB JS SDK and generate a synthetic auth code. The server-side exchange, WABA persistence, and webhook subscription all still run."
                                    : "Meta's Embedded Signup dialog opens in a popup. On success, we exchange the returned auth code server-side for a long-lived business access token, then subscribe your app to the WABA's webhooks and register the phone number."}
                            </p>
                        </div>
                    </div>
                    <div className="mt-6">
                        <Button
                            onClick={onLaunch}
                            disabled={launching || !sys}
                            data-testid="connect-launch-signup"
                        >
                            {launching ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Exchanging...
                                </>
                            ) : (
                                <>
                                    Launch Embedded Signup <ArrowRight className="ml-2 h-4 w-4" />
                                </>
                            )}
                        </Button>
                    </div>
                    <div className="mt-6 rounded-lg border bg-secondary/40 p-3 text-xs text-muted-foreground">
                        Tokens are encrypted at rest with Fernet and never returned to the
                        frontend. The server subscribes the app to the WABA&apos;s webhooks and
                        registers the phone number on your behalf.
                    </div>
                    {sys && !sys.mock_mode && (
                        <div className="mt-4 rounded-lg border bg-[hsl(38_92%_96%)] p-3 text-xs text-[hsl(38_92%_28%)]" data-testid="connect-live-checklist">
                            <div className="flex items-start gap-2">
                                <AlertTriangle className="mt-0.5 h-4 w-4" />
                                <div>
                                    <div className="font-semibold">Live-mode checklist</div>
                                    <ol className="mt-1 list-decimal space-y-1 pl-4">
                                        <li>
                                            Webhook callback URL in Meta App Dashboard =
                                            <code className="ml-1 font-mono text-[11px]">
                                                {typeof window !== "undefined" ? window.location.origin : ""}/api/webhooks/meta
                                            </code>
                                        </li>
                                        <li>Verify token in Meta Dashboard matches the server&apos;s <code className="font-mono text-[11px]">META_WEBHOOK_VERIFY_TOKEN</code>.</li>
                                        <li>App must have Advanced Access for whatsapp_business_management + whatsapp_business_messaging (or use approved testers).</li>
                                        <li>The Meta user launching the dialog must be an admin of the target Business Account.</li>
                                    </ol>
                                    <a
                                        href="https://developers.facebook.com/apps/"
                                        target="_blank"
                                        rel="noreferrer"
                                        className="mt-2 inline-flex items-center gap-1 text-[hsl(38_92%_28%)] underline"
                                    >
                                        Open Meta App Dashboard <ExternalLink className="h-3 w-3" />
                                    </a>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
                <div className="rounded-xl border bg-card p-6">
                    <div className="text-base font-semibold">Recently connected</div>
                    {recent.length === 0 ? (
                        <p className="mt-3 text-sm text-muted-foreground">
                            No WABAs yet. Use the button to launch the Embedded Signup dialog.
                        </p>
                    ) : (
                        <ul className="mt-4 space-y-3 text-sm" data-testid="connect-recent-list">
                            {recent.slice(0, 5).map((w) => (
                                <li
                                    key={w.waba_id}
                                    className="flex items-center justify-between rounded-lg border bg-background p-3"
                                >
                                    <div>
                                        <div className="flex items-center gap-2 font-medium">
                                            <CheckCircle2 className="h-4 w-4 text-[hsl(152_55%_35%)]" />
                                            {w.name}
                                        </div>
                                        <div className="text-xs text-muted-foreground">{w.waba_id}</div>
                                    </div>
                                    <Link to="/app/wabas" className="text-xs font-medium text-primary">
                                        View →
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </AppShell>
    );
}
