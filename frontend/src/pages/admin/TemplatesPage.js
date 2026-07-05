import { useEffect, useState, useRef } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
    Dialog, DialogContent, DialogDescription, DialogFooter,
    DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
    FileText, RefreshCcw, Plus, Trash2, AlertTriangle, Eye,
    ChevronDown, ChevronUp, Phone, Link as LinkIcon, MessageSquare,
    CheckCircle2, XCircle, Clock, PauseCircle, Ban,
} from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function extractVars(text) {
    if (!text) return [];
    const seen = new Set();
    const vars = [];
    for (const m of [...text.matchAll(/\{\{(\w+)\}\}/g)]) {
        if (!seen.has(m[1])) { seen.add(m[1]); vars.push(m[1]); }
    }
    return vars;
}

function interpolate(text, samples) {
    if (!text) return "";
    return text.replace(/\{\{(\w+)\}\}/g, (_, key) => {
        const idx = /^\d+$/.test(key) ? parseInt(key, 10) - 1 : key;
        return (samples && (samples[idx] || samples[key])) || `{{${key}}}`;
    });
}

const STATUS_CONFIG = {
    APPROVED:  { icon: CheckCircle2, cls: "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]" },
    PENDING:   { icon: Clock,        cls: "bg-[hsl(38_92%_94%)] text-[hsl(38_92%_28%)] border-[hsl(38_92%_84%)]" },
    REJECTED:  { icon: XCircle,      cls: "bg-[hsl(0_90%_96%)] text-[hsl(0_70%_40%)] border-[hsl(0_70%_88%)]" },
    PAUSED:    { icon: PauseCircle,  cls: "bg-[hsl(270_60%_95%)] text-[hsl(270_60%_35%)] border-[hsl(270_40%_85%)]" },
    DISABLED:  { icon: Ban,          cls: "bg-[hsl(215_20%_94%)] text-[hsl(215_25%_35%)] border-[hsl(215_20%_84%)]" },
};

function StatusPill({ status }) {
    const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.PENDING;
    const Icon = cfg.icon;
    return (
        <span className={cn("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium", cfg.cls)}
              data-testid="template-status-pill">
            <Icon className="h-3 w-3" /> {status}
        </span>
    );
}

// ─── WhatsApp preview ─────────────────────────────────────────────────────────

