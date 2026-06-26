"""Reproducibly generate synthetic, German test PDFs under tests/fixtures/.

These fixtures back the offline test suite (no real PDFs, no customer data).
Run it with:

    uv run python scripts/make_fixtures.py

It produces three kinds of fixtures (see FIXTURES below for the per-file
intent):

* five correct invoices/quotes with a real text layer (letterhead, document
  number, date, line items, net/VAT/gross — one with an IBAN),
* one deliberately unclear invoice whose printed totals don't add up
  (net + VAT != gross) so it must trigger needs_review downstream,
* one "scanned" PDF that is a pure image without any text layer, so it must
  be rejected with NoTextLayerError.

reportlab draws the text-layer PDFs; the scanned one renders its text into a
Pillow image first (both ship with the dev dependencies).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

VAT_RATE = Decimal("0.20")  # Austrian standard VAT rate (20 %).


@dataclass
class Position:
    """One line item on the document."""

    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _money(self.quantity * self.unit_price)


@dataclass
class Document:
    """Structured content for one synthetic invoice/quote."""

    filename: str
    doc_type: str  # "Rechnung" or "Angebot"
    vendor_name: str
    vendor_address: str
    document_number: str
    document_date: str
    positions: list[Position]
    due_date: str | None = None
    iban: str | None = None
    # If set, these override the computed totals (used to fake an
    # implausible document where net + VAT != gross).
    override_totals: dict[str, Decimal] = field(default_factory=dict)

    @property
    def net_total(self) -> Decimal:
        if "net" in self.override_totals:
            return self.override_totals["net"]
        return _money(sum((p.line_total for p in self.positions), Decimal("0")))

    @property
    def vat_total(self) -> Decimal:
        if "vat" in self.override_totals:
            return self.override_totals["vat"]
        return _money(self.net_total * VAT_RATE)

    @property
    def gross_total(self) -> Decimal:
        if "gross" in self.override_totals:
            return self.override_totals["gross"]
        return _money(self.net_total + self.vat_total)


def _money(value: Decimal) -> Decimal:
    """Round to two decimals, Austrian-style commercial rounding."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _eur(value: Decimal) -> str:
    """Format a Decimal as an Austrian euro string, e.g. '1.234,56 €'."""
    sign = "-" if value < 0 else ""
    whole, frac = f"{abs(value):.2f}".split(".")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return f"{sign}{'.'.join(groups)},{frac} €"


# --- The fixture set -------------------------------------------------------

DOCUMENTS: list[Document] = [
    Document(
        filename="rechnung_01_buerobedarf.pdf",
        doc_type="Rechnung",
        vendor_name="Bürowelt Handels GmbH",
        vendor_address="Hauptstraße 12, 4020 Linz",
        document_number="RE-2026-0042",
        document_date="03.06.2026",
        due_date="17.06.2026",
        iban="AT61 1904 3002 3457 3201",
        positions=[
            Position("Druckerpapier A4, 80g (Karton)", Decimal("5"), Decimal("24.90")),
            Position("Kugelschreiber blau (50er-Pack)", Decimal("2"), Decimal("12.50")),
            Position("Aktenordner breit", Decimal("10"), Decimal("3.20")),
        ],
    ),
    Document(
        filename="rechnung_02_it_dienstleistung.pdf",
        doc_type="Rechnung",
        vendor_name="NetzWerk IT-Services e.U.",
        vendor_address="Technologiepark 5, 8010 Graz",
        document_number="2026-114",
        document_date="11.06.2026",
        due_date="25.06.2026",
        positions=[
            Position("Serverwartung (Pauschale)", Decimal("1"), Decimal("450.00")),
            Position("Support-Stunden", Decimal("6"), Decimal("95.00")),
        ],
    ),
    Document(
        filename="rechnung_03_handwerk.pdf",
        doc_type="Rechnung",
        vendor_name="Tischlerei Moser",
        vendor_address="Dorfstraße 8, 5020 Salzburg",
        document_number="R2026/87",
        document_date="20.05.2026",
        due_date="03.06.2026",
        positions=[
            Position("Massivholz-Regal nach Maß", Decimal("1"), Decimal("780.00")),
            Position("Montage vor Ort (Stunden)", Decimal("3"), Decimal("65.00")),
        ],
    ),
    Document(
        filename="angebot_01_webdesign.pdf",
        doc_type="Angebot",
        vendor_name="Pixelschmiede Werbeagentur",
        vendor_address="Mariahilfer Straße 101, 1060 Wien",
        document_number="AN-2026-018",
        document_date="09.06.2026",
        positions=[
            Position("Webdesign Startseite", Decimal("1"), Decimal("1200.00")),
            Position("Unterseiten", Decimal("4"), Decimal("350.00")),
            Position("Einrichtung CMS", Decimal("1"), Decimal("600.00")),
        ],
    ),
    Document(
        filename="angebot_02_beratung.pdf",
        doc_type="Angebot",
        vendor_name="Consult & Co Unternehmensberatung",
        vendor_address="Bahnhofplatz 3, 6020 Innsbruck",
        document_number="ANG-2026-205",
        document_date="14.06.2026",
        positions=[
            Position("Strategieworkshop (Tag)", Decimal("2"), Decimal("1400.00")),
            Position("Dokumentation & Auswertung", Decimal("1"), Decimal("800.00")),
        ],
    ),
]

