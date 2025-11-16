import os
from typing import TypedDict, List, Optional
from escpos.printer import Usb
from datetime import datetime

PRINT_WIDTH_DOTS = 384
MAX_LINE_WIDTH = 32

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
    return f"{int(amount):,}".replace(",", " ")

def translate_payment_method(method_id: int) -> str:
    methods = {
        1: "Especes",
        2: "MVola",
        3: "Airtel Money",
        4: "Orange Money"
    }
    return methods.get(method_id, f"Methode {method_id}")

def wrap_text(text: str, max_width: int) -> List[str]:
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= max_width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [""]

def format_label_value(label: str, value: str) -> str:
    label_width = 14
    dots_needed = label_width - len(label) - 1
    label_part = f"{label}{'.' * dots_needed}: "
    remaining_width = MAX_LINE_WIDTH - len(label_part)
    
    if len(value) <= remaining_width:
        return f"{label_part}{value}"
    else:
        value_lines = wrap_text(value, remaining_width)
        result = f"{label_part}{value_lines[0]}\n"
        indent = " " * len(label_part)
        for line in value_lines[1:]:
            result += f"{indent}{line}\n"
        return result.rstrip()

def format_designation_amount(designation: str, amount: str) -> str:
    amount_width = len(amount)
    designation_width = MAX_LINE_WIDTH - amount_width - 1
    
    designation_lines = wrap_text(designation, designation_width)
    
    if len(designation_lines) == 1:
        return f"{designation_lines[0]:<{designation_width}} {amount}"
    else:
        result = f"{designation_lines[0]:<{designation_width}} {amount}\n"
        for line in designation_lines[1:]:
            result += f"{line}\n"
        return result.rstrip()

def generate_invoice_string(data: Invoice) -> str:
    school_name = os.getenv("SCHOOL_NAME", "INSTITUTION MARTHE HERVEE")
    school_address = os.getenv("SCHOOL_ADDRESS", "Ankasina, Bd de l'Europe, L. P. Rahajason, Antananarivo, Madagascar")
    school_phone = os.getenv("SCHOOL_PHONE", "+261 034 08 040 83")
    school_email = os.getenv("SCHOOL_EMAIL", "imh@gmail.com")
    
    lines = []
    
    lines.append(school_name.upper())
    lines.append("-" * MAX_LINE_WIDTH)
    
    address_lines = wrap_text(school_address, MAX_LINE_WIDTH)
    lines.extend(address_lines)
    
    lines.append("-" * MAX_LINE_WIDTH)
    lines.append(school_phone)
    lines.append(school_email)
    lines.append("-" * MAX_LINE_WIDTH)
    
    invoice_status = "PAYEE" if data['invoicePaymentState'] == "PAID" else data['invoicePaymentState']
    lines.append(format_label_value("FACTURE", data['invoiceNumber']))
    lines.append(format_label_value("STATUT", invoice_status))
    
    client_label = "CLIENT"
    client_dots = "." * (14 - len(client_label) - 1)
    client_label_part = f"{client_label}{client_dots}: "
    client_remaining_width = MAX_LINE_WIDTH - len(client_label_part)
    client_lines = wrap_text(data['clientName'], client_remaining_width)
    lines.append(f"{client_label_part}{client_lines[0]}")
    for line in client_lines[1:]:
        lines.append(" " * len(client_label_part) + line)
    
    contact_value = data['clientContact'] if data['clientContact'] and data['clientContact'] != "--" else "--"
    lines.append(format_label_value("CONTACT", contact_value))
    lines.append(format_label_value("CREE LE", format_date(data['creationDate'])))
    
    if data['paidDate']:
        lines.append(format_label_value("PAYEE LE", format_date(data['paidDate'])))
    
    lines.append("-" * MAX_LINE_WIDTH)
    designation_header_width = 24
    lines.append(f"{'DESIGNATION':<{designation_header_width}}MONTANT")
    lines.append("-" * MAX_LINE_WIDTH)
    
    total = 0.0
    for element in data['elements']:
        desc = element['description']
        amount = element['amount']
        total += amount
        lines.append(format_designation_amount(desc, format_currency(amount)))
    
    lines.append("-" * MAX_LINE_WIDTH)
    total_str = format_currency(total)
    total_width = len(total_str)
    designation_width = MAX_LINE_WIDTH - total_width - 1
    lines.append(f"{'TOTAL':<{designation_width}} {total_str}")
    lines.append("-" * MAX_LINE_WIDTH)
    
    if data['payments']:
        lines.append("REGLEMENTS")
        for payment in data['payments']:
            payment_date = format_date(payment['paymentDateTime'])
            payment_amount = format_currency(payment['amount'])
            amount_width = len(payment_amount)
            date_width = MAX_LINE_WIDTH - amount_width - 1
            lines.append(f"{payment_date:<{date_width}} {payment_amount}")
            
            method = translate_payment_method(payment['methodPaymentId'])
            lines.append(format_label_value("METHODE", method))
            
            if payment['methodPaymentId'] != 1:
                ref_value = payment['reference'] if payment['reference'] else "-"
                account_value = payment['account'] if payment['account'] else "-"
                lines.append(format_label_value("Ref", ref_value))
                lines.append(format_label_value("Compte", account_value))
    
    lines.append("-" * MAX_LINE_WIDTH)
    print_date = datetime.now().strftime("%d/%m/%Y %H:%M")
    lines.append(f"Imprime le : {print_date}")
    lines.append("Merci pour votre confiance.")
    
    return "\n".join(lines) + "\n"

def pos_print(data: Invoice) -> None:
    vendor_id = int(os.getenv("PRINTER_VENDOR_ID", "0x28E9"), 16)
    product_id = int(os.getenv("PRINTER_PRODUCT_ID", "0x0289"), 16)
    p = Usb(vendor_id, product_id)
    
    invoice_string = generate_invoice_string(data)
    p.text(invoice_string)
    p.cut()

