import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from crud import (
    get_customer,
    get_customers,
    get_customers_count,
    create_customer,
    update_customer,
    delete_customer,
    get_customer_orders,
    get_customer_payments,
    count_customers,
    count_orders,
    count_products,
    count_employees,
    count_offices,
    count_payments,
    count_orderdetails,
    count_productlines,
    get_all_counts,
)
from schemas import (
    CustomersCreate,
    CustomersUpdate,
    CustomersOut,
    CustomerListResponse,
    CountResponse,
    OverallCountsResponse,
    OrdersOut,
    PaymentsOut,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}


@router.get("/customers/count", response_model=CountResponse)
def get_customers_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /customers/count - Request received")
    start_time = time.time()
    
    count = count_customers(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /customers/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="customers")


@router.get("/customers/{customerNumber}", response_model=CustomersOut)
def read_customer(customerNumber: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customerNumber} - Request received")
    start_time = time.time()
    
    customer = get_customer(db, customerNumber)
    
    if not customer:
        logger.warning(f"Customer {customerNumber} not found - returning 404")
        raise HTTPException(status_code=404, detail="Customer not found")
    
    orders = get_customer_orders(db, customerNumber)
    payments = get_customer_payments(db, customerNumber)
    
    response = CustomersOut(
        customerNumber=customer.customerNumber,
        customerName=customer.customerName,
        contactLastName=customer.contactLastName,
        contactFirstName=customer.contactFirstName,
        phone=customer.phone,
        addressLine1=customer.addressLine1,
        addressLine2=customer.addressLine2,
        city=customer.city,
        state=customer.state,
        postalCode=customer.postalCode,
        country=customer.country,
        salesRepEmployeeNumber=customer.salesRepEmployeeNumber,
        creditLimit=customer.creditLimit,
        orders=[OrdersOut.model_validate(o) for o in orders],
        payments=[PaymentsOut.model_validate(p) for p in payments]
    )
    
    elapsed = time.time() - start_time
    logger.info(f"GET /customers/{customerNumber} - Response sent ({elapsed:.3f}s)")
    return response


@router.get("/customers", response_model=CustomerListResponse)
def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    logger.info(f"GET /customers - Request received (skip={skip}, limit={limit})")
    start_time = time.time()
    
    total = get_customers_count(db)
    customers = get_customers(db, skip, limit)
    
    customer_list = []
    for c in customers:
        orders = get_customer_orders(db, c.customerNumber)
        payments = get_customer_payments(db, c.customerNumber)
        customer_list.append(CustomersOut(
            customerNumber=c.customerNumber,
            customerName=c.customerName,
            contactLastName=c.contactLastName,
            contactFirstName=c.contactFirstName,
            phone=c.phone,
            addressLine1=c.addressLine1,
            addressLine2=c.addressLine2,
            city=c.city,
            state=c.state,
            postalCode=c.postalCode,
            country=c.country,
            salesRepEmployeeNumber=c.salesRepEmployeeNumber,
            creditLimit=c.creditLimit,
            orders=[OrdersOut.model_validate(o) for o in orders],
            payments=[PaymentsOut.model_validate(p) for p in payments]
        ))
    
    elapsed = time.time() - start_time
    logger.info(f"GET /customers - Response sent (total={total}, elapsed={elapsed:.3f}s)")
    
    return CustomerListResponse(total=total, skip=skip, limit=limit, data=customer_list)


@router.post("/customers", response_model=CustomersOut, status_code=201)
def create_new_customer(customer: CustomersCreate, db: Session = Depends(get_db)):
    logger.info(f"POST /customers - Request received for: {customer.customerName}")
    start_time = time.time()
    
    new_customer = create_customer(db, customer)
    
    orders = get_customer_orders(db, new_customer.customerNumber)
    payments = get_customer_payments(db, new_customer.customerNumber)
    
    response = CustomersOut(
        customerNumber=new_customer.customerNumber,
        customerName=new_customer.customerName,
        contactLastName=new_customer.contactLastName,
        contactFirstName=new_customer.contactFirstName,
        phone=new_customer.phone,
        addressLine1=new_customer.addressLine1,
        addressLine2=new_customer.addressLine2,
        city=new_customer.city,
        state=new_customer.state,
        postalCode=new_customer.postalCode,
        country=new_customer.country,
        salesRepEmployeeNumber=new_customer.salesRepEmployeeNumber,
        creditLimit=new_customer.creditLimit,
        orders=[],
        payments=[]
    )
    
    elapsed = time.time() - start_time
    logger.info(f"POST /customers - Customer created (id={new_customer.customerNumber}, elapsed={elapsed:.3f}s)")
    return response