# Deliberately unclear: printed totals are inconsistent (net + VAT != gross),
# which must make validate() flag needs_review for the plausibility breach.
UNCLEAR_DOCUMENT = Document(
    filename="unklar_summen.pdf",
    doc_type="Rechnung",
    vendor_name="Diffus Dienstleistungen GmbH",
    vendor_address="Industriestraße 22, 9020 Klagenfurt",
    document_number="RE-2026-0099",
    document_date="18.06.2026",
    due_date="02.07.2026",
    positions=[
        Position("Projektarbeit (Pauschale)", Decimal("1"), Decimal("500.00")),
        Position("Zusatzleistung", Decimal("1"), Decimal("100.00")),
    ],
    # net would be 600,00 / VAT 120,00 / gross 720,00 — but we print a wrong
    # gross so the document contradicts itself.
    override_totals={"gross": Decimal("700.00")},
)

# What each fixture is meant to exercise (for documentation / the README).
FIXTURES = {
    "rechnung_01_buerobedarf.pdf": "Korrekte Rechnung mit IBAN, mehrere Positionen.",
    "rechnung_02_it_dienstleistung.pdf": "Korrekte Rechnung, Dienstleistung, ohne IBAN.",
    "rechnung_03_handwerk.pdf": "Korrekte Rechnung, Handwerk, mit Zahlungsziel.",
    "angebot_01_webdesign.pdf": "Korrektes Angebot (kein Zahlungsziel).",
    "angebot_02_beratung.pdf": "Korrektes Angebot, Beratungsleistung.",
    "unklar_summen.pdf": "Unplausibel: Netto + USt != Brutto -> needs_review.",
    "gescannt_ohne_textebene.pdf": "Reines Bild ohne Textebene -> NoTextLayerError.",
}


# --- PDF rendering ---------------------------------------------------------

def build_document_pdf(doc: Document, out_path: Path) -> None:
    """Draw a single invoice/quote as a text-layer PDF via reportlab."""
    width, height = A4
    c = canvas.Canvas(str(out_path), pagesize=A4)
    left = 50
    y = height - 60

    # Letterhead.
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, doc.vendor_name)
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(left, y, doc.vendor_address)

    # Document title.
    y -= 40
    c.setFont("Helvetica-Bold", 20)
    c.drawString(left, y, doc.doc_type)

    # Meta block (number / dates), right-aligned.
    c.setFont("Helvetica", 10)
    meta_y = y
    c.drawRightString(width - left, meta_y, f"Belegnummer: {doc.document_number}")
    meta_y -= 14
    c.drawRightString(width - left, meta_y, f"Datum: {doc.document_date}")
    if doc.due_date:
        meta_y -= 14
        c.drawRightString(width - left, meta_y, f"Zahlungsziel: {doc.due_date}")

    # Positions table header.
    y -= 50
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Position")
    c.drawRightString(left + 300, y, "Menge")
    c.drawRightString(left + 400, y, "Einzelpreis")
    c.drawRightString(width - left, y, "Summe")
    y -= 6
    c.line(left, y, width - left, y)

    # Position rows.
    c.setFont("Helvetica", 10)
    for pos in doc.positions:
        y -= 18
        c.drawString(left, y, pos.description)
        c.drawRightString(left + 300, y, _qty(pos.quantity))
        c.drawRightString(left + 400, y, _eur(pos.unit_price))
        c.drawRightString(width - left, y, _eur(pos.line_total))

    # Totals.
    y -= 12
    c.line(left + 300, y, width - left, y)
    c.setFont("Helvetica", 10)
    for label, value in (
        ("Nettobetrag", doc.net_total),
        ("USt 20%", doc.vat_total),
    ):
        y -= 18
        c.drawRightString(left + 400, y, f"{label}:")
        c.drawRightString(width - left, y, _eur(value))
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(left + 400, y, "Bruttobetrag:")
    c.drawRightString(width - left, y, _eur(doc.gross_total))

    # IBAN footer.
    if doc.iban:
        y -= 50
        c.setFont("Helvetica", 10)
        c.drawString(left, y, f"Zahlbar auf IBAN: {doc.iban}")

    c.showPage()
    c.save()


def _qty(value: Decimal) -> str:
    """Render a quantity without trailing zeros (e.g. '5' not '5.00')."""
    return f"{value.normalize():f}"


def build_scanned_pdf(out_path: Path) -> None:
    """Render text into a raster image and embed it — no text layer at all."""
    # White page with black "typed" text, rendered as pixels only.
    img = Image.new("RGB", (1240, 1754), "white")  # ~150 dpi A4
    draw = ImageDraw.Draw(img)
    lines = [
        "Rechnung",
        "",
        "Scan & Druck Kopierservice",
        "Belegnummer: RE-2026-0001",
        "Datum: 05.06.2026",
        "",
        "Position: Kopien s/w (500 Stueck)",
        "Nettobetrag: 45,00 EUR",
        "USt 20%: 9,00 EUR",
        "Bruttobetrag: 54,00 EUR",
        "",
        "(Dieses PDF ist ein reines Bild ohne Textebene.)",
    ]
    x, y = 80, 80
    for line in lines:
        draw.text((x, y), line, fill="black")
        y += 50

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    c.drawImage(ImageReader(img), 0, 0, width=width, height=height)
    c.showPage()
    c.save()


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    for doc in DOCUMENTS:
        build_document_pdf(doc, FIXTURES_DIR / doc.filename)
        print(f"  erzeugt: {doc.filename}")

    build_document_pdf(UNCLEAR_DOCUMENT, FIXTURES_DIR / UNCLEAR_DOCUMENT.filename)
    print(f"  erzeugt: {UNCLEAR_DOCUMENT.filename}")

    build_scanned_pdf(FIXTURES_DIR / "gescannt_ohne_textebene.pdf")
    print("  erzeugt: gescannt_ohne_textebene.pdf")

    print(f"\nFertig. {len(FIXTURES)} Fixtures unter {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
