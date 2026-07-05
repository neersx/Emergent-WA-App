{
  "brand": {
    "name": "WABA Provider Console (Phase 1)",
    "attributes": [
      "trustworthy",
      "enterprise-ready",
      "communication-first",
      "calm + precise",
      "conversion-focused marketing / data-dense admin"
    ],
    "experience_split": {
      "marketing": "Expressive, airy, conversion-first. Bento feature grid, social proof, pricing emphasis.",
      "admin": "Clean, structured, operational. Sidebar + topbar, tables, badges, empty states, toasts."
    },
    "mode": {
      "default": "light",
      "note": "Phase 1 uses light mode only for clarity and speed. Keep tokens compatible with future dark mode but do not implement dark UI now."
    }
  },

  "design_tokens": {
    "colors_hsl": {
      "note": "Set these in /src/index.css :root (replace current shadcn defaults). Keep gradients decorative only (<=20% viewport).",
      "core": {
        "background": "210 33% 99%",
        "foreground": "222 47% 11%",
        "card": "0 0% 100%",
        "card-foreground": "222 47% 11%",
        "popover": "0 0% 100%",
        "popover-foreground": "222 47% 11%",

        "primary": "173 78% 26%",
        "primary-foreground": "0 0% 100%",

        "secondary": "210 25% 96%",
        "secondary-foreground": "222 47% 11%",

        "muted": "210 25% 96%",
        "muted-foreground": "215 16% 47%",

        "accent": "38 92% 55%",
        "accent-foreground": "222 47% 11%",

        "destructive": "0 84% 60%",
        "destructive-foreground": "0 0% 100%",

        "border": "214 20% 90%",
        "input": "214 20% 90%",
        "ring": "173 78% 26%"
      },

      "admin_surface": {
        "app-shell": "210 33% 98%",
        "sidebar": "222 47% 11%",
        "sidebar-foreground": "210 40% 98%",
        "sidebar-muted": "215 25% 20%",
        "sidebar-border": "215 25% 18%",
        "topbar": "0 0% 100%"
      },

      "status_badges": {
        "queued": { "bg": "215 20% 94%", "fg": "215 25% 25%", "border": "215 18% 86%" },
        "sent": { "bg": "199 95% 94%", "fg": "199 80% 28%", "border": "199 70% 86%" },
        "delivered": { "bg": "152 55% 93%", "fg": "152 55% 26%", "border": "152 40% 84%" },
        "read": { "bg": "238 85% 95%", "fg": "238 55% 35%", "border": "238 55% 88%" },
        "failed": { "bg": "0 90% 96%", "fg": "0 70% 40%", "border": "0 70% 88%" }
      },

      "charts": {
        "chart-1": "173 78% 26%",
        "chart-2": "199 80% 40%",
        "chart-3": "38 92% 55%",
        "chart-4": "152 55% 35%",
        "chart-5": "238 55% 45%"
      },

      "allowed_gradients": {
        "hero_bg": "linear-gradient(135deg, hsl(173 78% 26% / 0.10), hsl(199 80% 40% / 0.10), hsl(38 92% 55% / 0.08))",
        "note": "Use only as section background overlay (blurred), never behind long text blocks."
      }
    },

    "radius_scale": {
      "--radius": "0.75rem",
      "usage": {
        "cards": "rounded-xl",
        "buttons": "rounded-lg",
        "inputs": "rounded-lg",
        "badges": "rounded-full"
      }
    },

    "shadows": {
      "soft": "shadow-[0_1px_0_hsl(214_20%_90%)_inset,0_10px_30px_-20px_hsl(222_47%_11%/0.25)]",
      "lift": "shadow-[0_1px_0_hsl(214_20%_90%)_inset,0_18px_50px_-30px_hsl(222_47%_11%/0.35)]"
    },

    "spacing_scale": {
      "base": "Tailwind spacing scale; prefer these steps for layout rhythm",
      "steps_px": {
        "2": 8,
        "3": 12,
        "4": 16,
        "6": 24,
        "8": 32,
        "10": 40,
        "12": 48,
        "16": 64
      },
      "section_padding": "py-16 md:py-24",
      "container": "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8"
    },

    "typography": {
      "fonts": {
        "heading": "Space Grotesk (600/700)",
        "body": "Inter (400/500)",
        "mono": "IBM Plex Mono (optional for IDs/webhook payload snippets)"
      },
      "google_fonts_import": "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');",
      "tailwind_usage": {
        "heading": "font-[family-name:var(--font-heading)]",
        "body": "font-[family-name:var(--font-body)]"
      },
      "scale": {
        "h1": "text-4xl sm:text-5xl lg:text-6xl tracking-tight",
        "h2": "text-base md:text-lg text-muted-foreground",
        "h3": "text-xl md:text-2xl font-semibold",
        "body": "text-sm md:text-base leading-relaxed",
        "small": "text-xs text-muted-foreground"
      }
    },

    "motion": {
      "library": "framer-motion (already installed)",
      "principles": [
        "Use motion to clarify hierarchy: nav -> hero -> feature cards -> pricing.",
        "Prefer opacity + translateY (6–12px) entrance; avoid large bouncy motion in admin.",
        "Respect prefers-reduced-motion: disable non-essential animations."
      ],
      "durations": {
        "fast": "150ms",
        "base": "220ms",
        "slow": "320ms"
      },
      "easing": {
        "standard": "cubic-bezier(0.2, 0.8, 0.2, 1)",
        "emphasized": "cubic-bezier(0.2, 1, 0.2, 1)"
      },
      "hover_micro": {
        "cards": "hover:-translate-y-0.5 hover:shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]",
        "buttons": "active:scale-[0.98]"
      }
    },

    "accessibility": {
      "wcag": "AA",
      "rules": [
        "All focusable elements must have visible focus ring: focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2.",
        "Do not rely on color alone for status: pair badge color with label text (Queued/Sent/Delivered/Read/Failed).",
        "Use aria-label for icon-only buttons.",
        "Ensure table row actions are reachable via keyboard (DropdownMenu)."
      ]
    }
  },

  "layout_system": {
    "marketing": {
      "nav": {
        "pattern": "Sticky top nav with blur + border; CTA cluster on right.",
        "classes": "sticky top-0 z-50 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        "structure": [
          "Left: logo + 3-4 links (Features, Pricing, Security, Contact)",
          "Right: Sign in (ghost) + Get started (primary)"
        ]
      },
      "hero": {
        "pattern": "Left-aligned copy + right bento preview card stack (or screenshot placeholder).",
        "grid": "grid gap-10 lg:grid-cols-2 items-center",
        "background": "Use allowed hero_bg gradient overlay as an absolutely-positioned blurred blob (max 20% viewport)."
      },
      "feature_bento": {
        "pattern": "Asymmetric bento grid (scan-friendly).",
        "grid": "grid gap-4 md:gap-6 md:grid-cols-12",
        "card_spans": [
          "Primary card: col-span-12 md:col-span-7",
          "Secondary: col-span-12 md:col-span-5",
          "Tertiary: 3 cards col-span-12 md:col-span-4"
        ]
      },
      "pricing": {
        "pattern": "3-tier cards; middle tier highlighted.",
        "grid": "grid gap-6 lg:grid-cols-3",
        "highlight": "Pro tier uses ring-2 ring-primary/30 and subtle bg-primary/5"
      },
      "faq": {
        "pattern": "Accordion; 1-col mobile, 2-col desktop split list.",
        "grid": "grid gap-6 lg:grid-cols-2"
      },
      "footer": {
        "pattern": "Dense but breathable; 4 columns + bottom legal row.",
        "classes": "border-t bg-card"
      }
    },

    "admin": {
      "app_shell": {
        "pattern": "Sidebar (collapsible) + topbar + scrollable content.",
        "grid": "min-h-screen bg-[hsl(var(--background))]",
        "sidebar_width": "w-72 (expanded) / w-16 (collapsed)"
      },
      "topbar": {
        "pattern": "Tenant name + environment badge + search + user menu.",
        "classes": "sticky top-0 z-40 border-b bg-background/90 backdrop-blur"
      },
      "content": {
        "pattern": "Page header + KPI row + main table/cards.",
        "container": "mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8 py-6"
      }
    }
  },

  "component_recipes": {
    "note": "All examples are for .js React components using Tailwind + shadcn/ui. Add data-testid to every interactive element and key info.",

    "sticky_marketing_nav": {
      "component_path": ["/app/frontend/src/components/ui/navigation-menu.jsx", "/app/frontend/src/components/ui/button.jsx"],
      "recipe": {
        "wrapper": "sticky top-0 z-50 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        "inner": "mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8",
        "cta_group": "flex items-center gap-2",
        "buttons": {
          "signin": "variant=ghost className=\"h-9\"",
          "get_started": "variant=default className=\"h-9 shadow-sm\""
        }
      },
      "testids": {
        "nav": "marketing-nav",
        "signin": "marketing-nav-signin-button",
        "get-started": "marketing-nav-get-started-button"
      }
    },

    "sidebar_item": {
      "component_path": ["/app/frontend/src/components/ui/button.jsx", "/app/frontend/src/components/ui/tooltip.jsx", "/app/frontend/src/components/ui/collapsible.jsx"],
      "recipe": {
        "item": "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-200 hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--accent))]",
        "active": "bg-white/12 text-white",
        "icon": "h-4 w-4 opacity-90",
        "collapsed_tooltip": "Wrap icon-only state with Tooltip for discoverability"
      },
      "testids": {
        "nav-item": "admin-sidebar-nav-item"
      }
    },

    "stat_card": {
      "component_path": ["/app/frontend/src/components/ui/card.jsx", "/app/frontend/src/components/ui/badge.jsx"],
      "recipe": {
        "card": "rounded-xl border bg-card p-5 shadow-[0_1px_0_hsl(214_20%_90%)_inset]",
        "label": "text-xs font-medium text-muted-foreground",
        "value": "mt-2 text-2xl font-semibold tracking-tight",
        "delta_badge": "mt-3 inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-1 text-xs text-primary"
      },
      "testids": {
        "stat": "admin-stat-card",
        "stat-value": "admin-stat-card-value"
      }
    },

    "status_badge": {
      "component_path": ["/app/frontend/src/components/ui/badge.jsx"],
      "recipe": {
        "base": "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        "variants": {
          "queued": "bg-[hsl(215_20%_94%)] text-[hsl(215_25%_25%)] border-[hsl(215_18%_86%)]",
          "sent": "bg-[hsl(199_95%_94%)] text-[hsl(199_80%_28%)] border-[hsl(199_70%_86%)]",
          "delivered": "bg-[hsl(152_55%_93%)] text-[hsl(152_55%_26%)] border-[hsl(152_40%_84%)]",
          "read": "bg-[hsl(238_85%_95%)] text-[hsl(238_55%_35%)] border-[hsl(238_55%_88%)]",
          "failed": "bg-[hsl(0_90%_96%)] text-[hsl(0_70%_40%)] border-[hsl(0_70%_88%)]"
        }
      },
      "testids": {
        "message-status": "message-status-badge"
      }
    },

    "page_header_with_breadcrumb": {
      "component_path": ["/app/frontend/src/components/ui/breadcrumb.jsx", "/app/frontend/src/components/ui/button.jsx", "/app/frontend/src/components/ui/separator.jsx"],
      "recipe": {
        "wrapper": "mb-6",
        "breadcrumb": "text-xs text-muted-foreground",
        "row": "mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
        "title": "text-2xl font-semibold tracking-tight",
        "actions": "flex items-center gap-2"
      },
      "testids": {
        "page-title": "admin-page-title",
        "primary-action": "admin-page-primary-action"
      }
    },

    "modal_dialog_pattern": {
      "component_path": ["/app/frontend/src/components/ui/dialog.jsx", "/app/frontend/src/components/ui/alert-dialog.jsx"],
      "recipe": {
        "dialog": "Use Dialog for forms; AlertDialog for destructive confirmations.",
        "content_classes": "rounded-xl border bg-card p-0 shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]",
        "header": "px-6 pt-6",
        "body": "px-6 py-4",
        "footer": "flex flex-col-reverse gap-2 px-6 pb-6 sm:flex-row sm:justify-end"
      },
      "testids": {
        "open": "dialog-open-button",
        "confirm": "dialog-confirm-button",
        "cancel": "dialog-cancel-button"
      }
    },

    "empty_state": {
      "component_path": ["/app/frontend/src/components/ui/card.jsx", "/app/frontend/src/components/ui/button.jsx"],
      "recipe": {
        "wrapper": "rounded-xl border bg-card p-10 text-center",
        "icon": "mx-auto mb-4 h-10 w-10 text-primary",
        "title": "text-base font-semibold",
        "desc": "mt-1 text-sm text-muted-foreground",
        "actions": "mt-6 flex flex-col items-center justify-center gap-2 sm:flex-row"
      },
      "testids": {
        "empty": "empty-state",
        "primary": "empty-state-primary-action",
        "secondary": "empty-state-secondary-action"
      }
    },

    "pricing_card": {
      "component_path": ["/app/frontend/src/components/ui/card.jsx", "/app/frontend/src/components/ui/button.jsx", "/app/frontend/src/components/ui/badge.jsx", "/app/frontend/src/components/ui/separator.jsx"],
      "recipe": {
        "card": "relative rounded-2xl border bg-card p-6",
        "popular": "ring-2 ring-primary/30 bg-primary/5",
        "plan": "text-sm font-semibold",
        "price": "mt-3 text-4xl font-semibold tracking-tight",
        "features": "mt-6 space-y-3 text-sm",
        "cta": "mt-8 w-full"
      },
      "testids": {
        "pricing-tier": "pricing-tier-card",
        "pricing-cta": "pricing-tier-cta-button"
      }
    },

    "faq_accordion": {
      "component_path": ["/app/frontend/src/components/ui/accordion.jsx"],
      "recipe": {
        "item": "rounded-xl border bg-card px-4",
        "trigger": "py-4 text-left text-sm font-medium",
        "content": "pb-4 text-sm text-muted-foreground"
      },
      "testids": {
        "faq-item": "faq-accordion-item"
      }
    },

    "toast_patterns": {
      "component_path": ["/app/frontend/src/components/ui/sonner.jsx"],
      "recipe": {
        "usage": "Use sonner for all toasts. Success for connect WABA, template send; error for failed send; info for queued.",
        "copy": {
          "success": "Template sent — delivery updates will appear in Message Log.",
          "error": "Send failed — check template approval and recipient formatting.",
          "info": "Queued — WhatsApp provider is processing your request."
        }
      },
      "testids": {
        "toast-region": "toast-region"
      }
    }
  },

  "auth_screens": {
    "pattern": "Centered card with subtle decorative side panel on desktop; single column on mobile.",
    "layout": {
      "wrapper": "min-h-screen bg-[hsl(var(--background))]",
      "grid": "mx-auto grid min-h-screen max-w-6xl grid-cols-1 lg:grid-cols-2",
      "form_col": "flex items-center justify-center px-4 py-10",
      "decor_col": "hidden lg:block relative overflow-hidden border-l bg-[hsl(var(--secondary))]"
    },
    "decor": {
      "idea": "Use CSS-only blurred blobs + subtle noise overlay (no external images required).",
      "classes": "absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,hsl(173_78%_26%/0.18),transparent_55%),radial-gradient(circle_at_80%_30%,hsl(199_80%_40%/0.14),transparent_55%),radial-gradient(circle_at_60%_80%,hsl(38_92%_55%/0.10),transparent_55%)]"
    },
    "form_card": {
      "classes": "w-full max-w-md rounded-2xl border bg-card p-6 sm:p-8 shadow-[0_18px_50px_-30px_hsl(222_47%_11%/0.35)]",
      "fields": "Use shadcn Input, Label, Button, InputOTP for MFA.",
      "mfa": "Enroll screen shows QR placeholder + secret + InputOTP verify."
    },
    "testids": {
      "login-email": "login-email-input",
      "login-password": "login-password-input",
      "login-submit": "login-submit-button",
      "mfa-otp": "mfa-otp-input",
      "mfa-verify": "mfa-verify-button"
    }
  },

  "image_urls": {
    "note": "Image provider tool unavailable in this environment (stock search failed). Use CSS decorative gradients/noise for MVP. If you later add images, prefer abstract comms illustrations and avoid WhatsApp logo usage.",
    "categories": [
      {
        "category": "marketing_hero",
        "description": "Optional: abstract communication illustration or dashboard screenshot mock.",
        "urls": []
      },
      {
        "category": "social_proof",
        "description": "Customer logos as simple monochrome SVG wordmarks (self-made placeholders).",
        "urls": []
      },
      {
        "category": "auth_decor",
        "description": "No external images required; use CSS blobs + noise overlay.",
        "urls": []
      }
    ]
  },

  "libraries_and_scaffolds": {
    "framer_motion": {
      "use_cases": [
        "Marketing hero entrance",
        "Bento card hover lift",
        "Sidebar collapse animation (width + label fade)"
      ],
      "scaffold_js": "// Example: const MotionDiv = motion.div; <MotionDiv initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} transition={{duration:0.32,ease:[0.2,0.8,0.2,1]}} />"
    },
    "charts": {
      "library": "recharts (optional for Phase 1)",
      "install": "npm i recharts",
      "use_cases": ["Message volume over time", "Delivery funnel"],
      "empty_state": "If no data, show EmptyState with date range CTA."
    }
  },

  "instructions_to_main_agent": [
    "Replace CRA default App.css usage; do NOT center the app container globally.",
    "Update /src/index.css :root tokens to the provided HSL values; keep light mode only.",
    "Marketing pages: implement sticky nav, hero (left copy/right preview), bento feature grid, pricing (3 tiers), FAQ accordion, contact form, footer.",
    "Admin portal: implement sidebar + topbar shell; use PageHeaderWithBreadcrumb, StatCards, Tables with StatusBadge, EmptyState, Sonner toasts.",
    "Auth screens: use 2-col layout on desktop with CSS decorative panel; use shadcn InputOTP for MFA.",
    "Every interactive element and key info must include stable data-testid attributes (kebab-case).",
    "Gradients: only use the allowed hero background overlay; never apply gradients to text-heavy areas or small elements."
  ],

  "general_ui_ux_design_guidelines_appendix": "<General UI UX Design Guidelines>\n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