@router.put("/customers/{customerNumber}", response_model=CustomersOut)
def update_existing_customer(
    customerNumber: int,
    customer: CustomersUpdate,
    db: Session = Depends(get_db)
):
    logger.info(f"PUT /customers/{customerNumber} - Request received")
    start_time = time.time()
    
    updated_customer = update_customer(db, customerNumber, customer)
    
    if not updated_customer:
        logger.warning(f"PUT /customers/{customerNumber} - Customer not found")
        raise HTTPException(status_code=404, detail="Customer not found")
    
    orders = get_customer_orders(db, customerNumber)
    payments = get_customer_payments(db, customerNumber)
    
    response = CustomersOut(
        customerNumber=updated_customer.customerNumber,
        customerName=updated_customer.customerName,
        contactLastName=updated_customer.contactLastName,
        contactFirstName=updated_customer.contactFirstName,
        phone=updated_customer.phone,
        addressLine1=updated_customer.addressLine1,
        addressLine2=updated_customer.addressLine2,
        city=updated_customer.city,
        state=updated_customer.state,
        postalCode=updated_customer.postalCode,
        country=updated_customer.country,
        salesRepEmployeeNumber=updated_customer.salesRepEmployeeNumber,
        creditLimit=updated_customer.creditLimit,
        orders=[OrdersOut.model_validate(o) for o in orders],
        payments=[PaymentsOut.model_validate(p) for p in payments]
    )
    
    elapsed = time.time() - start_time
    logger.info(f"PUT /customers/{customerNumber} - Customer updated (elapsed={elapsed:.3f}s)")
    return response


@router.delete("/customers/{customerNumber}")
def delete_existing_customer(customerNumber: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /customers/{customerNumber} - Request received")
    start_time = time.time()
    
    success = delete_customer(db, customerNumber)
    
    if not success:
        logger.warning(f"DELETE /customers/{customerNumber} - Customer not found")
        raise HTTPException(status_code=404, detail="Customer not found")
    
    elapsed = time.time() - start_time
    logger.info(f"DELETE /customers/{customerNumber} - Customer deleted (elapsed={elapsed:.3f}s)")
    return {"message": f"Customer {customerNumber} deleted successfully"}


@router.get("/orders/count", response_model=CountResponse)
def get_orders_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /orders/count - Request received")
    start_time = time.time()
    
    count = count_orders(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /orders/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="orders")


@router.get("/products/count", response_model=CountResponse)
def get_products_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /products/count - Request received")
    start_time = time.time()
    
    count = count_products(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /products/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="products")


@router.get("/employees/count", response_model=CountResponse)
def get_employees_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /employees/count - Request received")
    start_time = time.time()
    
    count = count_employees(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /employees/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="employees")


@router.get("/offices/count", response_model=CountResponse)
def get_offices_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /offices/count - Request received")
    start_time = time.time()
    
    count = count_offices(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /offices/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="offices")


@router.get("/payments/count", response_model=CountResponse)
def get_payments_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /payments/count - Request received")
    start_time = time.time()
    
    count = count_payments(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /payments/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="payments")


@router.get("/orderdetails/count", response_model=CountResponse)
def get_orderdetails_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /orderdetails/count - Request received")
    start_time = time.time()
    
    count = count_orderdetails(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /orderdetails/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="orderdetails")


@router.get("/productlines/count", response_model=CountResponse)
def get_productlines_count_endpoint(db: Session = Depends(get_db)):
    logger.info("GET /productlines/count - Request received")
    start_time = time.time()
    
    count = count_productlines(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /productlines/count - Response sent (count={count}, elapsed={elapsed:.3f}s)")
    return CountResponse(count=count, table="productlines")


@router.get("/overall_counts", response_model=OverallCountsResponse)
def get_overall_counts(db: Session = Depends(get_db)):
    logger.info("GET /overall_counts - Concurrent request received")
    start_time = time.time()
    
    counts = get_all_counts(db)
    
    elapsed = time.time() - start_time
    logger.info(f"GET /overall_counts - Response sent (elapsed={elapsed:.3f}s)")
    
    return OverallCountsResponse(**counts)