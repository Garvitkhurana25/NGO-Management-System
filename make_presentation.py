# -*- coding: utf-8 -*-
"""Generate the NGO Operations Management Platform presentation (.pptx).

Uses python-pptx (>=1.0). Produces an editable 16:9 deck styled with the app's
"Warm Mission" palette (forest-green brand, amber accent, cream paper).

Run:  .venv\\Scripts\\python.exe make_presentation.py
"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---- Warm Mission palette -------------------------------------------------
GREEN = RGBColor(0x1B, 0x7A, 0x63)      # brand forest green
GREEN_DEEP = RGBColor(0x12, 0x55, 0x45)  # darker green (shadows / title bar)
SAGE = RGBColor(0x3F, 0xA6, 0x8B)       # lighter green accent
AMBER = RGBColor(0xE8, 0xA3, 0x3D)      # warm amber accent
CREAM = RGBColor(0xF7, 0xF5, 0xF0)      # paper ground
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x2E, 0x2B, 0x26)        # warm charcoal text
MUTED = RGBColor(0x6B, 0x65, 0x5C)      # secondary text

SW, SH = Inches(13.333), Inches(7.5)     # 16:9 slide size


def base_presentation():
    prs = Presentation()
    prs.slide_width = SW
    prs.slide_height = SH
    return prs


def add_slide(prs):
    """Blank slide with a cream background."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    bg.fill.solid()
    bg.fill.fore_color.rgb = CREAM
    bg.line.fill.background()
    bg.shadow.inherit = False
    return slide


def textbox(slide, l, t, w, h):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    return box, tf


def set_run(run, text, size, color, bold=False, italic=False, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    return run


def para(tf, first=False, space_after=6, align=PP_ALIGN.LEFT, level=0):
    if first and not tf.paragraphs[0].runs:
        p = tf.paragraphs[0]
    else:
        p = tf.add_paragraph()
    p.space_after = Pt(space_after)
    p.alignment = align
    p.level = level
    return p


def add_text(slide, l, t, w, h, text, size, color, bold=False, align=PP_ALIGN.LEFT,
             font="Calibri", anchor=MSO_ANCHOR.TOP):
    box, tf = textbox(slide, l, t, w, h)
    tf.vertical_anchor = anchor
    p = para(tf, first=True)
    set_run(p.add_run(), text, size, color, bold, font=font)
    return box


def add_bullets(slide, l, t, w, h, items, size=20, color=INK, gap=10,
                bullet_color=AMBER, sub=None):
    """items: list[str] top-level, sub: list[list[str]] optional sub-bullets."""
    box, tf = textbox(slide, l, t, w, h)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    first = True
    for i, item in enumerate(items):
        p = para(tf, first=first, space_after=gap)
        first = False
        set_run(p.add_run(), "▪  ", size, bullet_color, bold=True)
        set_run(p.add_run(), item, size, color)
        if sub and i < len(sub):
            for sitem in sub[i]:
                ps = para(tf, space_after=gap, level=1)
                set_run(ps.add_run(), "–  ", size - 3, GREEN, bold=True)
                set_run(ps.add_run(), sitem, size - 3, MUTED)
    return box


def header_band(slide, title, subtitle=None):
    """Green band across the top with title + optional subtitle."""
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(1.05))
    band.fill.solid()
    band.fill.fore_color.rgb = GREEN
    band.line.fill.background()
    band.shadow.inherit = False
    add_text(slide, Inches(0.55), Inches(0.13), Inches(12.2), Inches(0.62),
             title, 30, WHITE, bold=True)
    if subtitle:
        add_text(slide, Inches(0.57), Inches(0.68), Inches(12.2), Inches(0.36),
                 subtitle, 15, SAGE)
    # amber accent strip
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(1.05), SW, Inches(0.06))
    strip.fill.solid()
    strip.fill.fore_color.rgb = AMBER
    strip.line.fill.background()
    strip.shadow.inherit = False


def footer(slide, num):
    add_text(slide, Inches(12.45), Inches(7.05), Inches(0.7), Inches(0.35),
             str(num), 12, MUTED, align=PP_ALIGN.RIGHT)


