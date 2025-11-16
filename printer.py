from typing import TypedDict, List, Optional

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

def pos_print(data: Invoice) -> None:
    print(data)

