import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import { Plug, Smartphone, MessageSquareText, CheckCircle2, Send, Eye } from "lucide-react";

function StatCard({ icon: Icon, label, value, testid }) {
    return (
        <div
            className="rounded-xl border bg-card p-5 shadow-[0_1px_0_hsl(214_20%_90%)_inset]"
            data-testid={testid}
        >
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <Icon className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight" data-testid={`${testid}-value`}>
                {value}
            </div>
        </div>
    );
}

export default function DashboardPage() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const r = await api.get("/dashboard");
                setStats(r.data);
            } catch (e) {
                setStats({
                    waba_count: 0,
                    phone_count: 0,
                    message_count: 0,
                    sent_count: 0,
                    delivered_count: 0,
                    read_count: 0,
                });
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Dashboard</span>}
                title="Dashboard"
                description="Overview of your WABAs, phone numbers, and message activity."
                actions={
                    <Button asChild data-testid="dashboard-connect-cta">
                        <Link to="/app/connect">
                            <Plug className="mr-2 h-4 w-4" /> Connect WhatsApp
                        </Link>
                    </Button>
                }
            />
            {loading ? (
                <div className="grid gap-4 md:grid-cols-3">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-28 animate-pulse rounded-xl border bg-card" />
                    ))}
                </div>
            ) : (
                <div className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-3">
                        <StatCard icon={Smartphone} label="WABAs" value={stats.waba_count} testid="stat-wabas" />
                        <StatCard icon={Smartphone} label="Phone numbers" value={stats.phone_count} testid="stat-phones" />
                        <StatCard icon={MessageSquareText} label="Total messages" value={stats.message_count} testid="stat-messages" />
                    </div>
                    <div className="grid gap-4 md:grid-cols-3">
                        <StatCard icon={Send} label="Sent" value={stats.sent_count} testid="stat-sent" />
                        <StatCard icon={CheckCircle2} label="Delivered" value={stats.delivered_count} testid="stat-delivered" />
                        <StatCard icon={Eye} label="Read" value={stats.read_count} testid="stat-read" />
                    </div>
                    <div className="rounded-xl border bg-card p-6">
                        <div className="text-base font-semibold">Get started</div>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Run through the full mock flow in under 2 minutes.
                        </p>
                        <ol className="mt-4 space-y-3 text-sm">
                            <li className="flex items-start gap-3">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">1</span>
                                <div>
                                    <Link to="/app/connect" className="font-medium text-primary">Connect WhatsApp</Link>
                                    {" — launch the mock Embedded Signup to create a WABA + phone number."}
                                </div>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">2</span>
                                <div>
                                    <Link to="/app/send" className="font-medium text-primary">Send a template</Link>
                                    {" — it will be recorded with status queued → sent."}
                                </div>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">3</span>
                                <div>
                                    <Link to="/app/messages" className="font-medium text-primary">Simulate delivery</Link>
                                    {" — from the message log, advance status to delivered / read."}
                                </div>
                            </li>
                        </ol>
                    </div>
                </div>
            )}
        </AppShell>
    );
}
