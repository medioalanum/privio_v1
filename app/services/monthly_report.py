"""Read-only monthly PDF, generated in memory without retaining reports."""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.i18n import t
from app.models.commitment import Commitment
from app.services.decisions import ZERO, decision_summary

COPY = {
    "pt": {
        "download": "Baixar relatório do mês (PDF)",
        "title": "Suas contas",
        "scope": "Contas com vencimento neste mês. Pendências de outros meses não estão incluídas.",
        "snapshot": "Situação em",
        "pending": "Falta pagar neste mês",
        "paid": "Já pago",
        "total": "Total das contas do mês",
        "due_section": "A pagar",
        "paid_section": "Pagas",
        "bill": "Conta",
        "due": "Vencimento",
        "amount": "Valor a pagar",
        "status": "Situação",
        "paid_on": "Pago em",
        "paid_amount": "Valor pago",
        "overdue": "Vencida",
        "upcoming": "A vencer",
        "today": "Vence hoje",
        "estimated": "Estimado",
        "unknown": "Não informado",
        "incomplete": "Total incompleto",
        "legacy": "Há contas marcadas como pagas sem valor ou data de pagamento registrados. Os totais pagos e do mês estão incompletos.",
        "known": "Pagamentos com valor informado",
        "late": "Do valor pendente, {amount} estão vencidos.",
        "empty": "Nenhuma conta registrada para este mês.",
        "all_paid": "Todas as contas deste mês estão marcadas como pagas.",
        "none_paid": "Nenhum pagamento registrado para as contas deste mês.",
        "footer": "Retrato dos registros na exportação. Alterações posteriores não estão incluídas.",
        "page": "Página",
        "estimate_note": "Valores estimados estão identificados e podem mudar.",
    },
    "en": {
        "download": "Download monthly report (PDF)",
        "title": "Your bills",
        "scope": "Bills due this month. Outstanding bills from other months are not included.",
        "snapshot": "Status as of",
        "pending": "Left to pay this month",
        "paid": "Already paid",
        "total": "Total for this month's bills",
        "due_section": "To pay",
        "paid_section": "Paid",
        "bill": "Bill",
        "due": "Due date",
        "amount": "Amount due",
        "status": "Status",
        "paid_on": "Paid on",
        "paid_amount": "Amount paid",
        "overdue": "Overdue",
        "upcoming": "Upcoming",
        "today": "Due today",
        "estimated": "Estimated",
        "unknown": "Not recorded",
        "incomplete": "Incomplete total",
        "legacy": "Some bills are marked paid without a recorded payment amount or date. Paid and monthly totals are incomplete.",
        "known": "Payments with recorded amounts",
        "late": "Of the outstanding amount, {amount} is overdue.",
        "empty": "No bills recorded for this month.",
        "all_paid": "All bills for this month are marked paid.",
        "none_paid": "No payments recorded for this month's bills.",
        "footer": "Snapshot at export time. Later changes are not included.",
        "page": "Page",
        "estimate_note": "Estimated amounts are identified and may change.",
    },
    "it": {
        "download": "Scarica il resoconto mensile (PDF)",
        "title": "Le tue scadenze",
        "scope": "Spese in scadenza questo mese. Gli arretrati di altri mesi non sono inclusi.",
        "snapshot": "Situazione al",
        "pending": "Da pagare questo mese",
        "paid": "Già pagato",
        "total": "Totale delle spese del mese",
        "due_section": "Da pagare",
        "paid_section": "Pagate",
        "bill": "Spesa",
        "due": "Scadenza",
        "amount": "Da pagare",
        "status": "Stato",
        "paid_on": "Pagato il",
        "paid_amount": "Importo pagato",
        "overdue": "Scaduta",
        "upcoming": "In scadenza",
        "today": "Scade oggi",
        "estimated": "Stimato",
        "unknown": "Non registrato",
        "incomplete": "Totale incompleto",
        "legacy": "Alcune spese risultano pagate senza importo o data registrati. I totali pagati e del mese sono incompleti.",
        "known": "Pagamenti con importo registrato",
        "late": "Dell'importo da pagare, {amount} sono scaduti.",
        "empty": "Nessuna spesa registrata per questo mese.",
        "all_paid": "Tutte le spese di questo mese risultano pagate.",
        "none_paid": "Nessun pagamento registrato per le spese di questo mese.",
        "footer": "Situazione al momento dell'esportazione. Le modifiche successive non sono incluse.",
        "page": "Pagina",
        "estimate_note": "Gli importi stimati sono indicati e possono cambiare.",
    },
}


