import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { FileText, RefreshCcw, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";

function StatusPill({ status }) {
    const map = {
        APPROVED: "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]",
        PENDING: "bg-[hsl(38_92%_94%)] text-[hsl(38_92%_28%)] border-[hsl(38_92%_84%)]",
        REJECTED: "bg-[hsl(0_90%_96%)] text-[hsl(0_70%_40%)] border-[hsl(0_70%_88%)]",
    };
    return (
        <span
            className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${map[status] || map.APPROVED}`}
            data-testid="template-status-pill"
        >
            {status}
        </span>
    );
}

export default function TemplatesPage() {
    const [wabas, setWabas] = useState([]);
    const [selectedWaba, setSelectedWaba] = useState("");
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [creating, setCreating] = useState(false);
    const [createForm, setCreateForm] = useState({
        name: "",
        language: "en_US",
        category: "UTILITY",
        body: "",
    });
    const [createOpen, setCreateOpen] = useState(false);

    const refresh = async (wabaId) => {
        try {
            const params = wabaId ? `?waba_id=${wabaId}` : "";
            const r = await api.get(`/templates${params}`);
            setTemplates(r.data);
        } catch (err) {
            toast.error("Failed to load templates");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        (async () => {
            try {
                const r = await api.get("/wabas");
                setWabas(r.data);
                if (r.data.length) {
                    setSelectedWaba(r.data[0].waba_id);
                    await refresh(r.data[0].waba_id);
                } else {
                    setLoading(false);
                }
            } catch {
                setLoading(false);
            }
        })();
    }, []);

    const sync = async () => {
        if (!selectedWaba) return;
        setSyncing(true);
        try {
            const r = await api.post("/templates/sync", { waba_id: selectedWaba });
            toast.success(`Synced ${r.data.synced} templates from Meta (mock)`);
            await refresh(selectedWaba);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Sync failed");
        } finally {
            setSyncing(false);
        }
    };

    const create = async () => {
        if (!selectedWaba) {
            toast.error("Select a WABA first");
            return;
        }
        if (!createForm.name || !createForm.body) {
            toast.error("Name and body are required");
            return;
        }
        setCreating(true);
        try {
            await api.post("/templates", { waba_id: selectedWaba, ...createForm });
            toast.success("Template created");
            setCreateOpen(false);
            setCreateForm({ name: "", language: "en_US", category: "UTILITY", body: "" });
            await refresh(selectedWaba);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Create failed");
        } finally {
            setCreating(false);
        }
    };

    const remove = async (id) => {
        if (!confirm("Delete this template?")) return;
        try {
            await api.delete(`/templates/${id}`);
            toast.success("Template deleted");
            await refresh(selectedWaba);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Delete failed");
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Templates</span>}
                title="Message Templates"
                description="Sync templates from Meta or create local ones. Mock mode auto-approves all templates."
                actions={
                    <div className="flex flex-wrap gap-2">
                        <Button variant="outline" onClick={sync} disabled={syncing || !selectedWaba} data-testid="templates-sync-button">
                            <RefreshCcw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                            Sync from Meta
                        </Button>
                        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                            <DialogTrigger asChild>
                                <Button data-testid="templates-create-trigger">
                                    <Plus className="mr-2 h-4 w-4" /> New template
                                </Button>
                            </DialogTrigger>
                            <DialogContent>
                                <DialogHeader>
                                    <DialogTitle>Create a template</DialogTitle>
                                    <DialogDescription>
                                        Local templates are auto-approved in mock mode. Use
                                        {" "}<code>{`{{1}}`}</code>, <code>{`{{2}}`}</code>... as placeholders.
                                    </DialogDescription>
                                </DialogHeader>
                                <div className="space-y-4">
                                    <div>
                                        <Label>Name</Label>
                                        <Input
                                            value={createForm.name}
                                            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                                            placeholder="order_confirmation"
                                            data-testid="templates-create-name"
                                        />
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <Label>Language</Label>
                                            <Input
                                                value={createForm.language}
                                                onChange={(e) => setCreateForm({ ...createForm, language: e.target.value })}
                                                data-testid="templates-create-language"
                                            />
                                        </div>
                                        <div>
                                            <Label>Category</Label>
                                            <Select
                                                value={createForm.category}
                                                onValueChange={(v) => setCreateForm({ ...createForm, category: v })}
                                            >
                                                <SelectTrigger data-testid="templates-create-category">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="UTILITY">Utility</SelectItem>
                                                    <SelectItem value="MARKETING">Marketing</SelectItem>
                                                    <SelectItem value="AUTHENTICATION">Authentication</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>
                                    </div>
                                    <div>
                                        <Label>Body</Label>
                                        <Textarea
                                            rows={4}
                                            value={createForm.body}
                                            onChange={(e) => setCreateForm({ ...createForm, body: e.target.value })}
                                            placeholder="Hi {{1}}, your order #{{2}} has shipped!"
                                            data-testid="templates-create-body"
                                        />
                                    </div>
                                </div>
                                <DialogFooter>
                                    <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
                                    <Button onClick={create} disabled={creating} data-testid="templates-create-submit">
                                        {creating ? "Creating..." : "Create"}
                                    </Button>
                                </DialogFooter>
                            </DialogContent>
                        </Dialog>
                    </div>
                }
            />
            {wabas.length === 0 ? (
                <EmptyState
                    icon={FileText}
                    title="Connect a WABA first"
                    description="Templates are scoped to a WhatsApp Business Account. Connect one to get started."
                    action={
                        <Button asChild data-testid="empty-state-primary-action">
                            <Link to="/app/connect">Connect WhatsApp</Link>
                        </Button>
                    }
                />
            ) : (
                <div className="space-y-4">
                    <div className="flex items-end gap-3">
                        <div className="w-72">
                            <Label>WABA</Label>
                            <Select
                                value={selectedWaba}
                                onValueChange={(v) => {
                                    setSelectedWaba(v);
                                    refresh(v);
                                }}
                            >
                                <SelectTrigger data-testid="templates-waba-select">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {wabas.map((w) => (
                                        <SelectItem key={w.waba_id} value={w.waba_id}>
                                            {w.name} · {w.waba_id}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    {loading ? (
                        <div className="h-40 animate-pulse rounded-xl border bg-card" />
                    ) : templates.length === 0 ? (
                        <EmptyState
                            icon={FileText}
                            title="No templates yet"
                            description="Sync from Meta to import your approved templates, or create a local one."
                            action={
                                <Button onClick={sync} data-testid="empty-state-primary-action">
                                    Sync from Meta
                                </Button>
                            }
                        />
                    ) : (
                        <div className="overflow-hidden rounded-xl border bg-card">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Name</TableHead>
                                        <TableHead>Language</TableHead>
                                        <TableHead>Category</TableHead>
                                        <TableHead>Body preview</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Source</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {templates.map((t) => (
                                        <TableRow key={t.id} data-testid="template-row">
                                            <TableCell className="font-medium">{t.name}</TableCell>
                                            <TableCell className="text-xs">{t.language}</TableCell>
                                            <TableCell className="text-xs uppercase">{t.category || "—"}</TableCell>
                                            <TableCell className="max-w-md truncate text-xs text-muted-foreground">{t.body || "—"}</TableCell>
                                            <TableCell><StatusPill status={t.status} /></TableCell>
                                            <TableCell className="text-xs text-muted-foreground">{t.source || "—"}</TableCell>
                                            <TableCell className="text-right">
                                                <Button
                                                    size="sm"
                                                    variant="ghost"
                                                    onClick={() => remove(t.id)}
                                                    data-testid="template-delete-button"
                                                >
                                                    <Trash2 className="h-4 w-4 text-destructive" />
                                                </Button>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </div>
            )}
        </AppShell>
    );
}
