import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Send, Loader2, FileText } from "lucide-react";
import { useNavigate, Link } from "react-router-dom";

function randomKey() {
    return `key-${Math.random().toString(36).slice(2, 10)}-${Date.now()}`;
}

export default function SendPage() {
    const navigate = useNavigate();
    const [phones, setPhones] = useState([]);
    const [templates, setTemplates] = useState([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState("");
    const [form, setForm] = useState({
        phone_number_id: "",
        to_wa_id: "",
        template_name: "hello_world",
        language_code: "en_US",
        idempotency_key: randomKey(),
    });
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        (async () => {
            try {
                const [pr, tr] = await Promise.all([
                    api.get("/phone-numbers"),
                    api.get("/templates"),
                ]);
                setPhones(pr.data);
                setTemplates(tr.data);
                setForm((f) => {
                    const next = { ...f };
                    if (pr.data.length && !f.phone_number_id) {
                        next.phone_number_id = pr.data[0].phone_number_id;
                    }
                    if (tr.data.length) {
                        next.template_name = tr.data[0].name;
                        next.language_code = tr.data[0].language;
                        setSelectedTemplateId(tr.data[0].id);
                    }
                    return next;
                });
            } catch {}
        })();
    }, []);

    const onTemplateChange = (templateId) => {
        const t = templates.find((x) => x.id === templateId);
        if (t) {
            setSelectedTemplateId(templateId);
            setForm((f) => ({
                ...f,
                template_name: t.name,
                language_code: t.language,
            }));
        }
    };

    const submit = async (e) => {
        e.preventDefault();
        if (!form.phone_number_id) {
            toast.error("Connect a WhatsApp number first.");
            return;
        }
        if (!/^\d{5,15}$/.test(form.to_wa_id)) {
            toast.error("Recipient WhatsApp ID must be 5–15 digits (no spaces or +).");
            return;
        }
        setSubmitting(true);
        try {
            const r = await api.post("/messages/send", form);
            if (r.data.status === "failed") {
                toast.error(`Send failed: ${r.data.error || "unknown error"}`);
            } else {
                toast.success(`Message ${r.data.status} — view in Message Log.`);
                navigate("/app/messages");
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Send failed");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Send Template</span>}
                title="Send Template Message"
                description="In mock mode, the platform returns a synthetic wamid and you can simulate the webhook to advance the status."
                actions={
                    <Button asChild variant="outline" data-testid="send-manage-templates">
                        <Link to="/app/templates"><FileText className="mr-2 h-4 w-4" /> Manage templates</Link>
                    </Button>
                }
            />
            <form
                onSubmit={submit}
                className="max-w-2xl rounded-xl border bg-card p-6 shadow-[0_1px_0_hsl(214_20%_90%)_inset]"
                data-testid="send-template-form"
            >
                <div className="grid gap-5 sm:grid-cols-2">
                    <div className="sm:col-span-2">
                        <Label>From phone number</Label>
                        <Select
                            value={form.phone_number_id}
                            onValueChange={(v) => setForm({ ...form, phone_number_id: v })}
                        >
                            <SelectTrigger data-testid="send-phone-select">
                                <SelectValue placeholder="Select a connected phone number" />
                            </SelectTrigger>
                            <SelectContent>
                                {phones.length === 0 && (
                                    <SelectItem value="none" disabled>
                                        No phone numbers connected
                                    </SelectItem>
                                )}
                                {phones.map((p) => (
                                    <SelectItem key={p.phone_number_id} value={p.phone_number_id}>
                                        {p.display_phone_number} · {p.verified_name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="sm:col-span-2">
                        <Label htmlFor="to_wa_id">Recipient WhatsApp ID</Label>
                        <Input
                            id="to_wa_id"
                            value={form.to_wa_id}
                            onChange={(e) => setForm({ ...form, to_wa_id: e.target.value })}
                            placeholder="15551234567"
                            data-testid="send-to-wa-input"
                        />
                        <p className="mt-1 text-xs text-muted-foreground">
                            Digits only, no spaces or +. Example: 15551234567.
                        </p>
                    </div>
                    <div>
                        <Label>Template</Label>
                        {templates.length > 0 ? (
                            <Select value={selectedTemplateId} onValueChange={onTemplateChange}>
                                <SelectTrigger data-testid="send-template-select">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {templates.map((t) => (
                                        <SelectItem key={t.id} value={t.id}>
                                            {t.name} <span className="text-xs text-muted-foreground">· {t.language}</span>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        ) : (
                            <Input
                                value={form.template_name}
                                onChange={(e) => setForm({ ...form, template_name: e.target.value })}
                                data-testid="send-template-name-input"
                            />
                        )}
                        <p className="mt-1 text-xs text-muted-foreground">
                            Sync templates from <Link to="/app/templates" className="text-primary">Templates</Link>.
                        </p>
                    </div>
                    <div>
                        <Label htmlFor="language_code">Language code</Label>
                        <Input
                            id="language_code"
                            value={form.language_code}
                            onChange={(e) => setForm({ ...form, language_code: e.target.value })}
                            data-testid="send-language-input"
                        />
                    </div>
                    <div className="sm:col-span-2">
                        <Label htmlFor="idempotency_key">Idempotency key</Label>
                        <div className="flex gap-2">
                            <Input
                                id="idempotency_key"
                                value={form.idempotency_key}
                                onChange={(e) => setForm({ ...form, idempotency_key: e.target.value })}
                                data-testid="send-idempotency-input"
                            />
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setForm({ ...form, idempotency_key: randomKey() })}
                                data-testid="send-idempotency-regen"
                            >
                                New key
                            </Button>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Repeat sends with the same key return the original message.
                        </p>
                    </div>
                </div>
                <div className="mt-6">
                    <Button type="submit" disabled={submitting} data-testid="send-submit-button">
                        {submitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...
                            </>
                        ) : (
                            <>
                                <Send className="mr-2 h-4 w-4" /> Send template
                            </>
                        )}
                    </Button>
                </div>
            </form>
        </AppShell>
    );
}