def monthly_data(db: Session, month: date, today: date) -> dict:
    # Must be the first statement: keep all SELECTs on one consistent snapshot.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    commitments = db.scalars(select(Commitment).order_by(Commitment.id)).all()
    rows = decision_summary(db, commitments, month, today)["rows"]
    pending = [r for r in rows if r["status"] != "paid"]
    paid = [r for r in rows if r["status"] == "paid"]
    incomplete = any(r["payment"] is None for r in paid)
    known_paid = sum(
        (r["payment"].paid_amount for r in paid if r["payment"] is not None), ZERO
    )
    due = sum((r["pending"] for r in pending), ZERO)
    return {
        "rows": rows,
        "pending": pending,
        "paid": paid,
        "incomplete": incomplete,
        "known_paid": known_paid,
        "due": due,
        "total": None if incomplete else due + known_paid,
        "overdue": sum(
            (r["pending"] for r in pending if r["status"] == "overdue"), ZERO
        ),
    }


def render_monthly_pdf(data: dict, month: date, exported: datetime, lang: str) -> bytes:
    copy = COPY[lang]

    def money(value: Decimal) -> str:
        result = f"{value:,.2f}"
        if lang != "en":
            result = result.translate(str.maketrans({",": ".", ".": ","}))
        return f"€ {result}"

    ink = colors.HexColor("#18352F")
    muted = colors.HexColor("#50615D")
    body = ParagraphStyle(
        "body",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=ink,
        spaceAfter=7,
    )
    small = ParagraphStyle(
        "small", parent=body, fontSize=8, leading=11, textColor=muted
    )
    heading = ParagraphStyle(
        "heading",
        parent=body,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=19,
        spaceBefore=17,
        spaceAfter=10,
        keepWithNext=True,
    )
    title = ParagraphStyle(
        "title", parent=heading, fontSize=24, leading=29, spaceBefore=0
    )

    def p(value: object, style=body):
        return Paragraph(escape(str(value)), style)

    month_label = f"{t('month_' + str(month.month), lang)} {month.year}"
    stamp = exported.strftime("%d/%m/%Y %H:%M:%S %Z")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=42,
        bottomMargin=60,
        title=f"Privio - {month_label}",
        author="Privio",
    )
    story = [
        p("PRIVIO", small),
        p(f"{copy['title']} - {month_label}", title),
        p(f"{copy['snapshot']} {stamp}"),
        p(copy["scope"], small),
        Spacer(1, 10),
    ]
    metrics = [
        (copy["pending"], money(data["due"])),
        (
            copy["paid"],
            copy["incomplete"] if data["incomplete"] else money(data["known_paid"]),
        ),
        (
            copy["total"],
            copy["incomplete"] if data["total"] is None else money(data["total"]),
        ),
    ]
    metric = Table(
        [[p(label, small) for label, _ in metrics], [p(value) for _, value in metrics]],
        colWidths=[doc.width / 3] * 3,
    )
    metric.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF4F1")),
                ("BOX", (0, 0), (0, -1), 1, ink),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story += [metric, Spacer(1, 10)]
    if data["incomplete"]:
        story += [
            p(copy["legacy"], small),
            p(f"{copy['known']}: {money(data['known_paid'])}", small),
        ]
    if data["overdue"]:
        story.append(p(copy["late"].format(amount=money(data["overdue"]))))
    if any(r["nature"] == "estimated" for r in data["pending"]):
        story.append(p(copy["estimate_note"], small))
    if not data["rows"]:
        story.append(p(copy["empty"], heading))
    else:
        for paid, section in [(False, "due_section"), (True, "paid_section")]:
            story.append(p(copy[section], heading))
            rows = data["paid" if paid else "pending"]
            if not rows:
                story.append(p(copy["none_paid" if paid else "all_paid"]))
                continue
            headers = (
                ["bill", "due", "paid_on", "paid_amount"]
                if paid
                else ["bill", "due", "amount", "status"]
            )
            cells = [[p(copy[k], small) for k in headers]]
            for row in rows:
                item, payment = row["item"], row["payment"]
                name = item.description
                if not paid and row["nature"] == "estimated":
                    name += f" ({copy['estimated']})"
                values = [name, item.occurrence_date.strftime("%d/%m/%Y")]
                if paid:
                    values += [
                        payment.payment_date.strftime("%d/%m/%Y")
                        if payment
                        else copy["unknown"],
                        money(payment.paid_amount) if payment else copy["unknown"],
                    ]
                else:
                    state = (
                        "overdue"
                        if row["status"] == "overdue"
                        else "today"
                        if item.occurrence_date == exported.date()
                        else "upcoming"
                    )
                    values += [money(row["pending"]), copy[state]]
                cells.append([p(value) for value in values])
            table = Table(
                cells,
                colWidths=[doc.width - 270, 90, 90, 90],
                repeatRows=1,
                hAlign="LEFT",
            )
            table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF4F1")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.7, ink),
                        (
                            "LINEBELOW",
                            (0, 1),
                            (-1, -1),
                            0.3,
                            colors.HexColor("#DDE5E1"),
                        ),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(table)

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 35, copy["footer"])
        canvas.drawString(40, 23, f"Privio | {month_label} | {stamp}")
        canvas.drawRightString(A4[0] - 40, 23, f"{copy['page']} {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
