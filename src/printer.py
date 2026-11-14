from contextlib import closing
from typing import Any, Dict, TypedDict, List, Optional, Union
from escpos.printer import Usb
from escpos.exceptions import USBNotFoundError
from datetime import datetime

import config

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
    paymentDateTime: Union[str, int, float]
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
    creationDate: Union[str, int, float]
    dueDate: Optional[Union[str, int, float]]
    paidDate: Union[str, int, float]
    elements: List[InvoiceElement]
    payments: List[Payment]

def format_date(date_value: Union[str, int, float]) -> str:
    try:
        if isinstance(date_value, (int, float)):
            dt = datetime.fromtimestamp(date_value / 1000.0)
            return dt.strftime("%d/%m/%Y %H:%M")
        else:
            dt = datetime.fromisoformat(date_value.replace("+00:00", ""))
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(date_value)

def format_currency(amount: float) -> str:
    value = int(amount)
    if abs(value) <= 999_999:
        return f"{value:,}".replace(",", " ")
    # Millions keep every significant digit (1 234 500 -> 1,2345M) so the
    # abbreviation never changes the amount that was actually paid.
    millions, remainder = divmod(abs(value), 1_000_000)
    decimals = f"{remainder:06d}".rstrip("0")
    sign = "-" if value < 0 else ""
    whole = f"{millions:,}".replace(",", " ")
    return f"{sign}{whole}{',' + decimals if decimals else ''}M"

def translate_payment_method(method_id: int) -> str:
    methods = {
        1: "Especes",
        2: "MVola",
        3: "Airtel Money",
        4: "Orange Money"
    }
    return methods.get(method_id, f"Methode {method_id}")

def payment_methods(data: Invoice) -> str:
    """How the client paid: each method once, in payment order; "--" if
    the invoice carries no payment."""
    names: List[str] = []
    for payment in data.get('payments') or []:
        name = translate_payment_method(payment['methodPaymentId'])
        if name not in names:
            names.append(name)
    return ", ".join(names) if names else "--"

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
    label_width = 10
    value_width = MAX_LINE_WIDTH - label_width
    dots_needed = max(0, label_width - len(label) - 2)
    label_part = f"{label}{'.' * dots_needed}: "
    
    if len(value) <= value_width:
        return f"{label_part}{value}"
    else:
        value_lines = wrap_text(value, value_width)
        result = f"{label_part}{value_lines[0]}\n"
        for line in value_lines[1:]:
            result += f"{line}\n"
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

def generate_invoice_string(
    data: Invoice,
    settings: Optional[Dict[str, Any]] = None,
    printed_at: Optional[datetime] = None,
) -> str:
    if settings is None:
        settings = config.load()
    lines = []

    # Header: name, then address, phone and email, each only if filled in.
    lines.append(settings["schoolName"].upper())
    if settings["schoolAddress"]:
        lines.extend(wrap_text(settings["schoolAddress"], MAX_LINE_WIDTH))
    if settings["schoolPhone"]:
        lines.append(settings["schoolPhone"])
    if settings["schoolEmail"]:
        lines.append(settings["schoolEmail"])
    lines.append("-" * MAX_LINE_WIDTH)
    
    lines.append(format_label_value("FACTURE", data['invoiceNumber']))
    
    client_line = format_label_value("CLIENT", data['clientName'])
    lines.append(client_line)
    
    if data['paidDate']:
        date_line = format_label_value("PAYEE LE", format_date(data['paidDate']))
        lines.append(date_line)

    lines.append(format_label_value("PAYE PAR", payment_methods(data)))
    
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
    
    printed_at = printed_at or datetime.now()
    lines.append(f"Imprime le: {printed_at.strftime('%d/%m/%Y %H:%M')}")
    lines.append(settings["invoiceFooter"])
    
    while lines and not lines[-1].strip():
        lines.pop()
    
    result = "\n".join(lines)
    return result.rstrip()

def get_usb_backend() -> Optional[Any]:
    """libusb backend from the DLL shipped inside the app.

    Bundling libusb means the host does not need one installed. Returns None
    if it cannot be loaded, which makes pyusb search the system instead.
    """
    try:
        import libusb_package
        return libusb_package.get_libusb1_backend()
    except Exception:
        return None

def usb_backend_name() -> Optional[str]:
    """Backend pyusb would use, or None if no libusb is reachable at all."""
    backend = get_usb_backend()
    if backend is None:
        try:
            from usb.backend import libusb1, libusb0, openusb
            for module in (libusb1, libusb0, openusb):
                backend = module.get_backend()
                if backend is not None:
                    break
        except Exception:
            return None
    return type(backend).__module__ if backend is not None else None

def open_printer(vendor_id: int, product_id: int) -> Usb:
    """Open the printer, preferring the bundled libusb over any system copy.

    A device bound to the libusb-win32 driver may only be visible to the
    system libusb, so fall back to pyusb's own search before giving up.
    """
    backend = get_usb_backend()
    if backend is not None:
        try:
            return Usb(vendor_id, product_id, usb_args={"backend": backend})
        except USBNotFoundError:
            pass
    return Usb(vendor_id, product_id)

def printer_connected(vendor_id: int, product_id: int) -> Optional[bool]:
    """Whether the printer is visible over USB, without opening it.

    Looks through the same backends as open_printer. None means no libusb
    could be loaded, so nothing can be said.
    """
    import usb.core

    searched = False
    for backend in (get_usb_backend(), None):
        arguments: Dict[str, Any] = {"idVendor": vendor_id, "idProduct": product_id}
        if backend is not None:
            arguments["backend"] = backend
        try:
            if usb.core.find(**arguments) is not None:
                return True
            searched = True
        except Exception:
            # No usable backend this way; the other one may still work.
            continue
    return False if searched else None

def pos_print(data: Invoice) -> None:
    # Read on every print, so saved settings apply without a restart.
    settings = config.load()
    vendor_id = config.parse_usb_id(settings["printerVendorId"])
    product_id = config.parse_usb_id(settings["printerProductId"])
    # Usb keeps a reference cycle, so GC may not free it before the next
    # request; closing() releases the USB interface deterministically.
    with closing(open_printer(vendor_id, product_id)) as p:
        invoice_string = generate_invoice_string(data, settings)
        copies = settings["copies"]
        if settings["hasCutter"]:
            # Each copy leaves the printer as a separate ticket.
            for _ in range(copies):
                p.text(invoice_string)
                p.cut()
        else:
            # One strip: a line marks where to tear the copies apart. The
            # final cut command still feeds the paper past the tear bar.
            for i in range(copies):
                p.text(invoice_string)
                if i < copies - 1:
                    p.text("\n" + "=" * MAX_LINE_WIDTH + "\n")
            p.cut()