function WhatsAppPreview({ header, body, footer, buttons, samples }) {
    return (
        <div className="rounded-xl border-2 border-[#25d366]/30 bg-[#e5ddd5] p-3">
            <div className="text-[10px] text-center text-[#667781] mb-2">WhatsApp Preview</div>
            <div className="max-w-[260px] mx-auto rounded-lg bg-white p-3 shadow-md text-sm space-y-1.5">
                {header?.enabled && header.text && (
                    <p className="font-semibold text-[#1d1d1d] text-sm">{header.text}</p>
                )}
                {body && (
                    <p className="text-[#303030] whitespace-pre-wrap text-sm leading-relaxed">
                        {interpolate(body, samples)}
                    </p>
                )}
                {footer?.enabled && footer.text && (
                    <p className="text-[10px] text-[#667781]">{footer.text}</p>
                )}
                <div className="text-[10px] text-[#b0b3b5] text-right">12:00</div>
            </div>
            {buttons?.filter(b => b.text).length > 0 && (
                <div className="mt-1 max-w-[260px] mx-auto space-y-1">
                    {buttons.filter(b => b.text).map((b, i) => (
                        <div key={i} className="bg-white rounded-lg text-center text-[#009de2] text-xs py-2 font-medium shadow-sm">
                            {b.type === "PHONE_NUMBER" && <Phone className="inline h-3 w-3 mr-1" />}
                            {b.type === "URL" && <LinkIcon className="inline h-3 w-3 mr-1" />}
                            {b.type === "QUICK_REPLY" && <MessageSquare className="inline h-3 w-3 mr-1" />}
                            {b.text}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

// ─── Create dialog ────────────────────────────────────────────────────────────

const LANGS = [
    { v: "en_US", l: "English (US)" }, { v: "en", l: "English" },
    { v: "es", l: "Spanish" }, { v: "pt_BR", l: "Portuguese (Brazil)" },
    { v: "fr", l: "French" }, { v: "de", l: "German" },
    { v: "ar", l: "Arabic" }, { v: "hi", l: "Hindi" },
    { v: "id", l: "Indonesian" }, { v: "tr", l: "Turkish" },
];

const emptyForm = () => ({
    name: "", language: "en_US", category: "UTILITY",
    header: { enabled: false, text: "" },
    body: "",
    footer: { enabled: false, text: "" },
    buttons: [],
    samples: {},
});

function CreateDialog({ open, onClose, wabas, selectedWaba, onCreated }) {
    const [form, setForm] = useState(emptyForm());
    const [saving, setSaving] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    const bodyVars = extractVars(form.body);

    const setField = (path, val) => {
        setForm(prev => {
            const next = { ...prev };
            if (path === "header.enabled") next.header = { ...next.header, enabled: val };
            else if (path === "header.text") next.header = { ...next.header, text: val };
            else if (path === "footer.enabled") next.footer = { ...next.footer, enabled: val };
            else if (path === "footer.text") next.footer = { ...next.footer, text: val };
            else next[path] = val;
            return next;
        });
    };

    const addButton = () => {
        if (form.buttons.length >= 3) return;
        setForm(prev => ({ ...prev, buttons: [...prev.buttons, { type: "QUICK_REPLY", text: "", url: "", phone_number: "" }] }));
    };
    const removeButton = (i) => setForm(prev => ({ ...prev, buttons: prev.buttons.filter((_, idx) => idx !== i) }));
    const updateButton = (i, key, val) => setForm(prev => {
        const btns = [...prev.buttons];
        btns[i] = { ...btns[i], [key]: val };
        return { ...prev, buttons: btns };
    });

    const buildComponents = () => {
        const comps = [];
        if (form.header.enabled && form.header.text) {
            const hVars = extractVars(form.header.text);
            const ex = hVars.length ? { example_header_text: hVars.map(v => form.samples[v] || `{{${v}}}`) } : {};
            comps.push({ type: "HEADER", format: "TEXT", text: form.header.text, ...ex });
        }
        if (form.body) {
            const bVars = extractVars(form.body);
            const positional = bVars.every(v => /^\d+$/.test(v));
            const exRow = bVars.map(v => form.samples[v] || `{{${v}}}`);
            const ex = bVars.length ? { example_body_text: [exRow] } : {};
            comps.push({ type: "BODY", text: form.body, ...ex });
        }
        if (form.footer.enabled && form.footer.text) {
            comps.push({ type: "FOOTER", text: form.footer.text });
        }
        if (form.buttons.filter(b => b.text).length > 0) {
            comps.push({
                type: "BUTTONS",
                buttons: form.buttons.filter(b => b.text).map(b => ({
                    type: b.type,
                    text: b.text,
                    ...(b.type === "URL" ? { url: b.url, ...(b.url_example ? { url_example: b.url_example } : {}) } : {}),
                    ...(b.type === "PHONE_NUMBER" ? { phone_number: b.phone_number } : {}),
                })),
            });
        }
        return comps;
    };

    const submit = async () => {
        if (!form.name.trim() || !form.body.trim()) { toast.error("Name and body are required"); return; }
        if (!/^[a-z0-9_]+$/.test(form.name)) { toast.error("Name must be lowercase letters, numbers, and underscores only"); return; }
        setSaving(true);
        try {
            await api.post("/templates", {
                waba_id: selectedWaba,
                name: form.name,
                language: form.language,
                category: form.category,
                components: buildComponents(),
            });
            toast.success("Template submitted to Meta (status: PENDING)");
            setForm(emptyForm());
            onClose();
            onCreated();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Create failed");
        } finally {
            setSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={v => { if (!v) { setForm(emptyForm()); onClose(); } }}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create Message Template</DialogTitle>
                    <DialogDescription>
                        Submitted to Meta for approval. Variables use <code>{"{{1}}"}</code> or <code>{"{{name}}"}</code> syntax.
                    </DialogDescription>
                </DialogHeader>

                <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
                    <div className="space-y-4">
                        {/* Basic info */}
                        <div className="grid grid-cols-3 gap-3">
                            <div className="col-span-3 sm:col-span-1">
                                <Label>Template name *</Label>
                                <Input value={form.name} onChange={e => setField("name", e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))}
                                       placeholder="order_shipped" data-testid="template-create-name" />
                                <p className="text-[10px] text-muted-foreground mt-0.5">lowercase, numbers, underscores</p>
                            </div>
                            <div>
                                <Label>Language</Label>
                                <Select value={form.language} onValueChange={v => setField("language", v)}>
                                    <SelectTrigger><SelectValue /></SelectTrigger>
                                    <SelectContent>{LANGS.map(l => <SelectItem key={l.v} value={l.v}>{l.l}</SelectItem>)}</SelectContent>
                                </Select>
                            </div>
                            <div>
                                <Label>Category *</Label>
                                <Select value={form.category} onValueChange={v => setField("category", v)}>
                                    <SelectTrigger data-testid="template-create-category"><SelectValue /></SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="UTILITY">Utility</SelectItem>
                                        <SelectItem value="MARKETING">Marketing</SelectItem>
                                        <SelectItem value="AUTHENTICATION">Authentication</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                        {form.category === "UTILITY" && (
                            <div className="flex items-start gap-2 rounded-lg border bg-[hsl(38_92%_96%)] p-3 text-xs text-[hsl(38_92%_28%)]">
                                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                                <span><strong>Note:</strong> Meta may reclassify utility templates that read as promotional content as Marketing (higher cost + possible utility template suspension).</span>
                            </div>
                        )}

                        {/* Header */}
                        <div className="rounded-lg border p-3">
                            <div className="flex items-center gap-2">
                                <input type="checkbox" id="hdr-en" checked={form.header.enabled} onChange={e => setField("header.enabled", e.target.checked)} className="rounded" />
                                <Label htmlFor="hdr-en" className="cursor-pointer">Header (optional)</Label>
                            </div>
                            {form.header.enabled && (
                                <div className="mt-2">
                                    <Input value={form.header.text} onChange={e => setField("header.text", e.target.value)}
                                           placeholder="Header text (supports {{1}})" data-testid="template-header-text" />
                                </div>
                            )}
                        </div>

                        {/* Body */}
                        <div>
                            <Label>Body *</Label>
                            <Textarea rows={4} value={form.body} onChange={e => setField("body", e.target.value)}
                                      placeholder={"Hi {{1}}, your order #{{2}} has shipped via {{3}}!"} data-testid="template-body-text" />
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                                Use <code>{"{{1}}"}</code>, <code>{"{{2}}"}</code>… or <code>{"{{name}}"}</code> for variables ({bodyVars.length} detected)
                            </p>
                        </div>

                        {/* Sample values */}
                        {bodyVars.length > 0 && (
                            <div className="rounded-lg border p-3 space-y-2">
                                <Label className="text-xs text-muted-foreground">Sample values (required by Meta for variable templates)</Label>
                                {bodyVars.map(v => (
                                    <div key={v} className="flex items-center gap-2">
                                        <span className="text-xs font-mono w-12 shrink-0 text-primary">{`{{${v}}}`}</span>
                                        <Input size="sm" value={form.samples[v] || ""} className="h-7 text-xs"
                                               onChange={e => setForm(prev => ({ ...prev, samples: { ...prev.samples, [v]: e.target.value } }))}
                                               placeholder={`Sample for ${v}`} />
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Footer */}
                        <div className="rounded-lg border p-3">
                            <div className="flex items-center gap-2">
                                <input type="checkbox" id="ftr-en" checked={form.footer.enabled} onChange={e => setField("footer.enabled", e.target.checked)} className="rounded" />
                                <Label htmlFor="ftr-en" className="cursor-pointer">Footer (optional)</Label>
                            </div>
                            {form.footer.enabled && (
                                <Input className="mt-2" value={form.footer.text} onChange={e => setField("footer.text", e.target.value)}
                                       placeholder="e.g. Reply STOP to unsubscribe" data-testid="template-footer-text" />
                            )}
                        </div>

                        {/* Buttons */}
                        <div className="rounded-lg border p-3 space-y-2">
                            <div className="flex items-center justify-between">
                                <Label>Buttons (up to 3)</Label>
                                <Button variant="outline" size="sm" onClick={addButton} disabled={form.buttons.length >= 3} data-testid="template-add-button">
                                    <Plus className="h-3 w-3 mr-1" /> Add
                                </Button>
                            </div>
                            {form.buttons.map((btn, i) => (
                                <div key={i} className="rounded border p-2 space-y-1.5 bg-secondary/20">
                                    <div className="flex items-center gap-2">
                                        <Select value={btn.type} onValueChange={v => updateButton(i, "type", v)}>
                                            <SelectTrigger className="h-7 w-40 text-xs"><SelectValue /></SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="QUICK_REPLY">Quick Reply</SelectItem>
                                                <SelectItem value="URL">URL / Website</SelectItem>
                                                <SelectItem value="PHONE_NUMBER">Phone Number</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Input className="h-7 text-xs flex-1" value={btn.text} onChange={e => updateButton(i, "text", e.target.value)} placeholder="Button text (max 25 chars)" maxLength={25} />
                                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => removeButton(i)}>
                                            <Trash2 className="h-3 w-3 text-destructive" />
                                        </Button>
                                    </div>
                                    {btn.type === "URL" && (
                                        <Input className="h-7 text-xs" value={btn.url} onChange={e => updateButton(i, "url", e.target.value)} placeholder="https://example.com/track/{{1}}" />
                                    )}
                                    {btn.type === "PHONE_NUMBER" && (
                                        <Input className="h-7 text-xs" value={btn.phone_number} onChange={e => updateButton(i, "phone_number", e.target.value)} placeholder="+1234567890" />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Preview */}
                    <div className="hidden lg:block">
                        <Label className="text-xs text-muted-foreground">Live preview</Label>
                        <div className="mt-2">
                            <WhatsAppPreview
                                header={form.header}
                                body={form.body}
                                footer={form.footer}
                                buttons={form.buttons}
                                samples={form.samples}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => { setForm(emptyForm()); onClose(); }}>Cancel</Button>
                    <Button onClick={submit} disabled={saving} data-testid="templates-create-submit">
                        {saving ? "Submitting…" : "Submit to Meta"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

const ALL_STATUSES = ["APPROVED", "PENDING", "REJECTED", "PAUSED", "DISABLED"];

export default function TemplatesPage() {
    const [wabas, setWabas] = useState([]);
    const [selectedWaba, setSelectedWaba] = useState("");
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [createOpen, setCreateOpen] = useState(false);
    const [filterStatus, setFilterStatus] = useState("");
    const [filterCategory, setFilterCategory] = useState("");
    const [search, setSearch] = useState("");
    const [expanded, setExpanded] = useState(null);

    const refresh = async (wabaId, opts = {}) => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (wabaId) params.set("waba_id", wabaId);
            if (opts.status || filterStatus) params.set("status", opts.status ?? filterStatus);
            if (opts.category || filterCategory) params.set("category", opts.category ?? filterCategory);
            if (opts.search ?? search) params.set("search", opts.search ?? search);
            const r = await api.get(`/templates?${params}`);
            setTemplates(r.data);
        } catch { toast.error("Failed to load templates"); }
        finally { setLoading(false); }
    };

    useEffect(() => {
        (async () => {
            try {
                const r = await api.get("/wabas");
                setWabas(r.data);
                if (r.data.length) {
                    setSelectedWaba(r.data[0].waba_id);
                    await refresh(r.data[0].waba_id);
                } else { setLoading(false); }
            } catch { setLoading(false); }
        })();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const sync = async () => {
        if (!selectedWaba) return;
        setSyncing(true);
        try {
            const r = await api.post("/templates/sync", { waba_id: selectedWaba });
            toast.success(`Synced ${r.data.synced} templates from Meta`);
            await refresh(selectedWaba);
        } catch (err) { toast.error(err?.response?.data?.detail || "Sync failed"); }
        finally { setSyncing(false); }
    };

    const remove = async (id) => {
        if (!window.confirm("Delete this template? This will also remove it from Meta.")) return;
        try {
            await api.delete(`/templates/${id}`);
            toast.success("Template deleted");
            await refresh(selectedWaba);
        } catch (err) { toast.error(err?.response?.data?.detail || "Delete failed"); }
    };

    const applyFilter = (key, val) => {
        const opts = { status: filterStatus, category: filterCategory, search };
        opts[key] = val;
        if (key === "status") setFilterStatus(val);
        if (key === "category") setFilterCategory(val);
        if (key === "search") setSearch(val);
        refresh(selectedWaba, opts);
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Templates</span>}
                title="Message Templates"
                description="Create and manage WhatsApp message templates. Approved templates appear here after Meta review."
                actions={
                    <div className="flex flex-wrap gap-2">
                        <Button variant="outline" onClick={sync} disabled={syncing || !selectedWaba} data-testid="templates-sync-button">
                            <RefreshCcw className={cn("mr-2 h-4 w-4", syncing && "animate-spin")} />
                            Sync from Meta
                        </Button>
                        <Button onClick={() => setCreateOpen(true)} disabled={!selectedWaba} data-testid="templates-create-trigger">
                            <Plus className="mr-2 h-4 w-4" /> New Template
                        </Button>
                    </div>
                }
            />

            {wabas.length === 0 ? (
                <EmptyState icon={FileText} title="Connect a WABA first"
                    description="Templates are scoped to a WhatsApp Business Account."
                    action={<Button asChild><Link to="/app/connect">Connect WhatsApp</Link></Button>}
                />
            ) : (
                <div className="space-y-4">
                    {/* Toolbar */}
                    <div className="flex flex-wrap items-end gap-3">
                        <div>
                            <Label className="text-xs">WABA</Label>
                            <Select value={selectedWaba} onValueChange={v => { setSelectedWaba(v); refresh(v); }}>
                                <SelectTrigger className="w-64" data-testid="templates-waba-select"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    {wabas.map(w => <SelectItem key={w.waba_id} value={w.waba_id}>{w.name} · {w.waba_id}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Status</Label>
                            <Select value={filterStatus || "all"} onValueChange={v => applyFilter("status", v === "all" ? "" : v)}>
                                <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All statuses</SelectItem>
                                    {ALL_STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div>
                            <Label className="text-xs">Category</Label>
                            <Select value={filterCategory || "all"} onValueChange={v => applyFilter("category", v === "all" ? "" : v)}>
                                <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All categories</SelectItem>
                                    <SelectItem value="UTILITY">Utility</SelectItem>
                                    <SelectItem value="MARKETING">Marketing</SelectItem>
                                    <SelectItem value="AUTHENTICATION">Authentication</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex-1 min-w-[160px]">
                            <Label className="text-xs">Search</Label>
                            <Input value={search} onChange={e => applyFilter("search", e.target.value)} placeholder="Search by name…" data-testid="templates-search" />
                        </div>
                    </div>

                    {loading ? (
                        <div className="h-40 animate-pulse rounded-xl border bg-card" />
                    ) : templates.length === 0 ? (
                        <EmptyState icon={FileText} title="No templates"
                            description="Sync from Meta to import approved templates, or create a new one."
                            action={<Button onClick={sync} data-testid="empty-state-primary-action">Sync from Meta</Button>}
                        />
                    ) : (
                        <div className="overflow-hidden rounded-xl border bg-card">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead>Name</TableHead>
                                        <TableHead>Language</TableHead>
                                        <TableHead>Category</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead>Body preview</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {templates.map(t => (
                                        <>
                                            <TableRow key={t.id} data-testid="template-row" className="cursor-pointer" onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
                                                <TableCell className="font-medium">{t.name}</TableCell>
                                                <TableCell className="text-xs">{t.language}</TableCell>
                                                <TableCell><span className="text-xs uppercase">{t.category || "—"}</span></TableCell>
                                                <TableCell>
                                                    <div>
                                                        <StatusPill status={t.status} />
                                                        {t.rejection_reason && (
                                                            <div className="mt-0.5 text-[10px] text-destructive">{t.rejection_reason}</div>
                                                        )}
                                                    </div>
                                                </TableCell>
                                                <TableCell className="max-w-xs truncate text-xs text-muted-foreground">{t.body || "—"}</TableCell>
                                                <TableCell className="text-right">
                                                    <div className="flex items-center justify-end gap-1">
                                                        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); setExpanded(expanded === t.id ? null : t.id); }}>
                                                            {expanded === t.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                                                        </Button>
                                                        <Button size="sm" variant="ghost" onClick={e => { e.stopPropagation(); remove(t.id); }} data-testid="template-delete-button">
                                                            <Trash2 className="h-4 w-4 text-destructive" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                            {expanded === t.id && (
                                                <TableRow key={`${t.id}-detail`}>
                                                    <TableCell colSpan={6} className="bg-secondary/20 p-4">
                                                        <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
                                                            <div>
                                                                <div className="text-xs font-medium text-muted-foreground mb-2">Components</div>
                                                                {(t.components || []).map((c, i) => (
                                                                    <div key={i} className="mb-2 rounded border bg-background p-2 text-xs">
                                                                        <span className="font-mono font-bold text-primary">{c.type}</span>
                                                                        {c.format && <span className="ml-2 text-muted-foreground">({c.format})</span>}
                                                                        {c.text && <p className="mt-1 whitespace-pre-wrap">{c.text}</p>}
                                                                        {c.buttons && c.buttons.map((b, j) => (
                                                                            <div key={j} className="mt-1 flex items-center gap-2 text-[10px]">
                                                                                <Badge variant="outline" className="text-[10px]">{b.type}</Badge>
                                                                                <span>{b.text}</span>
                                                                                {b.url && <span className="text-muted-foreground">{b.url}</span>}
                                                                            </div>
                                                                        ))}
                                                                    </div>
                                                                ))}
                                                                {t.meta_template_id && (
                                                                    <div className="text-[10px] text-muted-foreground mt-1">Meta ID: {t.meta_template_id}</div>
                                                                )}
                                                            </div>
                                                            <WhatsAppPreview
                                                                header={t.components?.find(c => c.type === "HEADER")
                                                                    ? { enabled: true, text: t.components.find(c => c.type === "HEADER")?.text } : { enabled: false }}
                                                                body={t.body}
                                                                footer={t.components?.find(c => c.type === "FOOTER")
                                                                    ? { enabled: true, text: t.components.find(c => c.type === "FOOTER")?.text } : { enabled: false }}
                                                                buttons={t.components?.find(c => c.type === "BUTTONS")?.buttons || []}
                                                                samples={{}}
                                                            />
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            )}
                                        </>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    )}
                </div>
            )}

            <CreateDialog
                open={createOpen}
                onClose={() => setCreateOpen(false)}
                wabas={wabas}
                selectedWaba={selectedWaba}
                onCreated={() => refresh(selectedWaba)}
            />
        </AppShell>
    );
}