def card(slide, l, t, w, h, fill=WHITE, line_color=GREEN):
    c = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    c.adjustments[0] = 0.06
    c.fill.solid()
    c.fill.fore_color.rgb = fill
    c.line.color.rgb = line_color
    c.line.width = Pt(1.0)
    c.shadow.inherit = False
    return c


# ---- Slides ---------------------------------------------------------------

def slide_title(prs, num):
    slide = add_slide(prs)
    # Full-screen green header panel
    panel = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, Inches(3.4))
    panel.fill.solid()
    panel.fill.fore_color.rgb = GREEN_DEEP
    panel.line.fill.background()
    panel.shadow.inherit = False
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(3.4), SW, Inches(0.09))
    strip.fill.solid()
    strip.fill.fore_color.rgb = AMBER
    strip.line.fill.background()
    strip.shadow.inherit = False

    add_text(slide, Inches(0.9), Inches(0.95), Inches(11.5), Inches(1.2),
             "NGO Operations Management Platform", 44, WHITE, bold=True)
    add_text(slide, Inches(0.92), Inches(2.35), Inches(11.5), Inches(0.6),
             "One unified platform for donors, donations, campaigns, volunteers, and events",
             20, SAGE)
    add_text(slide, Inches(0.92), Inches(4.0), Inches(11.5), Inches(1.4),
             "Team Final Submission · Hackathon 2026", 24, INK, bold=True)
    add_text(slide, Inches(0.92), Inches(4.75), Inches(11.5), Inches(0.6),
             "Presentation Round · 16 September 2026", 18, MUTED)
    footer(slide, num)
    return slide


def slide_problem(prs, num):
    slide = add_slide(prs)
    header_band(slide, "The Problem", "Manual, fragmented NGO operations")
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9), [
        "Donor records, campaigns, donations, volunteers, and events live in "
        "separate spreadsheets, emails, and paper files",
        "No single source of truth — reconciling donations and tracking "
        "campaign progress is slow and error-prone",
        "Payments are collected manually and acknowledgements are forgotten",
        "Staff can't see one clear view of fundraising and volunteer operations",
        "Volunteers and donors have no self-service way to manage their participation",
    ], size=22, gap=14)
    footer(slide, num)
    return slide


def slide_solution(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Our Solution", "A unified, role-aware web platform")
    bullets = [
        "Donor & volunteer self-service",
        "Staff workflows for registrations and verification",
        "Live dashboards and reporting",
        "Online payments with an offline fallback",
    ]
    add_bullets(slide, Inches(0.85), Inches(1.6), Inches(11.7), Inches(3.6),
                bullets, size=22, gap=14)
    # Row of three highlight cards
    labels = [("DONATE WITH CONFIDENCE", "Razorpay online payments, verified signatures, safe offline fallback"),
              ("OPERATE WITH CLARITY", "Every donor, campaign, and event tracked in one place"),
              ("ENGAGE WITH EASE", "Self-service portals for donors and volunteers")]
    cw, gap = Inches(3.7), Inches(0.35)
    x0 = Inches(0.85)
    for i, (head, body) in enumerate(labels):
        cx = Emu(int(x0) + i * (int(cw) + int(gap)))
        card(slide, cx, Inches(5.0), cw, Inches(1.9))
        add_text(slide, Emu(int(cx) + Inches(0.25)), Inches(5.15), Inches(3.2),
                 Inches(0.4), head, 15, GREEN, bold=True)
        add_text(slide, Emu(int(cx) + Inches(0.25)), Inches(5.6), Inches(3.2),
                 Inches(1.2), body, 13, MUTED)
    footer(slide, num)
    return slide


def slide_tech(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Technology Stack", "Modern, production-ready tools")
    tech = [
        "Backend · Django 5.2 (Python) with role-based Auth (Admin / Staff / Donor / Volunteer)",
        "Frontend · React 18 + Vite · Chart.js analytics · responsive, mobile-friendly UI",
        "Payments · Razorpay online checkout + signature-verified webhooks, with an offline / cash fallback",
        "Database · Supabase (PostgreSQL) — managed, production databases with SSL",
        "Dev experience · python-dotenv configuration · 29 end-to-end tests across the full stack",
    ]
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9),
                tech, size=20, gap=13, bullet_color=GREEN)
    footer(slide, num)
    return slide


