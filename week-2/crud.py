import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from database import Customers, Orders, Payments, Products, Employees, Offices, Productlines, Orderdetails
from schemas import (
    CustomersCreate,
    CustomersUpdate,
    CustomersOut,
    OrdersOut,
    PaymentsOut,
)

logger = logging.getLogger(__name__)


def get_customer(db: Session, customer_number: int) -> Optional[Customers]:
    logger.info(f"Fetching customer with customerNumber: {customer_number}")
    result = db.query(Customers).filter(Customers.customerNumber == customer_number).first()
    if not result:
        logger.warning(f"Customer {customer_number} not found")
    return result


def get_customers(db: Session, skip: int = 0, limit: int = 10) -> List[Customers]:
    logger.info(f"Fetching customers with skip={skip}, limit={limit}")
    return db.query(Customers).offset(skip).limit(limit).all()


def get_customers_count(db: Session) -> int:
    logger.info("Counting total customers")
    return db.query(func.count(Customers.customerNumber)).scalar()


def create_customer(db: Session, customer: CustomersCreate) -> Customers:
    logger.info(f"Creating new customer: {customer.customerName}")
    db_customer = Customers(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    logger.info(f"Customer created with customerNumber: {db_customer.customerNumber}")
    return db_customer


def update_customer(db: Session, customer_number: int, customer: CustomersUpdate) -> Optional[Customers]:
    logger.info(f"Updating customer {customer_number}")
    db_customer = get_customer(db, customer_number)
    if not db_customer:
        logger.warning(f"Cannot update - customer {customer_number} not found")
        return None
    
    update_data = customer.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_customer, key, value)
    
    db.commit()
    db.refresh(db_customer)
    logger.info(f"Customer {customer_number} updated successfully")
    return db_customer


def delete_customer(db: Session, customer_number: int) -> bool:
    logger.info(f"Deleting customer {customer_number}")
    db_customer = get_customer(db, customer_number)
    if not db_customer:
        logger.warning(f"Cannot delete - customer {customer_number} not found")
        return False
    
    db.delete(db_customer)
    db.commit()
    logger.info(f"Customer {customer_number} deleted successfully")
    return True


def get_customer_orders(db: Session, customer_number: int) -> List[Orders]:
    logger.info(f"Fetching orders for customer {customer_number}")
    return db.query(Orders).filter(Orders.customerNumber == customer_number).all()


def get_customer_payments(db: Session, customer_number: int) -> List[Payments]:
    logger.info(f"Fetching payments for customer {customer_number}")
    return db.query(Payments).filter(Payments.customerNumber == customer_number).all()


def count_customers(db: Session) -> int:
    logger.info("Query: COUNT customers")
    return db.query(func.count(Customers.customerNumber)).scalar()


def count_orders(db: Session) -> int:
    logger.info("Query: COUNT orders")
    return db.query(func.count(Orders.orderNumber)).scalar()


def count_products(db: Session) -> int:
    logger.info("Query: COUNT products")
    return db.query(func.count(Products.productCode)).scalar()


def count_employees(db: Session) -> int:
    logger.info("Query: COUNT employees")
    return db.query(func.count(Employees.employeeNumber)).scalar()


def count_offices(db: Session) -> int:
    logger.info("Query: COUNT offices")
    return db.query(func.count(Offices.officeCode)).scalar()


def count_payments(db: Session) -> int:
    logger.info("Query: COUNT payments")
    return db.query(func.count(Payments.checkNumber)).scalar()


def count_orderdetails(db: Session) -> int:
    logger.info("Query: COUNT orderdetails")
    return db.query(func.count(Orderdetails.orderNumber)).scalar()


def count_productlines(db: Session) -> int:
    logger.info("Query: COUNT productlines")
    return db.query(func.count(Productlines.productLine)).scalar()


def get_all_counts(db: Session):
    logger.info("Starting count queries for all tables")
    
    customers_count = count_customers(db)
    orders_count = count_orders(db)
    products_count = count_products(db)
    employees_count = count_employees(db)
    offices_count = count_offices(db)
    payments_count = count_payments(db)
    orderdetails_count = count_orderdetails(db)
    productlines_count = count_productlines(db)
    
    logger.info("All count queries completed")
    
    return {
        "customers": customers_count,
        "orders": orders_count,
        "products": products_count,
        "employees": employees_count,
        "offices": offices_count,
        "payments": payments_count,
        "orderdetails": orderdetails_count,
        "productlines": productlines_count
    }