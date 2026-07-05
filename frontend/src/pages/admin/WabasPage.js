import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { api } from "@/lib/api";
import { Smartphone, Plug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

export default function WabasPage() {
    const [wabas, setWabas] = useState([]);
    const [phones, setPhones] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        (async () => {
            try {
                const [w, p] = await Promise.all([api.get("/wabas"), api.get("/phone-numbers")]);
                setWabas(w.data);
                setPhones(p.data);
            } finally {
                setLoading(false);
            }
        })();
    }, []);

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / WABAs & Numbers</span>}
                title="WABAs & Phone Numbers"
                description="All connected WhatsApp Business Accounts and their phone numbers."
                actions={
                    <Button asChild data-testid="wabas-connect-cta">
                        <Link to="/app/connect">
                            <Plug className="mr-2 h-4 w-4" /> Connect another
                        </Link>
                    </Button>
                }
            />
            {loading ? (
                <div className="h-32 animate-pulse rounded-xl border bg-card" />
            ) : wabas.length === 0 ? (
                <EmptyState
                    icon={Smartphone}
                    title="No WABAs connected yet"
                    description="Run the mock Embedded Signup to create your first WhatsApp Business Account."
                    action={
                        <Button asChild data-testid="empty-state-primary-action">
                            <Link to="/app/connect">Connect WhatsApp</Link>
                        </Button>
                    }
                />
            ) : (
                <div className="space-y-6">
                    <div className="rounded-xl border bg-card">
                        <div className="border-b p-4">
                            <div className="text-sm font-semibold">WhatsApp Business Accounts</div>
                        </div>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead>WABA ID</TableHead>
                                    <TableHead>Business ID</TableHead>
                                    <TableHead>Created</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {wabas.map((w) => (
                                    <TableRow key={w.waba_id} data-testid="waba-row">
                                        <TableCell className="font-medium">{w.name}</TableCell>
                                        <TableCell className="font-mono text-xs">{w.waba_id}</TableCell>
                                        <TableCell className="font-mono text-xs">{w.business_id || "—"}</TableCell>
                                        <TableCell className="text-sm text-muted-foreground">
                                            {new Date(w.created_at).toLocaleString()}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                    <div className="rounded-xl border bg-card">
                        <div className="border-b p-4">
                            <div className="text-sm font-semibold">Phone Numbers</div>
                        </div>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Phone</TableHead>
                                    <TableHead>Verified Name</TableHead>
                                    <TableHead>Quality</TableHead>
                                    <TableHead>Phone Number ID</TableHead>
                                    <TableHead>WABA</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {phones.map((p) => (
                                    <TableRow key={p.phone_number_id} data-testid="phone-row">
                                        <TableCell className="font-medium">{p.display_phone_number}</TableCell>
                                        <TableCell>{p.verified_name || "—"}</TableCell>
                                        <TableCell>
                                            <span className="inline-flex items-center rounded-full border bg-[hsl(152_55%_93%)] px-2 py-0.5 text-xs text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]">
                                                {p.quality_rating || "GREEN"}
                                            </span>
                                        </TableCell>
                                        <TableCell className="font-mono text-xs">{p.phone_number_id}</TableCell>
                                        <TableCell className="font-mono text-xs">{p.waba_id}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>
            )}
        </AppShell>
    );
}
