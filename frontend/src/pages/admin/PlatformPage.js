import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Users, MessageSquareText, DollarSign, Shield, ChevronRight, X, Download, FileText } from "lucide-react";
import { toast } from "sonner";

function StatCard({ icon: Icon, label, value, sub, testid }) {
    return (
        <div className="rounded-xl border bg-card p-5" data-testid={testid}>
            <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-muted-foreground">{label}</span>
                <Icon className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-semibold tracking-tight">{value}</div>
            {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
        </div>
    );
}

export default function PlatformPage() {
    const [days, setDays] = useState("30");
    const [overview, setOverview] = useState(null);
    const [tenants, setTenants] = useState([]);
    const [drilldown, setDrilldown] = useState(null);
    const [drilldownData, setDrilldownData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(null);

    const load = async (d = days) => {
        setLoading(true);
        try {
            const [ov, tl] = await Promise.all([
                api.get(`/platform/overview?days=${d}`),
                api.get(`/platform/tenants?days=${d}`),
            ]);
            setOverview(ov.data);
            setTenants(tl.data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(days); }, [days]); // eslint-disable-line

    const openDrilldown = async (tenant) => {
        setDrilldown(tenant);
        try {
            const r = await api.get(`/platform/tenants/${tenant.tenant_id}/usage?days=${days}`);
            setDrilldownData(r.data);
        } catch (e) {
            toast.error("Failed to load tenant details");
        }
    };

    const handleExport = async (tenantId, format) => {
        setExporting(tenantId + format);
        try {
            const resp = await api.get(`/platform/tenants/${tenantId}/export?format=${format}`, {
                responseType: "blob",
            });
            const url = URL.createObjectURL(resp.data);
            const a = document.createElement("a");
            a.href = url;
            a.download = `tenant_${tenantId.slice(0, 8)}_usage.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            toast.error("Export failed");
        } finally {
            setExporting(null);
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Platform Admin</span>}
                title="Platform Overview"
                description="Cross-tenant usage and cost. All reads here are audited in the audit log."
                actions={
                    <Select value={days} onValueChange={setDays}>
                        <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                        <SelectContent>
                            <SelectItem value="7">Last 7 days</SelectItem>
                            <SelectItem value="30">Last 30 days</SelectItem>
                            <SelectItem value="90">Last 90 days</SelectItem>
                        </SelectContent>
                    </Select>
                }
            />

            {loading || !overview ? (
                <div className="grid gap-4 md:grid-cols-4">
                    {[1,2,3,4].map(i => <div key={i} className="h-28 animate-pulse rounded-xl border bg-card" />)}
                </div>
            ) : (
                <div className="space-y-6">
                    {/* Platform stats */}
                    <div className="grid gap-4 md:grid-cols-4">
                        <StatCard icon={Users} label="Total tenants" value={overview.total_tenants} testid="platform-stat-tenants" />
                        <StatCard icon={MessageSquareText} label="Total messages" value={overview.total_messages} sub={`Last ${days} days`} testid="platform-stat-messages" />
                        <StatCard icon={DollarSign} label="Platform cost" value={`$${overview.total_cost_usd.toFixed(4)}`} sub="Estimated USD" testid="platform-stat-cost" />
                        <StatCard icon={Shield} label="Total delivered" value={overview.total_delivered} sub={`${overview.total_billable} billable`} testid="platform-stat-delivered" />
                    </div>

                    {/* Top tenants chart */}
                    {overview.top_tenants_by_volume?.length > 0 && (
                        <div className="rounded-xl border bg-card p-5">
                            <div className="text-base font-semibold mb-1">Top tenants by volume</div>
                            <div className="text-xs text-muted-foreground mb-3">Message count in selected window</div>
                            <div className="h-52">
                                <ResponsiveContainer>
                                    <BarChart data={overview.top_tenants_by_volume} layout="vertical">
                                        <CartesianGrid stroke="#e5e7eb" />
                                        <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                                        <YAxis type="category" dataKey="tenant_name" width={100} tick={{ fontSize: 10 }} />
                                        <Tooltip />
                                        <Bar dataKey="message_count" fill="#0d9488" radius={[0, 4, 4, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    {/* Tenants table */}
                    <div className="rounded-xl border bg-card p-5">
                        <div className="text-base font-semibold mb-3">All tenants</div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="border-b text-xs text-muted-foreground">
                                    <tr>
                                        <th className="py-2 text-left">Tenant</th>
                                        <th className="text-right">Messages</th>
                                        <th className="text-right">Delivered</th>
                                        <th className="text-right">Billable</th>
                                        <th className="text-right">Cost (USD)</th>
                                        <th className="text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tenants.map(t => (
                                        <tr key={t.tenant_id} className="border-t hover:bg-secondary/20 cursor-pointer" data-testid="platform-tenant-row" onClick={() => openDrilldown(t)}>
                                            <td className="py-2">
                                                <div className="font-medium">{t.tenant_name}</div>
                                                <div className="text-xs text-muted-foreground font-mono">{t.tenant_id.slice(0, 8)}</div>
                                            </td>
                                            <td className="text-right text-xs">{t.messages}</td>
                                            <td className="text-right text-xs">{t.delivered}</td>
                                            <td className="text-right text-xs">{t.billable}</td>
                                            <td className="text-right font-mono text-xs">${t.cost_usd.toFixed(4)}</td>
                                            <td className="text-right">
                                                <Button variant="ghost" size="sm" className="h-7 text-xs">
                                                    <ChevronRight className="h-4 w-4" />
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* Tenant drill-down panel */}
            {drilldown && (
                <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-background border-l shadow-2xl overflow-y-auto" data-testid="platform-drilldown-panel">
                    <div className="sticky top-0 bg-background border-b px-5 py-4 flex items-center justify-between">
                        <div>
                            <div className="font-semibold">{drilldown.tenant_name}</div>
                            <div className="text-xs text-muted-foreground">{drilldown.tenant_id}</div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Button variant="outline" size="sm" onClick={() => handleExport(drilldown.tenant_id, "csv")} disabled={!!exporting} className="h-7 text-xs">
                                <Download className="h-3 w-3 mr-1" /> CSV
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => handleExport(drilldown.tenant_id, "xlsx")} disabled={!!exporting} className="h-7 text-xs">
                                <FileText className="h-3 w-3 mr-1" /> Excel
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => { setDrilldown(null); setDrilldownData(null); }} className="h-7 w-7 p-0">
                                <X className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                    <div className="p-5 space-y-4">
                        {!drilldownData ? (
                            <div className="h-40 animate-pulse rounded-xl border bg-card" />
                        ) : (
                            <>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="rounded-lg border p-3">
                                        <div className="text-xs text-muted-foreground">Total messages</div>
                                        <div className="text-lg font-semibold">{drilldownData.total_messages}</div>
                                    </div>
                                    <div className="rounded-lg border p-3">
                                        <div className="text-xs text-muted-foreground">Estimated cost</div>
                                        <div className="text-lg font-semibold">${drilldownData.total_cost_usd.toFixed(4)}</div>
                                    </div>
                                    <div className="rounded-lg border p-3">
                                        <div className="text-xs text-muted-foreground">Outbound</div>
                                        <div className="text-lg font-semibold">{drilldownData.outbound}</div>
                                    </div>
                                    <div className="rounded-lg border p-3">
                                        <div className="text-xs text-muted-foreground">Inbound</div>
                                        <div className="text-lg font-semibold">{drilldownData.inbound}</div>
                                    </div>
                                </div>
                                <div>
                                    <div className="text-sm font-medium mb-2">Status breakdown</div>
                                    {Object.entries(drilldownData.status_breakdown || {}).map(([k, v]) => (
                                        <div key={k} className="flex justify-between text-xs border-b py-1">
                                            <span className="capitalize">{k}</span><span>{v}</span>
                                        </div>
                                    ))}
                                </div>
                                <div>
                                    <div className="text-sm font-medium mb-2">Daily rollup ({drilldownData.daily_rollup?.length} rows)</div>
                                    <div className="max-h-64 overflow-y-auto">
                                        <table className="w-full text-xs">
                                            <thead className="text-muted-foreground border-b">
                                                <tr>
                                                    <th className="text-left py-1">Date</th>
                                                    <th className="text-left">Category</th>
                                                    <th className="text-right">Delivered</th>
                                                    <th className="text-right">Cost</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(drilldownData.daily_rollup || []).map((r, i) => (
                                                    <tr key={i} className="border-t">
                                                        <td className="py-0.5 font-mono">{r.day}</td>
                                                        <td className="capitalize">{r.category}</td>
                                                        <td className="text-right">{r.delivered_count}</td>
                                                        <td className="text-right font-mono">${r.cost_amount.toFixed(4)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </AppShell>
    );
}
