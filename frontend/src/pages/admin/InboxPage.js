import { useEffect, useState, useRef, useCallback } from "react";
import AppShell from "@/components/AppShell";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
    Inbox as InboxIcon, Send, Sparkles, Clock, User, CheckCheck,
    Check, ImageIcon, FileText, Mic, Video, MapPin, Phone, List,
    Smile, X, ChevronRight, RefreshCw, AlertCircle, Wifi, WifiOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNowStrict, formatDistanceToNow } from "date-fns";

// ─── Window badge ─────────────────────────────────────────────────────────────

function WindowBadge({ open, expiresAt, freeEntry }) {
    if (!expiresAt) {
        return (
            <span className="inline-flex items-center gap-1 rounded-full border bg-secondary px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                <Clock className="h-3 w-3" /> No window
            </span>
        );
    }
    if (freeEntry) {
        return (
            <span className="inline-flex items-center gap-1 rounded-full border bg-[hsl(270_60%_95%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(270_60%_35%)]">
                <Clock className="h-3 w-3" /> Free 72h window
            </span>
        );
    }
    if (open) {
        const rel = formatDistanceToNowStrict(new Date(expiresAt), { addSuffix: false });
        return (
            <span className="inline-flex items-center gap-1 rounded-full border bg-[hsl(152_55%_93%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(152_55%_26%)]" data-testid="window-badge-open">
                <Clock className="h-3 w-3" /> {rel} left
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 rounded-full border bg-[hsl(0_90%_96%)] px-2 py-0.5 text-[10px] font-medium text-[hsl(0_70%_40%)]" data-testid="window-badge-closed">
            <Clock className="h-3 w-3" /> Closed
        </span>
    );
}

// ─── Message type renderer ────────────────────────────────────────────────────

function MessageContent({ m }) {
    const type = m.msg_type || "text";
    if (type === "image") return (
        <div>
            {m.media_url
                ? <img src={m.media_url} alt="img" className="rounded max-h-48 max-w-full object-cover" />
                : <div className="flex items-center gap-1 text-xs opacity-70"><ImageIcon className="h-4 w-4" /> Image</div>}
            {m.caption && <p className="text-xs mt-1">{m.caption}</p>}
        </div>
    );
    if (type === "video") return (
        <div>
            {m.media_url
                ? <video src={m.media_url} controls className="rounded max-h-48 max-w-full" />
                : <div className="flex items-center gap-1 text-xs opacity-70"><Video className="h-4 w-4" /> Video</div>}
            {m.caption && <p className="text-xs mt-1">{m.caption}</p>}
        </div>
    );
    if (type === "audio") return m.media_url
        ? <audio src={m.media_url} controls className="max-w-full" />
        : <div className="flex items-center gap-1 text-xs opacity-70"><Mic className="h-4 w-4" /> Voice message</div>;
    if (type === "document") return (
        <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 shrink-0" />
            <div>
                <p className="text-sm font-medium">{m.filename || "Document"}</p>
                {m.media_url && <a href={m.media_url} target="_blank" rel="noreferrer" className="text-xs underline">Download</a>}
            </div>
        </div>
    );
    if (type === "location") return (
        <div className="text-sm">
            <div className="flex items-center gap-1"><MapPin className="h-4 w-4 shrink-0" />
                <span className="font-medium">{m.location_name || "Location"}</span></div>
            {m.location_address && <p className="text-xs mt-0.5 opacity-80">{m.location_address}</p>}
            {m.latitude && (
                <a href={`https://maps.google.com/?q=${m.latitude},${m.longitude}`} target="_blank" rel="noreferrer"
                   className="text-xs underline mt-1 block">Open in Maps</a>
            )}
        </div>
    );
    if (type === "contacts") return (
        <div className="flex items-center gap-2 text-sm">
            <User className="h-4 w-4" /> <span>{m.contact_name || "Contact"}</span>
        </div>
    );
    if (type === "interactive") return (
        <div className="text-sm">
            <div className="flex items-center gap-1 mb-0.5"><List className="h-4 w-4" />
                <span className="font-medium">{m.interactive_reply_title || m.body || "Interactive reply"}</span></div>
            {m.interactive_reply_id && <p className="text-[10px] opacity-70">ID: {m.interactive_reply_id}</p>}
        </div>
    );
    if (type === "reaction") return (
        <div className="text-2xl leading-none">{m.reaction_emoji || "👍"}</div>
    );
    if (type === "sticker") return (
        <div className="text-xs opacity-70">Sticker</div>
    );
    // template / text
    if (m.is_template) return (
        <div><p className="text-[10px] uppercase opacity-70 mb-0.5">Template · {m.template_name}</p>
             {m.body && <p>{m.body}</p>}</div>
    );
    return <p className="whitespace-pre-wrap break-words">{m.body || "(no content)"}</p>;
}

function MessageBubble({ m }) {
    const out = m.direction === "outbound";
    return (
        <div className={cn("flex", out ? "justify-end" : "justify-start")}
             data-testid={`inbox-message-${m.direction}`}>
            <div className={cn(
                "max-w-[75%] rounded-2xl px-3 py-2 shadow-sm",
                out ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-card border",
            )}>
                <MessageContent m={m} />
                <div className={cn("mt-1 flex items-center gap-1 text-[10px]",
                    out ? "text-primary-foreground/70 justify-end" : "text-muted-foreground")}>
                    {m.status === "read" && <CheckCheck className="h-3 w-3 text-[hsl(152_55%_46%)]" />}
                    {m.status === "delivered" && <CheckCheck className="h-3 w-3" />}
                    {m.status === "sent" && <Check className="h-3 w-3" />}
                    <span>{m.status}</span>
                    <span>·</span>
                    <span>{m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}</span>
                </div>
            </div>
        </div>
    );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

export default function InboxPage() {
    const [conversations, setConversations] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [thread, setThread] = useState(null);
    const [reply, setReply] = useState("");
    const [sending, setSending] = useState(false);
    const [simulating, setSimulating] = useState(false);
    const [loading, setLoading] = useState(true);
    const [wsConnected, setWsConnected] = useState(false);
    const [simNewContact, setSimNewContact] = useState("15559998888");
    const [simBody, setSimBody] = useState("Hi! I have a question about my order.");
    const wsRef = useRef(null);
    const threadEndRef = useRef(null);

    // ── Data loading ──────────────────────────────────────────────────────────

    const loadConversations = useCallback(async () => {
        try {
            const r = await api.get("/inbox/conversations");
            setConversations(r.data);
        } catch { /* noop */ }
        finally { setLoading(false); }
    }, []);

    const loadThread = useCallback(async (id) => {
        if (!id) return;
        try {
            const r = await api.get(`/inbox/conversations/${id}/messages`);
            setThread(r.data);
        } catch { setThread(null); }
    }, []);

    useEffect(() => {
        loadConversations();
    }, [loadConversations]);

    useEffect(() => {
        if (selectedId) {
            loadThread(selectedId);
            // Mark as read locally
            setConversations(prev =>
                prev.map(c => c.id === selectedId ? { ...c, unread_count: 0 } : c)
            );
        }
    }, [selectedId, loadThread]);

    // Scroll to bottom on new messages
    useEffect(() => {
        threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [thread?.messages?.length]);

    // ── WebSocket ─────────────────────────────────────────────────────────────

    useEffect(() => {
        const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
        const wsUrl = backendUrl.replace(/^https/, "wss").replace(/^http/, "ws") + "/api/ws/inbox";
        let reconnectTimeout;
        let alive = true;

        const connect = () => {
            if (!alive) return;
            try {
                const ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => {};
                ws.onmessage = (event) => {
                    if (event.data === "pong") return;
                    try {
                        const msg = JSON.parse(event.data);
                        if (msg.type === "auth_ok") { setWsConnected(true); return; }
                        if (msg.type === "auth_failed") return;
                        if (msg.type === "ping") { ws.send("ping"); return; }

                        if (msg.type === "new_message") {
                            const convId = msg.conversation_id;
                            // Update conversation list
                            setConversations(prev => {
                                const existing = prev.find(c => c.id === convId);
                                if (existing) {
                                    return prev.map(c => c.id === convId ? {
                                        ...c,
                                        last_message_preview: msg.message?.body || msg.message?.msg_type || "",
                                        last_message_direction: msg.message?.direction,
                                        last_message_at: msg.message?.created_at,
                                        unread_count: convId === selectedId ? 0 : (c.unread_count || 0) + 1,
                                    } : c);
                                }
                                // New conversation - reload list
                                loadConversations();
                                return prev;
                            });
                            // If this is the current thread, append message
                            if (convId === selectedId) {
                                setThread(prev => prev ? {
                                    ...prev,
                                    messages: [...(prev.messages || []), msg.message],
                                } : prev);
                            }
                        }

                        if (msg.type === "status_update") {
                            setThread(prev => {
                                if (!prev) return prev;
                                return {
                                    ...prev,
                                    messages: prev.messages.map(m =>
                                        (m.meta_message_id && m.meta_message_id === msg.meta_message_id)
                                            ? { ...m, status: msg.status }
                                            : m
                                    ),
                                };
                            });
                        }

                        if (msg.type === "template_update") {
                            toast.info(`Template "${msg.template_name}" → ${msg.status}${msg.reason ? ": " + msg.reason : ""}`);
                        }
                    } catch { /* noop */ }
                };
                ws.onerror = () => {};
                ws.onclose = () => {
                    setWsConnected(false);
                    wsRef.current = null;
                    if (alive) {
                        reconnectTimeout = setTimeout(connect, 4000);
                    }
                };
            } catch { /* noop */ }
        };
        connect();
        return () => {
            alive = false;
            clearTimeout(reconnectTimeout);
            wsRef.current?.close();
        };
    }, [selectedId, loadConversations]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── Actions ───────────────────────────────────────────────────────────────

    const sendReply = async () => {
        if (!reply.trim() || !selectedId) return;
        setSending(true);
        try {
            const r = await api.post(`/inbox/conversations/${selectedId}/reply`, { body: reply });
            setReply("");
            setThread(prev => prev ? { ...prev, messages: [...(prev.messages || []), r.data] } : prev);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Reply failed");
        } finally { setSending(false); }
    };

    const simulateInbound = async () => {
        setSimulating(true);
        try {
            if (selectedId) {
                await api.post(`/inbox/conversations/${selectedId}/simulate-inbound`, { body: simBody });
                toast.success("Simulated inbound added");
                await loadThread(selectedId);
            } else {
                const r = await api.post(`/inbox/simulate-inbound`, { contact_wa_id: simNewContact, body: simBody });
                toast.success("New conversation created");
                await loadConversations();
                setSelectedId(r.data.conversation_id);
            }
        } catch (err) { toast.error(err?.response?.data?.detail || "Simulate failed"); }
        finally { setSimulating(false); }
    };

    const simulateNew = async () => {
        setSimulating(true);
        try {
            const r = await api.post(`/inbox/simulate-inbound`, { contact_wa_id: simNewContact, body: simBody });
            toast.success("New conversation created");
            await loadConversations();
            setSelectedId(r.data.conversation_id);
        } catch (err) { toast.error(err?.response?.data?.detail || "Simulate failed"); }
        finally { setSimulating(false); }
    };

    const closeConv = async () => {
        if (!selectedId) return;
        try {
            await api.post(`/inbox/conversations/${selectedId}/close`, {});
            setThread(prev => prev ? { ...prev, conversation: { ...prev.conversation, status: "closed" } } : prev);
            setConversations(prev => prev.map(c => c.id === selectedId ? { ...c, status: "closed" } : c));
            toast.success("Conversation closed");
        } catch (err) { toast.error(err?.response?.data?.detail || "Close failed"); }
    };

    const reopenConv = async () => {
        if (!selectedId) return;
        try {
            await api.post(`/inbox/conversations/${selectedId}/reopen`, {});
            setThread(prev => prev ? { ...prev, conversation: { ...prev.conversation, status: "open" } } : prev);
            setConversations(prev => prev.map(c => c.id === selectedId ? { ...c, status: "open" } : c));
            toast.success("Conversation reopened");
        } catch (err) { toast.error(err?.response?.data?.detail || "Reopen failed"); }
    };

    const conv = thread?.conversation;
    const windowOpen = conv?.service_window_open || conv?.free_entry_point;

    return (
        <AppShell>
            <PageHeader
                breadcrumb={<span>Admin / Inbox</span>}
                title="Inbox"
                description="Conversations with your WhatsApp contacts. Service messages require an open 24-hour window."
                actions={
                    <div className="flex items-center gap-2">
                        {wsConnected
                            ? <span className="flex items-center gap-1 text-xs text-[hsl(152_55%_35%)]"><Wifi className="h-3 w-3" /> Live</span>
                            : <span className="flex items-center gap-1 text-xs text-muted-foreground"><WifiOff className="h-3 w-3" /> Polling</span>}
                        <Button onClick={() => setSelectedId(null) || simulateNew()} variant="outline" disabled={simulating} data-testid="inbox-simulate-new-button">
                            <Sparkles className="mr-2 h-4 w-4" /> Simulate new
                        </Button>
                    </div>
                }
            />

            {loading ? (
                <div className="h-72 animate-pulse rounded-xl border bg-card" />
            ) : conversations.length === 0 ? (
                <div className="rounded-xl border bg-card p-8">
                    <EmptyState icon={InboxIcon} title="No conversations yet"
                        description="Simulate an inbound message or wait for real WhatsApp contacts to message you."
                        action={
                            <div className="flex flex-col gap-3 sm:flex-row">
                                <Input value={simNewContact} onChange={e => setSimNewContact(e.target.value)} placeholder="15559998888" className="sm:w-48" data-testid="inbox-empty-contact-input" />
                                <Button onClick={simulateNew} disabled={simulating} data-testid="inbox-empty-simulate-button">
                                    Create simulated conversation
                                </Button>
                            </div>
                        }
                    />
                </div>
            ) : (
                <div className="grid gap-0 lg:grid-cols-[320px_1fr] xl:grid-cols-[360px_1fr] rounded-xl border overflow-hidden bg-card" style={{ height: "calc(100vh - 13rem)" }}>
                    {/* ── Conversation list ── */}
                    <div className="flex flex-col border-r overflow-hidden">
                        <div className="border-b px-3 py-2 text-xs font-medium text-muted-foreground bg-secondary/30">
                            {conversations.length} conversation{conversations.length !== 1 ? "s" : ""}
                        </div>
                        <div className="flex-1 overflow-y-auto">
                            {conversations.map(c => (
                                <button key={c.id} onClick={() => setSelectedId(c.id)}
                                        data-testid="inbox-conversation-row"
                                        className={cn(
                                            "flex w-full flex-col gap-1 border-b px-4 py-3 text-left transition-colors hover:bg-secondary/40",
                                            selectedId === c.id && "bg-secondary/60",
                                        )}>
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                            <span className="font-semibold text-sm truncate">+{c.contact_wa_id}</span>
                                            {c.status === "closed" && <Badge variant="outline" className="text-[10px] shrink-0">Closed</Badge>}
                                        </div>
                                        <div className="flex items-center gap-1 shrink-0">
                                            {c.unread_count > 0 && (
                                                <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] text-primary-foreground font-bold">
                                                    {c.unread_count}
                                                </span>
                                            )}
                                            <WindowBadge open={c.service_window_open} expiresAt={c.service_window_expires_at} freeEntry={c.free_entry_point} />
                                        </div>
                                    </div>
                                    <div className="truncate text-xs text-muted-foreground">
                                        {c.last_message_direction === "outbound" ? "You: " : ""}{c.last_message_preview || "—"}
                                    </div>
                                    {c.assigned_to && (
                                        <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                                            <User className="h-2.5 w-2.5" /> Assigned
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* ── Thread view ── */}
                    <div className="flex flex-col overflow-hidden">
                        {thread ? (
                            <>
                                {/* Thread header */}
                                <div className="flex items-center justify-between border-b px-4 py-2.5 shrink-0 bg-background">
                                    <div className="flex items-center gap-3">
                                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-sm font-bold text-muted-foreground">
                                            {conv.contact_wa_id?.slice(-2)}
                                        </div>
                                        <div>
                                            <div className="font-semibold text-sm">+{conv.contact_wa_id}</div>
                                            <div className="text-[10px] text-muted-foreground">Phone ID: {conv.phone_number_id?.slice(-8)}</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <WindowBadge open={conv.service_window_open} expiresAt={conv.service_window_expires_at} freeEntry={conv.free_entry_point} />
                                        {conv.status === "open" ? (
                                            <Button variant="outline" size="sm" onClick={closeConv} className="h-7 text-xs">
                                                <X className="h-3 w-3 mr-1" /> Close
                                            </Button>
                                        ) : (
                                            <Button variant="outline" size="sm" onClick={reopenConv} className="h-7 text-xs">
                                                <RefreshCw className="h-3 w-3 mr-1" /> Reopen
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                {/* Messages */}
                                <div className="flex-1 space-y-2 overflow-y-auto bg-secondary/10 p-4" data-testid="inbox-thread">
                                    {thread.messages.length === 0 && (
                                        <div className="py-8 text-center text-xs text-muted-foreground">No messages yet.</div>
                                    )}
                                    {thread.messages.map(m => <MessageBubble key={m.id} m={m} />)}
                                    <div ref={threadEndRef} />
                                </div>

                                {/* Reply composer */}
                                <div className="border-t bg-background p-3 shrink-0">
                                    {!windowOpen && (
                                        <div className="mb-2 flex items-start gap-2 rounded-md border bg-[hsl(38_92%_96%)] p-2 text-xs text-[hsl(38_92%_28%)]"
                                             data-testid="inbox-window-closed-warning">
                                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                                            <span>Service window is closed. Send an approved template to re-open it, or simulate an inbound message.</span>
                                        </div>
                                    )}
                                    {conv.status === "closed" && (
                                        <div className="mb-2 flex items-start gap-2 rounded-md border bg-secondary/40 p-2 text-xs text-muted-foreground">
                                            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                                            <span>Conversation is closed. Reopen to reply.</span>
                                        </div>
                                    )}
                                    <div className="flex items-end gap-2">
                                        <Textarea
                                            rows={2}
                                            value={reply}
                                            onChange={e => setReply(e.target.value)}
                                            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendReply(); } }}
                                            placeholder={windowOpen && conv.status !== "closed" ? "Type a reply… (Enter to send)" : "Service window closed"}
                                            disabled={!windowOpen || sending || conv.status === "closed"}
                                            data-testid="inbox-reply-input"
                                            className="resize-none"
                                        />
                                        <div className="flex flex-col gap-1">
                                            <Button onClick={sendReply}
                                                    disabled={!windowOpen || sending || !reply.trim() || conv.status === "closed"}
                                                    data-testid="inbox-reply-send-button" className="h-9">
                                                <Send className="h-4 w-4" />
                                            </Button>
                                            <Button variant="outline" size="sm" onClick={simulateInbound} disabled={simulating}
                                                    className="h-7 text-[10px] px-2" data-testid="inbox-simulate-existing-button">
                                                <Sparkles className="h-3 w-3" />
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                                <div className="text-center">
                                    <InboxIcon className="h-10 w-10 mx-auto mb-2 opacity-30" />
                                    <p>Select a conversation</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </AppShell>
    );
}
