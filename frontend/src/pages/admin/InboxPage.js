import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Inbox as InboxIcon, Send, Sparkles, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNowStrict } from "date-fns";

function WindowBadge({ open, expiresAt }) {
    if (!expiresAt) {
        return (
            <span className="inline-flex items-center gap-1 rounded-full border bg-[hsl(215_20%_94%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(215_25%_25%)]">
                <Clock className="h-3 w-3" /> No inbound yet
            </span>
        );
    }
    if (open) {
        const rel = formatDistanceToNowStrict(new Date(expiresAt));
        return (
            <span
                className="inline-flex items-center gap-1 rounded-full border bg-[hsl(152_55%_93%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(152_55%_26%)]"
                data-testid="window-badge-open"
            >
                <Clock className="h-3 w-3" /> Window open · {rel} left
            </span>
        );
    }
    return (
        <span
            className="inline-flex items-center gap-1 rounded-full border bg-[hsl(0_90%_96%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(0_70%_40%)]"
            data-testid="window-badge-closed"
        >
            <Clock className="h-3 w-3" /> Window closed
        </span>
    );
}

export default function InboxPage() {
    const [conversations, setConversations] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [thread, setThread] = useState(null);
    const [reply, setReply] = useState("");
    const [sending, setSending] = useState(false);
    const [simulating, setSimulating] = useState(false);
    const [loading, setLoading] = useState(true);
    const [simNewContact, setSimNewContact] = useState("15559998888");
    const [simBody, setSimBody] = useState("Hi! I have a question about my order.");

    const loadConversations = async () => {
        try {
            const r = await api.get("/inbox/conversations");
            setConversations(r.data);
            if (r.data.length && !selectedId) {
                setSelectedId(r.data[0].id);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const loadThread = async (id) => {
        if (!id) return;
        try {
            const r = await api.get(`/inbox/conversations/${id}/messages`);
            setThread(r.data);
        } catch {
            setThread(null);
        }
    };

    useEffect(() => {
        loadConversations();
        const id = setInterval(loadConversations, 5000);
        return () => clearInterval(id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (selectedId) loadThread(selectedId);
    }, [selectedId]);

    const sendReply = async () => {
        if (!reply.trim()) return;
        if (!selectedId) return;
        setSending(true);
        try {
            await api.post(`/inbox/conversations/${selectedId}/reply`, { body: reply });
            toast.success("Reply sent");
            setReply("");
            await loadThread(selectedId);
            await loadConversations();
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Reply failed");
        } finally {
            setSending(false);
        }
    };

    const simulateInbound = async () => {
        setSimulating(true);
        try {
            if (selectedId) {
                await api.post(`/inbox/conversations/${selectedId}/simulate-inbound`, {
                    body: simBody,
                });
                toast.success("Simulated inbound message added to this conversation");
                await loadThread(selectedId);
            } else {
                const r = await api.post(`/inbox/simulate-inbound`, {
                    contact_wa_id: simNewContact,
                    body: simBody,
                });
                toast.success("New conversation created");
                await loadConversations();
                setSelectedId(r.data.conversation_id);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Simulate failed");
        } finally {
            setSimulating(false);
        }
    };

    const simulateNew = async () => {
        setSimulating(true);
        try {
            const r = await api.post(`/inbox/simulate-inbound`, {
                contact_wa_id: simNewContact,
                body: simBody,
            });
            toast.success("New conversation created");
            await loadConversations();
            setSelectedId(r.data.conversation_id);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Simulate failed");
        } finally {
            setSimulating(false);
        }
    };

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Inbox</span>}
                title="Inbox"
                description="Conversations with your WhatsApp contacts. Session messages require an open 24-hour service window."
                actions={
                    <Button onClick={simulateNew} variant="outline" disabled={simulating} data-testid="inbox-simulate-new-button">
                        <Sparkles className="mr-2 h-4 w-4" /> Simulate new inbound
                    </Button>
                }
            />
            {loading ? (
                <div className="h-72 animate-pulse rounded-xl border bg-card" />
            ) : conversations.length === 0 ? (
                <div className="rounded-xl border bg-card p-8">
                    <EmptyState
                        icon={InboxIcon}
                        title="No conversations yet"
                        description="Simulate an inbound message to create a conversation. In production, conversations appear automatically as customers message your phone numbers."
                        action={
                            <div className="flex flex-col gap-3 sm:flex-row">
                                <Input
                                    value={simNewContact}
                                    onChange={(e) => setSimNewContact(e.target.value)}
                                    placeholder="15559998888"
                                    className="sm:w-48"
                                    data-testid="inbox-empty-contact-input"
                                />
                                <Button onClick={simulateNew} disabled={simulating} data-testid="inbox-empty-simulate-button">
                                    Create simulated conversation
                                </Button>
                            </div>
                        }
                    />
                </div>
            ) : (
                <div className="grid gap-4 lg:grid-cols-[320px_1fr] xl:grid-cols-[360px_1fr]">
                    <div className="max-h-[calc(100vh-12rem)] overflow-y-auto rounded-xl border bg-card">
                        {conversations.map((c) => (
                            <button
                                key={c.id}
                                onClick={() => setSelectedId(c.id)}
                                data-testid="inbox-conversation-row"
                                className={cn(
                                    "flex w-full flex-col gap-1 border-b px-4 py-3 text-left transition-colors hover:bg-secondary/40",
                                    selectedId === c.id && "bg-secondary/60",
                                )}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="text-sm font-semibold">+{c.contact_wa_id}</div>
                                    <WindowBadge open={c.service_window_open} expiresAt={c.service_window_expires_at} />
                                </div>
                                <div className="truncate text-xs text-muted-foreground">
                                    {c.last_message_direction === "outbound" ? "You: " : ""}{c.last_message_preview || "—"}
                                </div>
                            </button>
                        ))}
                    </div>
                    <div className="flex max-h-[calc(100vh-12rem)] flex-col overflow-hidden rounded-xl border bg-card">
                        {thread ? (
                            <>
                                <div className="flex items-center justify-between border-b px-5 py-3">
                                    <div>
                                        <div className="text-sm font-semibold">+{thread.conversation.contact_wa_id}</div>
                                        <div className="text-[10px] text-muted-foreground">
                                            Phone {thread.conversation.phone_number_id}
                                        </div>
                                    </div>
                                    <WindowBadge open={thread.conversation.service_window_open} expiresAt={thread.conversation.service_window_expires_at} />
                                </div>
                                <div className="flex-1 space-y-2 overflow-y-auto bg-secondary/20 p-4" data-testid="inbox-thread">
                                    {thread.messages.length === 0 && (
                                        <div className="py-8 text-center text-xs text-muted-foreground">No messages yet.</div>
                                    )}
                                    {thread.messages.map((m) => (
                                        <div
                                            key={m.id}
                                            className={cn(
                                                "flex",
                                                m.direction === "outbound" ? "justify-end" : "justify-start",
                                            )}
                                            data-testid={`inbox-message-${m.direction}`}
                                        >
                                            <div
                                                className={cn(
                                                    "max-w-[75%] rounded-2xl px-3 py-2 text-sm shadow-sm",
                                                    m.direction === "outbound"
                                                        ? "rounded-br-sm bg-primary text-primary-foreground"
                                                        : "rounded-bl-sm bg-card border",
                                                )}
                                            >
                                                {m.is_template && (
                                                    <div className="mb-1 text-[10px] uppercase opacity-80">Template · {m.body}</div>
                                                )}
                                                {!m.is_template && <div>{m.body || "(no body)"}</div>}
                                                <div className={cn("mt-1 text-[10px]", m.direction === "outbound" ? "text-primary-foreground/80" : "text-muted-foreground")}>
                                                    {m.status} · {m.created_at ? new Date(m.created_at).toLocaleTimeString() : ""}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="border-t bg-background p-3">
                                    {!thread.conversation.service_window_open && (
                                        <div className="mb-2 rounded-md border bg-[hsl(38_92%_96%)] p-2 text-xs text-[hsl(38_92%_28%)]" data-testid="inbox-window-closed-warning">
                                            Service window is closed. Send an approved template (from Send Template) to re-open it, or simulate an inbound message for testing.
                                        </div>
                                    )}
                                    <div className="flex items-end gap-2">
                                        <Textarea
                                            rows={2}
                                            value={reply}
                                            onChange={(e) => setReply(e.target.value)}
                                            placeholder="Type a session reply..."
                                            disabled={!thread.conversation.service_window_open || sending}
                                            data-testid="inbox-reply-input"
                                        />
                                        <div className="flex flex-col gap-1">
                                            <Button onClick={sendReply} disabled={!thread.conversation.service_window_open || sending || !reply.trim()} data-testid="inbox-reply-send-button">
                                                <Send className="mr-2 h-4 w-4" /> Send
                                            </Button>
                                            <Button variant="outline" size="sm" onClick={simulateInbound} disabled={simulating} data-testid="inbox-simulate-existing-button">
                                                <Sparkles className="mr-1 h-3 w-3" /> Simulate inbound
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                                Select a conversation to view
                            </div>
                        )}
                    </div>
                </div>
            )}
        </AppShell>
    );
}
