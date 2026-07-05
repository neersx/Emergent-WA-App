import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import {
    DollarSign, Receipt, CheckCircle2, TrendingUp, TrendingDown,
    Download, FileText, BarChart3,
} from "lucide-react";

const CATEGORY_COLORS = {
    marketing: "#ef4444",
    utility: "#0ea5e9",
    authentication: "#8b5cf6",
    service: "#10b981",
};

function StatCard({ icon: Icon, label, value, sub, trend, testid }) {
    return (
        <div className="rounded-xl border bg-card p-5" data-testid={testid}>
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <Icon className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-semibold tracking-tight">{value}</div>
            {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
            {trend !== undefined && (
                <div className={`mt-1 flex items-center gap-1 text-xs ${trend >= 0 ? "text-destructive" : "text-[hsl(152_55%_35%)]"}`}>
                    {trend >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {Math.abs(trend).toFixed(1)}% vs last month
                </div>
            )}
        </div>
    );
}

export default function UsagePage() {
    const [days, setDays] = useState("30");
    const [costData, setCostData] = useState(null);
    const [daily, setDaily] = useState([]);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    const load = async (d = days) => {
        setLoading(true);
        try {
            const [cd, dl] = await Promise.all([
                api.get(`/analytics/usage/cost?days=${d}`),
                api.get(`/analytics/usage/daily?days=${d}`),
            ]);
            setCostData(cd.data);
            setDaily(dl.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(days); }, [days]); // eslint-disable-line

    const handleExport = async (format) => {
        setExporting(true);
        try {
            const resp = await api.get(`/analytics/export?format=${format}`, {
                responseType: "blob",
            });
            const url = URL.createObjectURL(resp.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `usage.${format === "xlsx" ? "xlsx" : "csv"}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
        } finally {
            setExporting(false);
        }
    };

    // Build daily cost chart data
    const dailyCostMap = daily.reduce((acc, row) => {
        const d = row.day;
        acc[d] = (acc[d] || 0) + row.cost_amount;
        return acc;
    }, {});
    const costSeries = Object.entries(dailyCostMap).sort().map(([d, c]) => ({ date: d, cost: +c.toFixed(4) }));

    // Build category pie
    const catPie = (costData?.by_category || []).map(c => ({
        name: c.category,
        value: c.delivered_count,
        color: CATEGORY_COLORS[c.category] || "#94a3b8",
    }));

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Usage & Billing</span>}
                title="Usage & Billing"
                description="Per-message cost tracking, billable vs free breakdown, and cost by category."
                actions={
                    <div className="flex items-center gap-2">
                        <Select value={days} onValueChange={setDays}>
                            <SelectTrigger className="w-36" data-testid="usage-range-select">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="7">Last 7 days</SelectItem>
                                <SelectItem value="30">Last 30 days</SelectItem>
                                <SelectItem value="60">Last 60 days</SelectItem>
                                <SelectItem value="90">Last 90 days</SelectItem>
                            </SelectContent>
                        </Select>
                        <Button variant="outline" size="sm" onClick={() => handleExport("csv")} disabled={exporting} data-testid="usage-export-csv">
                            <Download className="mr-1 h-4 w-4" /> CSV
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleExport("xlsx")} disabled={exporting} data-testid="usage-export-xlsx">
                            <FileText className="mr-1 h-4 w-4" /> Excel
                        </Button>
                    </div>
                }
            />

            {loading || !costData ? (
                <div className="grid gap-4 md:grid-cols-3">
                    {[1, 2, 3].map(i => <div key={i} className="h-28 animate-pulse rounded-xl border bg-card" />)}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Stat cards */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <StatCard icon={DollarSign} label="MTD spend" value={`$${costData.mtd_cost_usd.toFixed(4)}`}
                            sub="Month-to-date (UTC)" trend={costData.mtd_trend_pct} testid="usage-stat-mtd" />
                        <StatCard icon={DollarSign} label={`Last ${days} days`} value={`$${costData.total_cost_usd.toFixed(4)}`}
                            sub="Estimated USD" testid="usage-stat-total-cost" />
                        <StatCard icon={Receipt} label="Billable deliveries" value={costData.by_category.reduce((s, c) => s + c.billable_count, 0)}
                            sub="Charged messages" testid="usage-stat-billable" />
                        <StatCard icon={CheckCircle2} label="Free deliveries" value={costData.by_category.reduce((s, c) => s + c.free_count, 0)}
                            sub="In service window" testid="usage-stat-free" />
                    </div>

                    {/* Cost burn chart */}
                    {costSeries.length > 0 && (
                        <div className="rounded-xl border bg-card p-5">
                            <div className="mb-4 flex items-center justify-between">
                                <div>
                                    <div className="text-base font-semibold">Cost burn rate</div>
                                    <div className="text-xs text-muted-foreground">Daily estimated spend (USD)</div>
                                </div>
                                <TrendingUp className="h-4 w-4 text-primary" />
                            </div>
                            <div className="h-56">
                                <ResponsiveContainer>
                                    <LineChart data={costSeries}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                        <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                                        <YAxis tick={{ fontSize: 10 }} />
                                        <Tooltip formatter={v => [`$${v}`, "Cost"]} />
                                        <Line type="monotone" dataKey="cost" stroke="#0d9488" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    <div className="grid gap-4 lg:grid-cols-2">
                        {/* Cost by category */}
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold mb-1">Cost by category</div>
                            <div className="text-xs text-muted-foreground mb-3">Estimated USD</div>
                            {costData.by_category.length === 0 ? (
                                <div className="py-8 text-center text-sm text-muted-foreground">
                                    No cost data yet. Appears when messages are delivered in live mode.
                                </div>
                            ) : (
                                <div className="grid gap-3">
                                    {costData.by_category.map(c => (
                                        <div key={c.category} className="flex items-center justify-between rounded-lg border p-3" data-testid="usage-category-row">
                                            <div className="flex items-center gap-2">
                                                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[c.category] || "#94a3b8" }} />
                                                <span className="text-sm font-medium capitalize">{c.category}</span>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm font-semibold">${c.cost_amount.toFixed(4)}</div>
                                                <div className="text-xs text-muted-foreground">{c.delivered_count} delivered · {c.billable_count} billable · {c.free_count} free</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Cost by country */}
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold mb-1">Cost by country</div>
                            <div className="text-xs text-muted-foreground mb-3">Top recipient countries (based on WA ID prefix)</div>
                            {(costData.by_country || []).length === 0 ? (
                                <div className="py-8 text-center text-sm text-muted-foreground">
                                    No country data yet. Appears after messages are delivered to real contacts.
                                </div>
                            ) : (
                                <div className="h-52">
                                    <ResponsiveContainer>
                                        <BarChart data={costData.by_country} layout="vertical">
                                            <CartesianGrid stroke="#e5e7eb" />
                                            <XAxis type="number" tick={{ fontSize: 10 }} />
                                            <YAxis type="category" dataKey="country_code" width={35} tick={{ fontSize: 10 }} />
                                            <Tooltip formatter={v => [`$${v}`, "Cost"]} />
                                            <Bar dataKey="cost_amount" fill="#0d9488" radius={[0, 4, 4, 0]} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Daily rollup table */}
                    {daily.length > 0 && (
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold mb-3">Daily usage rollup</div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead className="border-b text-xs text-muted-foreground">
                                        <tr>
                                            <th className="py-2 text-left">Date</th>
                                            <th className="text-left">Category</th>
                                            <th className="text-left">Country</th>
                                            <th className="text-right">Delivered</th>
                                            <th className="text-right">Billable</th>
                                            <th className="text-right">Free</th>
                                            <th className="text-right">Cost (USD)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {daily.slice(0, 50).map((row, i) => (
                                            <tr key={i} className="border-t" data-testid="usage-rollup-row">
                                                <td className="py-1.5 font-mono text-xs">{row.day}</td>
                                                <td>
                                                    <span className="inline-flex items-center gap-1 text-xs capitalize">
                                                        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[row.category] || "#94a3b8" }} />
                                                        {row.category}
                                                    </span>
                                                </td>
                                                <td className="text-xs">{row.country_code || "—"}</td>
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
            )}
        </AppShell>
    );
}
