import os
from typing import TypedDict, List, Optional
from escpos.printer import Usb
from datetime import datetime

PRINT_WIDTH_DOTS = 384
MAX_LABEL_WIDTH = 20

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

def print_label_amount(p: Usb, label: str, amount: str) -> None:
    if len(label) <= MAX_LABEL_WIDTH:
        p.set(align="left")
        p.text(f"{label:<{MAX_LABEL_WIDTH}}")
        p.set(align="right")
        p.text(f"{amount}\n")
    else:
        words = label.split()
        first_line = ""
        second_line = ""
        
        for word in words:
            if len(first_line + " " + word) <= MAX_LABEL_WIDTH:
                first_line = first_line + " " + word if first_line else word
            else:
                second_line = second_line + " " + word if second_line else word
        
        p.set(align="left")
        p.text(f"{first_line:<{MAX_LABEL_WIDTH}}")
        p.set(align="right")
        p.text(f"{amount}\n")
        if second_line:
            p.set(align="left")
            p.text(f"{second_line}\n")

def pos_print(data: Invoice) -> None:
    vendor_id = int(os.getenv("PRINTER_VENDOR_ID", "0x28E9"), 16)
    product_id = int(os.getenv("PRINTER_PRODUCT_ID", "0x0289"), 16)
    p = Usb(vendor_id, product_id)
    
    p.set(align="center", font="a", width=1, height=1, bold=True)
    school_name = os.getenv("SCHOOL_NAME", "Institution Marthe Hervée")
    p.text(f"{school_name}\n")
    
    p.set(align="center", font="a", width=1, height=1)
    school_address = os.getenv("SCHOOL_ADDRESS", "Ankasina, Boulevard de l'europe, Lalana Pastora Rahajason, Antananarivo")
    p.text(f"{school_address}\n")
    
    school_phone = os.getenv("SCHOOL_PHONE", "+261 034 08 040 83")
    school_email = os.getenv("SCHOOL_EMAIL", "imh@gmail.com")
    p.text(f"{school_phone} • {school_email}\n")
    
    p.text("-" * 32 + "\n")
    
    p.set(align="left", font="a", width=1, height=1)
    p.text(f"Client: {data['clientName']}\n")
    if data['clientContact'] and data['clientContact'] != "--":
        p.text(f"Contact: {data['clientContact']}\n")
    
    p.text(f"Date facture: {format_date(data['creationDate'])}\n")
    p.text("-" * 32 + "\n")
    
    total = 0.0
    for element in data['elements']:
        desc = element['description']
        amount = element['amount']
        total += amount
        print_label_amount(p, desc, format_currency(amount))
    
    p.text("-" * 32 + "\n")
    p.set(align="left", font="a", width=1, height=1, bold=True)
    p.text("TOTAL")
    p.set(align="right", font="a", width=2, height=2, bold=True)
    p.text(f"{format_currency(total)}\n")
    p.set(align="left", font="a", width=1, height=1)
    p.text("-" * 32 + "\n")
    
    if data['payments']:
        for payment in data['payments']:
            payment_label = f"Paiement {format_date(payment['paymentDateTime'])}"
            print_label_amount(p, payment_label, format_currency(payment['amount']))
    
    p.text("-" * 32 + "\n")
    p.set(align="left", font="a", width=1, height=1)
    print_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    p.text(f"Imprimé le: {print_date}\n")
    
    p.text("\n" * 2)
    p.cut()