def slide_donations(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Key Feature — Donations & Campaigns",
                "Raise funds online, track everything automatically")
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9), [
        "Online payment through Razorpay with signature-verified reconciliation",
        "Automatic offline / cash fallback when online payment is not configured",
        "Campaign goals with live “raised” amount and progress percentage",
        "Goal cap — the campaign stops accepting donations once the target is reached",
        "Donation lifecycle tracked end-to-end: created → captured / failed / refunded",
        "Monthly donation reports exported to CSV",
    ], size=21, gap=13)
    footer(slide, num)
    return slide


def slide_people(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Key Feature — Donors & Volunteers",
                "Complete profiles with self-service and trust workflows")
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9), [
        "Donor records with type (individual / organisation), tags, and giving history",
        "Self-service profile editing for donors and volunteers",
        "Volunteer profiles with registrations and background-check tracking",
        "Background verification workflow — staff review and approve each volunteer",
        "Donor timeline — every interaction and donation in one view",
    ], size=21, gap=13)
    footer(slide, num)
    return slide


def slide_events(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Key Feature — Events & Staff Workflows",
                "Coordinated volunteering with the right controls")
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9), [
        "Event sign-up with capacity, confirmation, and waitlist handling",
        "Staff accept registrations for upcoming events",
        "Role-scoped dashboards — staff, donors, and volunteers each see what matters",
        "Admin-only guardrails for sensitive operations like donor / volunteer edits",
        "Central users panel for managing access and permissions",
    ], size=21, gap=13)
    footer(slide, num)
    return slide


def slide_impact(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Impact", "Real change for real organisations")
    impact = [
        "One source of truth — no more scattered spreadsheets or duplicated records",
        "Faster, safer donation reconciliation with automatic verification",
        "Increased fundraising — goal caps and live progress encourage momentum",
        "Stronger volunteer trust through transparent background-check workflow",
        "More time for mission — staff stop chasing data and act on it",
    ]
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9),
                impact, size=21, gap=13, bullet_color=GREEN)
    footer(slide, num)
    return slide


def slide_standout(prs, num):
    slide = add_slide(prs)
    header_band(slide, "Why Our Demo Stands Out", "Built like a product, not a prototype")
    add_bullets(slide, Inches(0.85), Inches(1.55), Inches(11.7), Inches(4.9), [
        "Warm, human design system — a visual identity matched to the mission",
        "Dark mode and fully responsive on desktop and mobile",
        "No native browser pop-ups — polished in-app toasts, confirmations, and modals",
        "29 end-to-end tests — the flows we show are the flows that are verified",
        "Real payments wiring — works in Razorpay test mode today",
    ], size=21, gap=13)
    footer(slide, num)
    return slide


def slide_thanks(prs, num):
    slide = add_slide(prs)
    panel = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SW, SH)
    panel.fill.solid()
    panel.fill.fore_color.rgb = GREEN_DEEP
    panel.line.fill.background()
    panel.shadow.inherit = False
    add_text(slide, Inches(1.2), Inches(2.6), Inches(11), Inches(1.3),
             "Thank You!", 54, WHITE, bold=True, align=PP_ALIGN.CENTER)
    add_text(slide, Inches(1.2), Inches(4.1), Inches(11), Inches(0.7),
             "Questions welcome — happy to demo the live platform",
             22, SAGE, align=PP_ALIGN.CENTER)
    footer(slide, num)  # footer text is muted; on dark bg it will sit at bottom
    return slide


def build():
    prs = base_presentation()
    builders = [
        slide_title,     # 1
        slide_problem,   # 2
        slide_solution,  # 3
        slide_tech,      # 4
        slide_donations, # 5
        slide_people,    # 6
        slide_events,    # 7
        slide_impact,    # 8
        slide_standout,  # 9
        slide_thanks,    # 10
    ]
    for i, builder in enumerate(builders, start=1):
        builder(prs, i)
    out = "NGO_Operations_Platform_Presentation.pptx"
    prs.save(out)
    print(f"Saved {out} with {len(builders)} slides")


if __name__ == "__main__":
    build()