import os
from typing import TypedDict, List, Optional
from escpos.printer import Usb
from PIL import Image
from datetime import datetime

PRINT_WIDTH_DOTS = 384

class InvoiceElement(TypedDict):
    id: int
    description: str
    amount: float
    unitPrice: Optional[float]
    quantity: Optional[float]
    value: float

class Payment(TypedDict):
    id: int
    amount: float
    paymentDateTime: str
    reference: str
    account: str
    methodPaymentId: int
    value: float

class Invoice(TypedDict):
    id: int
    invoiceNumber: str
    clientName: str
    clientContact: str
    invoicePaymentState: str
    creationDate: str
    dueDate: Optional[str]
    paidDate: str
    elements: List[InvoiceElement]
    payments: List[Payment]

def format_date(date_str: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str.replace("+00:00", ""))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return date_str

def format_currency(amount: float) -> str:
    return f"{amount:,.0f} Ar"

def print_image(p: Usb, path: str) -> None:
    img = Image.open(path)
    img = img.resize(
        (PRINT_WIDTH_DOTS, int(img.height * (PRINT_WIDTH_DOTS / img.width)))
    )
    p.image(img)

def pos_print(data: Invoice) -> None:
    vendor_id = int(os.getenv("PRINTER_VENDOR_ID", "0x28E9"), 16)
    product_id = int(os.getenv("PRINTER_PRODUCT_ID", "0x0289"), 16)
    p = Usb(vendor_id, product_id)
    
    p.set(align="center", font="a", width=1, height=1)
    print_image(p, "logo.png")
    p.text("\n")
    
    p.set(align="center", font="a", width=2, height=2, bold=True)
    p.text("FACTURE\n")
    p.set(align="center", font="a", width=1, height=1)
    p.text("-" * 32 + "\n")
    
    p.set(align="left", font="a", width=1, height=1)
    p.text(f"N°: {data['invoiceNumber']}\n")
    p.text(f"Date: {format_date(data['creationDate'])}\n")
    p.text("-" * 32 + "\n")
    
    p.set(align="left", font="a", width=1, height=1, bold=True)
    p.text("CLIENT\n")
    p.set(align="left", font="a", width=1, height=1)
    client_name = data['clientName'][:30] if len(data['clientName']) > 30 else data['clientName']
    p.text(f"{client_name}\n")
    if data['clientContact'] and data['clientContact'] != "--":
        p.text(f"Contact: {data['clientContact']}\n")
    p.text("-" * 32 + "\n")
    
    p.set(align="left", font="a", width=1, height=1, bold=True)
    p.text("DÉTAILS\n")
    p.set(align="left", font="a", width=1, height=1)
    
    total = 0.0
    for element in data['elements']:
        desc = element['description'][:25] if len(element['description']) > 25 else element['description']
        amount = element['amount']
        total += amount
        p.text(f"{desc}\n")
        p.set(align="right")
        p.text(f"{format_currency(amount)}\n")
        p.set(align="left")
        p.text("\n")
    
    p.text("-" * 32 + "\n")
    p.set(align="left", font="a", width=1, height=1, bold=True)
    p.text("TOTAL\n")
    p.set(align="right", font="a", width=2, height=2, bold=True)
    p.text(f"{format_currency(total)}\n")
    p.set(align="left", font="a", width=1, height=1)
    p.text("-" * 32 + "\n")
    
    p.set(align="left", font="a", width=1, height=1, bold=True)
    p.text("PAIEMENT\n")
    p.set(align="left", font="a", width=1, height=1)
    p.text(f"Statut: {data['invoicePaymentState']}\n")
    
    if data['payments']:
        for payment in data['payments']:
            p.text(f"Montant: {format_currency(payment['amount'])}\n")
            p.text(f"Date: {format_date(payment['paymentDateTime'])}\n")
    
    if data['paidDate']:
        p.text(f"Payé le: {format_date(data['paidDate'])}\n")
    
    p.text("\n" * 2)
    p.set(align="center", font="a", width=1, height=1)
    p.text("Merci de votre confiance!\n")
    p.text("\n" * 2)
    
    p.cut()

