import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Numeric, Date, SmallInteger, Text, ForeignKey
from sqlalchemy.orm import relationship
from config import config

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_engine(config.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Productlines(Base):
    __tablename__ = "productlines"
    productLine = Column(String(50), primary_key=True)
    textDescription = Column(String(4000))
    htmlDescription = Column(Text)
    image = Column(Text)


class Products(Base):
    __tablename__ = "products"
    productCode = Column(String(15), primary_key=True)
    productName = Column(String(70), nullable=False)
    productLine = Column(String(50), ForeignKey("productlines.productLine"), nullable=False)
    productScale = Column(String(10), nullable=False)
    productVendor = Column(String(50), nullable=False)
    productDescription = Column(Text, nullable=False)
    quantityInStock = Column(Integer, nullable=False)
    buyPrice = Column(Numeric(10, 2), nullable=False)
    msrp = Column(Numeric(10, 2), nullable=False)


class Offices(Base):
    __tablename__ = "offices"
    officeCode = Column(String(10), primary_key=True)
    city = Column(String(50), nullable=False)
    phone = Column(String(50), nullable=False)
    addressLine1 = Column(String(50), nullable=False)
    addressLine2 = Column(String(50))
    state = Column(String(50))
    country = Column(String(50), nullable=False)
    postalCode = Column(String(15), nullable=False)
    territory = Column(String(10), nullable=False)


class Employees(Base):
    __tablename__ = "employees"
    employeeNumber = Column(Integer, primary_key=True)
    lastName = Column(String(50), nullable=False)
    firstName = Column(String(50), nullable=False)
    extension = Column(String(10), nullable=False)
    email = Column(String(100), nullable=False)
    officeCode = Column(String(10), ForeignKey("offices.officeCode"), nullable=False)
    reportsTo = Column(Integer, ForeignKey("employees.employeeNumber"))
    jobTitle = Column(String(50), nullable=False)


class Customers(Base):
    __tablename__ = "customers"
    customerNumber = Column(Integer, primary_key=True)
    customerName = Column(String(50), nullable=False)
    contactLastName = Column(String(50), nullable=False)
    contactFirstName = Column(String(50), nullable=False)
    phone = Column(String(50), nullable=False)
    addressLine1 = Column(String(50), nullable=False)
    addressLine2 = Column(String(50))
    city = Column(String(50), nullable=False)
    state = Column(String(50))
    postalCode = Column(String(15))
    country = Column(String(50), nullable=False)
    salesRepEmployeeNumber = Column(Integer, ForeignKey("employees.employeeNumber"))
    creditLimit = Column(Numeric(10, 2))
    sales_rep = relationship("Employees", backref="customers")
    orders = relationship("Orders", backref="customer")
    payments = relationship("Payments", backref="customer")


class Payments(Base):
    __tablename__ = "payments"
    customerNumber = Column(Integer, ForeignKey("customers.customerNumber"), primary_key=True)
    checkNumber = Column(String(50), primary_key=True)
    paymentDate = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)


class Orders(Base):
    __tablename__ = "orders"
    orderNumber = Column(Integer, primary_key=True)
    orderDate = Column(Date, nullable=False)
    requiredDate = Column(Date, nullable=False)
    shippedDate = Column(Date)
    status = Column(String(15), nullable=False)
    comments = Column(Text)
    customerNumber = Column(Integer, ForeignKey("customers.customerNumber"), nullable=False)
    orderdetails = relationship("Orderdetails", backref="order")


class Orderdetails(Base):
    __tablename__ = "orderdetails"
    orderNumber = Column(Integer, ForeignKey("orders.orderNumber"), primary_key=True)
    productCode = Column(String(15), ForeignKey("products.productCode"), primary_key=True)
    quantityOrdered = Column(Integer, nullable=False)
    priceEach = Column(Numeric(10, 2), nullable=False)
    orderLineNumber = Column(SmallInteger, nullable=False)
    product = relationship("Products", backref="orderdetails")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise