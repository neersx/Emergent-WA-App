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
    Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
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
import { TrendingUp, MessageSquareText, CheckCircle2, XCircle, Users, DollarSign, Receipt } from "lucide-react";

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
    const [costSummary, setCostSummary] = useState(null);
    const [dailyUsage, setDailyUsage] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = async (d = days) => {
        setLoading(true);
        try {
            const [ov, ts, bt, bp, cs, du] = await Promise.all([
                api.get(`/analytics/overview?days=${d}`),
                api.get(`/analytics/timeseries?days=${d}`),
                api.get(`/analytics/by-template?days=${d}`),
                api.get(`/analytics/by-phone?days=${d}`),
                api.get(`/analytics/usage/cost?days=${d}`),
                api.get(`/analytics/usage/daily?days=${d}`),
            ]);
            setOverview(ov.data);
            setSeries(ts.data);
            setByTemplate(bt.data);
            setByPhone(bp.data);
            setCostSummary(cs.data);
            setDailyUsage(du.data);
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

    // Aggregate daily usage into chart data
    const dailyByDate = dailyUsage.reduce((acc, row) => {
        const d = row.day;
        if (!acc[d]) acc[d] = { date: d, marketing: 0, utility: 0, authentication: 0, service: 0, cost: 0 };
        acc[d][row.category.toLowerCase()] = (acc[d][row.category.toLowerCase()] || 0) + row.delivered_count;
        acc[d].cost = (acc[d].cost || 0) + row.cost_amount;
        return acc;
    }, {});
    const dailyChartData = Object.values(dailyByDate).sort((a, b) => a.date.localeCompare(b.date));

    const CATEGORY_COLORS = {
        marketing: "#ef4444",
        utility: "#0ea5e9",
        authentication: "#8b5cf6",
        service: "#10b981",
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Analytics</span>}
                title="Analytics"
                description="Message volume, delivery rates, conversation activity, and usage costs."
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
                <Tabs defaultValue="messages">
                    <TabsList className="mb-4">
                        <TabsTrigger value="messages">Messages</TabsTrigger>
                        <TabsTrigger value="cost" data-testid="analytics-cost-tab">Usage & Cost</TabsTrigger>
                    </TabsList>

                    {/* ─── Messages tab ─────────────────────────────────── */}
                    <TabsContent value="messages">
                        <div className="space-y-6">
                            <div className="grid gap-4 md:grid-cols-4">
                                <StatCard icon={MessageSquareText} label="Total messages" value={overview.total_messages} sub={`${overview.outbound} out · ${overview.inbound} in`} testid="analytics-stat-total" />
                                <StatCard icon={CheckCircle2} label="Delivered" value={overview.delivered} sub={`${(overview.delivery_rate * 100).toFixed(1)}% delivery rate`} testid="analytics-stat-delivered" />
                                <StatCard icon={XCircle} label="Failed" value={overview.failed} sub="Failed sends" testid="analytics-stat-failed" />
                                <StatCard icon={Users} label="Conversations" value={overview.conversations} sub={`${overview.conversations_open_window} in service window`} testid="analytics-stat-conversations" />
                            </div>

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
                                                        {statusPie.map((s, i) => <Cell key={i} fill={s.color} />)}
                                                    </Pie>
                                                    <Tooltip />
                                                    <Legend />
                                                </PieChart>
                                            </ResponsiveContainer>
                                        )}
                                    </div>
                                </div>

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
                    </TabsContent>

                    {/* ─── Usage & Cost tab ─────────────────────────────── */}
                    <TabsContent value="cost">
                        <div className="space-y-6">
                            {/* Summary cards */}
                            <div className="grid gap-4 md:grid-cols-3">
                                <StatCard icon={DollarSign} label="Estimated total cost" value={`$${(costSummary?.total_cost_usd || 0).toFixed(4)}`} sub="USD, approximate" testid="analytics-stat-cost" />
                                <StatCard icon={Receipt} label="Billable deliveries" value={costSummary?.by_category?.reduce((s, c) => s + c.billable_count, 0) || 0} sub="Charged messages" testid="analytics-stat-billable" />
                                <StatCard icon={CheckCircle2} label="Free deliveries" value={costSummary?.by_category?.reduce((s, c) => s + c.free_count, 0) || 0} sub="In service window" testid="analytics-stat-free" />
                            </div>

                            {/* Cost by category */}
                            <div className="rounded-xl border bg-card p-5">
                                <div className="text-base font-semibold">Cost by category</div>
                                <div className="text-xs text-muted-foreground mb-4">Estimated USD cost per message category</div>
                                {(!costSummary?.by_category?.length) ? (
                                    <div className="py-8 text-center text-sm text-muted-foreground">No cost data yet. Data appears when messages are delivered.</div>
                                ) : (
                                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                        {costSummary.by_category.map(cat => (
                                            <div key={cat.category} className="rounded-lg border p-4" data-testid="analytics-cost-category">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-xs font-medium uppercase text-muted-foreground">{cat.category}</span>
                                                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[cat.category] || "#94a3b8" }} />
                                                </div>
                                                <div className="text-2xl font-semibold">${cat.cost_amount.toFixed(4)}</div>
                                                <div className="mt-1 text-xs text-muted-foreground">
                                                    {cat.delivered_count} delivered · {cat.billable_count} billable · {cat.free_count} free
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Daily volume by category */}
                            {dailyChartData.length > 0 && (
                                <div className="rounded-xl border bg-card p-5">
                                    <div className="text-base font-semibold">Daily delivery volume by category</div>
                                    <div className="text-xs text-muted-foreground mb-4">Delivered message counts</div>
                                    <div className="h-64">
                                        <ResponsiveContainer>
                                            <BarChart data={dailyChartData}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                                                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="marketing" stackId="a" fill={CATEGORY_COLORS.marketing} />
                                                <Bar dataKey="utility" stackId="a" fill={CATEGORY_COLORS.utility} />
                                                <Bar dataKey="authentication" stackId="a" fill={CATEGORY_COLORS.authentication} />
                                                <Bar dataKey="service" stackId="a" fill={CATEGORY_COLORS.service} radius={[4, 4, 0, 0]} />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            )}

                            {/* Daily rollup table */}
                            {dailyUsage.length > 0 && (
                                <div className="rounded-xl border bg-card p-5">
                                    <div className="text-base font-semibold mb-3">Daily usage rollup</div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-sm">
                                            <thead className="text-xs text-muted-foreground border-b">
                                                <tr>
                                                    <th className="py-2 text-left">Date</th>
                                                    <th className="text-left">Category</th>
                                                    <th className="text-right">Delivered</th>
                                                    <th className="text-right">Billable</th>
                                                    <th className="text-right">Free</th>
                                                    <th className="text-right">Est. Cost (USD)</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {dailyUsage.slice(0, 30).map((row, i) => (
                                                    <tr key={i} className="border-t">
                                                        <td className="py-1.5 font-mono text-xs">{row.day}</td>
                                                        <td>
                                                            <span className="inline-flex items-center gap-1 text-xs capitalize">
                                                                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[row.category] || "#94a3b8" }} />
                                                                {row.category}
                                                            </span>
                                                        </td>
                                                        <td className="text-right text-xs">{row.delivered_count}</td>
                                                        <td className="text-right text-xs">{row.billable_count}</td>
                                                        <td className="text-right text-xs">{row.free_count}</td>
                                                        <td className="text-right font-mono text-xs">${row.cost_amount.toFixed(4)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}
                        </div>
                    </TabsContent>
                </Tabs>
            )}
        </AppShell>
    );
}
