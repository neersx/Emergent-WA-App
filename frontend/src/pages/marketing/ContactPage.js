import { useState } from "react";
import { MarketingNav, MarketingFooter } from "@/components/Marketing";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Mail, Phone, MapPin } from "lucide-react";

export default function ContactPage() {
    const [submitting, setSubmitting] = useState(false);
    const [form, setForm] = useState({ name: "", email: "", message: "" });

    const submit = (e) => {
        e.preventDefault();
        if (!form.name || !form.email || !form.message) {
            toast.error("Please fill in all fields.");
            return;
        }
        setSubmitting(true);
        // mock submit
        setTimeout(() => {
            toast.success("Thanks! We'll get back to you within one business day.");
            setForm({ name: "", email: "", message: "" });
            setSubmitting(false);
        }, 600);
    };

    return (
        <div className="min-h-screen bg-background">
            <MarketingNav />
            <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
                <div className="grid gap-10 lg:grid-cols-2">
                    <div>
                        <div className="text-sm font-medium text-primary">Contact</div>
                        <h1 className="mt-2 text-4xl font-semibold tracking-tight sm:text-5xl">
                            Talk to the team
                        </h1>
                        <p className="mt-3 text-muted-foreground">
                            Questions, demos, partnership inquiries—we read every message.
                        </p>
                        <div className="mt-8 space-y-4 text-sm">
                            <div className="flex items-center gap-3">
                                <Mail className="h-4 w-4 text-primary" />
                                <span>hello@wabaconsole.example</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <Phone className="h-4 w-4 text-primary" />
                                <span>+1 (415) 555-0142</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <MapPin className="h-4 w-4 text-primary" />
                                <span>San Francisco · Remote-first</span>
                            </div>
                        </div>
                    </div>
                    <form
                        onSubmit={submit}
                        className="rounded-2xl border bg-card p-6 sm:p-8 shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]"
                        data-testid="contact-form"
                    >
                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="name">Your name</Label>
                                <Input
                                    id="name"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    placeholder="Jane Doe"
                                    data-testid="contact-name-input"
                                />
                            </div>
                            <div>
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={form.email}
                                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                                    placeholder="you@company.com"
                                    data-testid="contact-email-input"
                                />
                            </div>
                            <div>
                                <Label htmlFor="message">Message</Label>
                                <Textarea
                                    id="message"
                                    value={form.message}
                                    onChange={(e) => setForm({ ...form, message: e.target.value })}
                                    rows={5}
                                    placeholder="Tell us about your use case..."
                                    data-testid="contact-message-input"
                                />
                            </div>
                            <Button
                                type="submit"
                                className="w-full"
                                disabled={submitting}
                                data-testid="contact-submit-button"
                            >
                                {submitting ? "Sending..." : "Send message"}
                            </Button>
                        </div>
                    </form>
                </div>
            </section>
            <MarketingFooter />
        </div>
    );
}
