import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";
import { TrendingUp, MessageSquareText, CheckCircle2, XCircle, Users, Send } from "lucide-react";

const STATUS_COLORS = {
    queued: "#94a3b8",
    sent: "#0ea5e9",
    delivered: "#10b981",
    read: "#6366f1",
    failed: "#ef4444",
};

function StatCard({ icon: Icon, label, value, sub, testid }) {
    return (
        <div className="rounded-xl border bg-card p-5 shadow-[0_1px_0_hsl(214_20%_90%)_inset]" data-testid={testid}>
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <Icon className="h-4 w-4 text-primary" />
            </div>
            <div className="mt-3 text-2xl font-semibold tracking-tight" data-testid={`${testid}-value`}>{value}</div>
            {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
        </div>
    );
}

export default function AnalyticsPage() {
    const [days, setDays] = useState("14");
    const [overview, setOverview] = useState(null);
    const [series, setSeries] = useState([]);
    const [byTemplate, setByTemplate] = useState([]);
    const [byPhone, setByPhone] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = async (d = days) => {
        setLoading(true);
        try {
            const [ov, ts, bt, bp] = await Promise.all([
                api.get(`/analytics/overview?days=${d}`),
                api.get(`/analytics/timeseries?days=${d}`),
                api.get(`/analytics/by-template?days=${d}`),
                api.get(`/analytics/by-phone?days=${d}`),
            ]);
            setOverview(ov.data);
            setSeries(ts.data);
            setByTemplate(bt.data);
            setByPhone(bp.data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load(days);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [days]);

    const statusPie = overview
        ? Object.entries(overview.status_breakdown || {}).map(([k, v]) => ({
              name: k,
              value: v,
              color: STATUS_COLORS[k] || "#94a3b8",
          }))
        : [];

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Analytics</span>}
                title="Analytics"
                description="Message volume, delivery rates, and conversation activity over time."
                actions={
                    <Select value={days} onValueChange={setDays}>
                        <SelectTrigger className="w-40" data-testid="analytics-range-select">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7">Last 7 days</SelectItem>
                            <SelectItem value="14">Last 14 days</SelectItem>
                            <SelectItem value="30">Last 30 days</SelectItem>
                            <SelectItem value="90">Last 90 days</SelectItem>
                        </SelectContent>
                    </Select>
                }
            />
            {loading || !overview ? (
                <div className="grid gap-4 md:grid-cols-4">
                    {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="h-28 animate-pulse rounded-xl border bg-card" />
                    ))}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Stat cards */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <StatCard icon={MessageSquareText} label="Total messages" value={overview.total_messages} sub={`${overview.outbound} out · ${overview.inbound} in`} testid="analytics-stat-total" />
                        <StatCard icon={CheckCircle2} label="Delivered" value={overview.delivered} sub={`${(overview.delivery_rate * 100).toFixed(1)}% delivery rate`} testid="analytics-stat-delivered" />
                        <StatCard icon={XCircle} label="Failed" value={overview.failed} sub="In window" testid="analytics-stat-failed" />
                        <StatCard icon={Users} label="Conversations" value={overview.conversations} sub={`${overview.conversations_open_window} in service window`} testid="analytics-stat-conversations" />
                    </div>

                    {/* Time series */}
                    <div className="rounded-xl border bg-card p-5">
                        <div className="mb-4 flex items-center justify-between">
                            <div>
                                <div className="text-base font-semibold">Messages over time</div>
                                <div className="text-xs text-muted-foreground">Daily counts by direction and final status</div>
                            </div>
                            <TrendingUp className="h-4 w-4 text-primary" />
                        </div>
                        <div className="h-72" data-testid="analytics-timeseries-chart">
                            <ResponsiveContainer>
                                <LineChart data={series}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                    <Tooltip />
                                    <Legend />
                                    <Line type="monotone" dataKey="outbound" stroke="#0d9488" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="inbound" stroke="#6366f1" strokeWidth={2} dot={false} />
                                    <Line type="monotone" dataKey="delivered" stroke="#10b981" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                                    <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    <div className="grid gap-4 lg:grid-cols-2">
                        {/* Status breakdown pie */}
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold">Status breakdown</div>
                            <div className="text-xs text-muted-foreground">All messages in selected window</div>
                            <div className="mt-4 h-64" data-testid="analytics-status-pie">
                                {statusPie.length === 0 ? (
                                    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No data</div>
                                ) : (
                                    <ResponsiveContainer>
                                        <PieChart>
                                            <Pie data={statusPie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={90} paddingAngle={2}>
                                                {statusPie.map((s, i) => (
                                                    <Cell key={i} fill={s.color} />
                                                ))}
                                            </Pie>
                                            <Tooltip />
                                            <Legend />
                                        </PieChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                        </div>

                        {/* Top templates */}
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold">Top templates</div>
                            <div className="text-xs text-muted-foreground">Sends · delivery rate</div>
                            <div className="mt-4 h-64" data-testid="analytics-template-chart">
                                {byTemplate.length === 0 ? (
                                    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No data</div>
                                ) : (
                                    <ResponsiveContainer>
                                        <BarChart data={byTemplate} layout="vertical" margin={{ left: 20 }}>
                                            <CartesianGrid stroke="#e5e7eb" />
                                            <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                                            <YAxis type="category" dataKey="template_name" width={130} tick={{ fontSize: 11 }} />
                                            <Tooltip />
                                            <Bar dataKey="sent" fill="#0d9488" radius={[0, 4, 4, 0]} />
                                            <Bar dataKey="delivered" fill="#10b981" radius={[0, 4, 4, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* By phone */}
                    <div className="rounded-xl border bg-card p-5">
                        <div className="text-base font-semibold">By phone number</div>
                        <div className="text-xs text-muted-foreground">Activity per connected number</div>
                        {byPhone.length === 0 ? (
                            <div className="py-10 text-center text-sm text-muted-foreground">No data</div>
                        ) : (
                            <div className="mt-4 overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="text-xs text-muted-foreground">
                                        <tr><th className="py-2 text-left">Phone</th><th className="text-left">Name</th><th className="text-right">Outbound</th><th className="text-right">Inbound</th><th className="text-right">Total</th></tr>
                                    </thead>
                                    <tbody>
                                        {byPhone.map((p) => (
                                            <tr key={p.phone_number_id} className="border-t" data-testid="analytics-phone-row">
                                                <td className="py-2 font-medium">{p.display}</td>
                                                <td>{p.verified_name || "—"}</td>
                                                <td className="text-right">{p.outbound}</td>
                                                <td className="text-right">{p.inbound}</td>
                                                <td className="text-right font-semibold">{p.outbound + p.inbound}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </AppShell>
    );
}
