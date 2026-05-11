import logging
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

logger = logging.getLogger(__name__)


class ProductlinesBase(BaseModel):
    productLine: str
    textDescription: Optional[str] = None
    htmlDescription: Optional[str] = None


class ProductlinesCreate(ProductlinesBase):
    pass


class ProductlinesOut(ProductlinesBase):
    class Config:
        from_attributes = True


class ProductsBase(BaseModel):
    productCode: str
    productName: str
    productLine: str
    productScale: str
    productVendor: str
    productDescription: str
    quantityInStock: int
    buyPrice: float
    msrp: float


class ProductsCreate(ProductsBase):
    pass


class ProductsOut(ProductsBase):
    class Config:
        from_attributes = True


class OfficesBase(BaseModel):
    officeCode: str
    city: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    state: Optional[str] = None
    country: str
    postalCode: str
    territory: str


class OfficesCreate(OfficesBase):
    pass


class OfficesOut(OfficesBase):
    class Config:
        from_attributes = True


class EmployeesBase(BaseModel):
    employeeNumber: int
    lastName: str
    firstName: str
    extension: str
    email: str
    officeCode: str
    reportsTo: Optional[int] = None
    jobTitle: str


class EmployeesCreate(EmployeesBase):
    pass


class EmployeesOut(EmployeesBase):
    class Config:
        from_attributes = True


class CustomersBase(BaseModel):
    customerNumber: int
    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[float] = None


class CustomersCreate(BaseModel):
    customerName: str
    contactLastName: str
    contactFirstName: str
    phone: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[float] = None


class CustomersUpdate(BaseModel):
    customerName: Optional[str] = None
    contactLastName: Optional[str] = None
    contactFirstName: Optional[str] = None
    phone: Optional[str] = None
    addressLine1: Optional[str] = None
    addressLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[float] = None


class OrdersOut(BaseModel):
    orderNumber: int
    orderDate: date
    requiredDate: date
    shippedDate: Optional[date] = None
    status: str
    comments: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentsOut(BaseModel):
    customerNumber: int
    checkNumber: str
    paymentDate: date
    amount: float

    class Config:
        from_attributes = True


class CustomersOut(CustomersBase):
    orders: List[OrdersOut] = []
    payments: List[PaymentsOut] = []

    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1, le=100)


class CustomerListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    data: List[CustomersOut]


class CountResponse(BaseModel):
    count: int
    table: str


class OverallCountsResponse(BaseModel):
    customers: int
    orders: int
    products: int
    employees: int
    offices: int
    payments: int
    orderdetails: int
    productlines: int