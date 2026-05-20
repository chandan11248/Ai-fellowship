from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class BenchmarkSpec:
    question: str
    intent: str
    tables: tuple[str, ...]
    columns: tuple[str, ...]
    filters: str
    joins: str
    sql: str
    explanation: str


def normalize_question(question: str) -> str:
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    return normalized.rstrip("?.!")


def spec(
    question: str,
    intent: str,
    tables: tuple[str, ...],
    columns: tuple[str, ...],
    sql: str,
    explanation: str,
    filters: str = "None",
    joins: str = "None",
) -> BenchmarkSpec:
    return BenchmarkSpec(
        question=question,
        intent=intent,
        tables=tables,
        columns=columns,
        filters=filters,
        joins=joins,
        sql=sql,
        explanation=explanation,
    )


BENCHMARK_SPECS: tuple[BenchmarkSpec, ...] = (
    spec(
        "List all products",
        "Retrieve every product record",
        ("products",),
        ("*",),
        "SELECT * FROM products;",
        "Selects every column from the products table.",
    ),
    spec(
        "Get all customers",
        "Retrieve every customer record",
        ("customers",),
        ("*",),
        "SELECT * FROM customers;",
        "Selects every column from the customers table.",
    ),
    spec(
        "Show all orders",
        "Retrieve every order record",
        ("orders",),
        ("*",),
        "SELECT * FROM orders;",
        "Selects every column from the orders table.",
    ),
    spec(
        "List all employees",
        "Retrieve every employee record",
        ("employees",),
        ("*",),
        "SELECT * FROM employees;",
        "Selects every column from the employees table.",
    ),
    spec(
        "Get all offices",
        "Retrieve every office record",
        ("offices",),
        ("*",),
        "SELECT * FROM offices;",
        "Selects every column from the offices table.",
    ),
    spec(
        "Show all product lines",
        "Retrieve every product line record",
        ("productlines",),
        ("*",),
        "SELECT * FROM productlines;",
        "Selects every column from the productlines table.",
    ),
    spec(
        "List all payments",
        "Retrieve every payment record",
        ("payments",),
        ("*",),
        "SELECT * FROM payments;",
        "Selects every column from the payments table.",
    ),
    spec(
        "Get product names and prices",
        "Retrieve product names with purchase and MSRP prices",
        ("products",),
        ('"productName"', '"buyPrice"', '"MSRP"'),
        'SELECT "productName", "buyPrice", "MSRP"\n'
        "FROM products\n"
        'ORDER BY "productName";',
        "Reads product name and price columns from products and sorts by product name.",
    ),
    spec(
        "Get customer names and cities",
        "Retrieve customer names and their cities",
        ("customers",),
        ('"customerName"', '"city"'),
        'SELECT "customerName", "city"\n'
        "FROM customers\n"
        'ORDER BY "customerName";',
        "Reads customer names and city values from customers.",
    ),
    spec(
        "List employee first and last names",
        "Retrieve employee names",
        ("employees",),
        ('"firstName"', '"lastName"'),
        'SELECT "firstName", "lastName"\n'
        "FROM employees\n"
        'ORDER BY "lastName", "firstName";',
        "Reads employee first and last names and sorts alphabetically.",
    ),
    spec(
        "Get all order dates",
        "Retrieve order numbers and dates",
        ("orders",),
        ('"orderNumber"', '"orderDate"'),
        'SELECT "orderNumber", "orderDate"\n'
        "FROM orders\n"
        'ORDER BY "orderDate", "orderNumber";',
        "Reads each order date with its order number.",
    ),
    spec(
        "Show product vendor list",
        "Retrieve unique product vendors",
        ("products",),
        ('"productVendor"',),
        'SELECT DISTINCT "productVendor"\n'
        "FROM products\n"
        'ORDER BY "productVendor";',
        "Uses DISTINCT to list each product vendor once.",
    ),
    spec(
        "Get all product codes",
        "Retrieve product codes",
        ("products",),
        ('"productCode"',),
        'SELECT "productCode"\n'
        "FROM products\n"
        'ORDER BY "productCode";',
        "Reads all product codes from products.",
    ),
    spec(
        "List all countries from offices",
        "Retrieve office countries",
        ("offices",),
        ('"country"',),
        'SELECT DISTINCT "country"\n'
        "FROM offices\n"
        'ORDER BY "country";',
        "Uses DISTINCT to list the countries that contain offices.",
    ),
    spec(
        "Show all order statuses",
        "Retrieve unique order statuses",
        ("orders",),
        ('"status"',),
        'SELECT DISTINCT "status"\n'
        "FROM orders\n"
        'ORDER BY "status";',
        "Uses DISTINCT to show each order status once.",
    ),
    spec(
        "Get all payment amounts",
        "Retrieve payment amounts",
        ("payments",),
        ('"customerNumber"', '"checkNumber"', '"amount"'),
        'SELECT "customerNumber", "checkNumber", "amount"\n'
        "FROM payments\n"
        'ORDER BY "amount" DESC;',
        "Reads payment amounts with their identifying customer and check numbers.",
    ),
    spec(
        "List all job titles",
        "Retrieve unique employee job titles",
        ("employees",),
        ('"jobTitle"',),
        'SELECT DISTINCT "jobTitle"\n'
        "FROM employees\n"
        'ORDER BY "jobTitle";',
        "Uses DISTINCT to list every job title once.",
    ),
    spec(
        "Get customer phone numbers",
        "Retrieve customer phone numbers",
        ("customers",),
        ('"customerName"', '"phone"'),
        'SELECT "customerName", "phone"\n'
        "FROM customers\n"
        'ORDER BY "customerName";',
        "Reads customer names and phone numbers from customers.",
    ),
    spec(
        "Show product MSRP values",
        "Retrieve MSRP values for products",
        ("products",),
        ('"productName"', '"MSRP"'),
        'SELECT "productName", "MSRP"\n'
        "FROM products\n"
        'ORDER BY "productName";',
        "Reads each product name with its MSRP.",
    ),
    spec(
        "List order numbers",
        "Retrieve order numbers",
        ("orders",),
        ('"orderNumber"',),
        'SELECT "orderNumber"\n'
        "FROM orders\n"
        'ORDER BY "orderNumber";',
        "Reads all order numbers from orders.",
    ),
    spec(
        "Get orders with customer names",
        "Retrieve orders and the customer for each order",
        ("orders", "customers"),
        ('o."orderNumber"', 'o."orderDate"', 'o."status"', 'c."customerName"'),
        'SELECT o."orderNumber", o."orderDate", o."status", c."customerName"\n'
        "FROM orders o\n"
        'JOIN customers c ON c."customerNumber" = o."customerNumber"\n'
        'ORDER BY o."orderNumber";',
        "Joins orders to customers on customerNumber so each order includes the customer name.",
        joins='customers.customerNumber = orders.customerNumber',
    ),
    spec(
        "Get employees with office city",
        "Retrieve employees and their office city",
        ("employees", "offices"),
        ('e."employeeNumber"', 'e."firstName"', 'e."lastName"', 'o."city"'),
        'SELECT e."employeeNumber", e."firstName", e."lastName", o."city" AS office_city\n'
        "FROM employees e\n"
        'JOIN offices o ON o."officeCode" = e."officeCode"\n'
        'ORDER BY e."employeeNumber";',
        "Joins employees to offices by officeCode to attach each employee's office city.",
        joins='offices.officeCode = employees.officeCode',
    ),
    spec(
        "Get payments with customer names",
        "Retrieve payments and customer names",
        ("payments", "customers"),
        ('p."checkNumber"', 'p."paymentDate"', 'p."amount"', 'c."customerName"'),
        'SELECT p."checkNumber", p."paymentDate", p."amount", c."customerName"\n'
        "FROM payments p\n"
        'JOIN customers c ON c."customerNumber" = p."customerNumber"\n'
        'ORDER BY p."paymentDate", p."checkNumber";',
        "Joins payments to customers by customerNumber so payment rows include customer names.",
        joins='customers.customerNumber = payments.customerNumber',
    ),
    spec(
        "Get order details with product names",
        "Retrieve order detail rows and product names",
        ("orderdetails", "products"),
        ('od."orderNumber"', 'p."productName"', 'od."quantityOrdered"', 'od."priceEach"'),
        'SELECT od."orderNumber", p."productName", od."quantityOrdered", od."priceEach"\n'
        "FROM orderdetails od\n"
        'JOIN products p ON p."productCode" = od."productCode"\n'
        'ORDER BY od."orderNumber", p."productName";',
        "Joins orderdetails to products by productCode so each line item includes the product name.",
        joins='products.productCode = orderdetails.productCode',
    ),
    spec(
        "Get products with product line description",
        "Retrieve products and product line descriptions",
        ("products", "productlines"),
        ('p."productCode"', 'p."productName"', 'pl."productLine"', 'pl."textDescription"'),
        'SELECT p."productCode", p."productName", pl."productLine", pl."textDescription"\n'
        "FROM products p\n"
        'JOIN productlines pl ON pl."productLine" = p."productLine"\n'
        'ORDER BY p."productCode";',
        "Joins products to productlines to include the description for each product line.",
        joins='productlines.productLine = products.productLine',
    ),
    spec(
        "Get customers with sales rep names",
        "Retrieve customers and assigned sales representatives",
        ("customers", "employees"),
        ('c."customerName"', 'e."firstName"', 'e."lastName"'),
        'SELECT c."customerName", e."firstName" AS sales_rep_first_name, e."lastName" AS sales_rep_last_name\n'
        "FROM customers c\n"
        'LEFT JOIN employees e ON e."employeeNumber" = c."salesRepEmployeeNumber"\n'
        'ORDER BY c."customerName";',
        "Uses a left join so customers without a sales representative are still included.",
        joins='employees.employeeNumber = customers.salesRepEmployeeNumber',
    ),
    spec(
        "Get orders with customer city",
        "Retrieve orders and customer cities",
        ("orders", "customers"),
        ('o."orderNumber"', 'o."orderDate"', 'o."status"', 'c."city"'),
        'SELECT o."orderNumber", o."orderDate", o."status", c."city"\n'
        "FROM orders o\n"
        'JOIN customers c ON c."customerNumber" = o."customerNumber"\n'
        'ORDER BY o."orderNumber";',
        "Joins orders to customers by customerNumber to include the customer city.",
        joins='customers.customerNumber = orders.customerNumber',
    ),
    spec(
        "Get employees and their manager",
        "Retrieve employees and manager names",
        ("employees",),
        ('e."employeeNumber"', 'e."firstName"', 'e."lastName"', 'm."firstName"', 'm."lastName"'),
        'SELECT e."employeeNumber", e."firstName", e."lastName", '
        'm."firstName" AS manager_first_name, m."lastName" AS manager_last_name\n'
        "FROM employees e\n"
        'LEFT JOIN employees m ON m."employeeNumber" = e."reportsTo"\n'
        'ORDER BY e."employeeNumber";',
        "Uses a self join on employees.reportsTo to include manager names.",
        joins='manager.employeeNumber = employee.reportsTo',
    ),
    spec(
        "Get orderdetails with product vendor",
        "Retrieve order detail rows and product vendors",
        ("orderdetails", "products"),
        ('od."orderNumber"', 'od."productCode"', 'p."productVendor"', 'od."quantityOrdered"', 'od."priceEach"'),
        'SELECT od."orderNumber", od."productCode", p."productVendor", od."quantityOrdered", od."priceEach"\n'
        "FROM orderdetails od\n"
        'JOIN products p ON p."productCode" = od."productCode"\n'
        'ORDER BY od."orderNumber", od."productCode";',
        "Joins orderdetails to products so each order line includes the product vendor.",
        joins='products.productCode = orderdetails.productCode',
    ),
    spec(
        "Get payments with customer country",
        "Retrieve payments and customer countries",
        ("payments", "customers"),
        ('p."checkNumber"', 'p."paymentDate"', 'p."amount"', 'c."country"'),
        'SELECT p."checkNumber", p."paymentDate", p."amount", c."country"\n'
        "FROM payments p\n"
        'JOIN customers c ON c."customerNumber" = p."customerNumber"\n'
        'ORDER BY p."paymentDate", p."checkNumber";',
        "Joins payments to customers by customerNumber to include customer country.",
        joins='customers.customerNumber = payments.customerNumber',
    ),
    spec(
        "Count customers per country",
        "Count customers grouped by country",
        ("customers",),
        ('"country"', "COUNT(*)"),
        'SELECT "country", COUNT(*) AS customer_count\n'
        "FROM customers\n"
        'GROUP BY "country"\n'
        'ORDER BY customer_count DESC, "country";',
        "Groups customers by country and counts rows in each group.",
    ),
    spec(
        "Total payments per customer",
        "Sum payment amounts by customer",
        ("customers", "payments"),
        ('c."customerNumber"', 'c."customerName"', 'SUM(p."amount")'),
        'SELECT c."customerNumber", c."customerName", COALESCE(SUM(p."amount"), 0) AS total_payments\n'
        "FROM customers c\n"
        'LEFT JOIN payments p ON p."customerNumber" = c."customerNumber"\n'
        'GROUP BY c."customerNumber", c."customerName"\n'
        'ORDER BY total_payments DESC, c."customerName";',
        "Left joins customers to payments, groups by customer, and sums payment amounts.",
        joins='payments.customerNumber = customers.customerNumber',
    ),
    spec(
        "Number of orders per status",
        "Count orders grouped by status",
        ("orders",),
        ('"status"', "COUNT(*)"),
        'SELECT "status", COUNT(*) AS order_count\n'
        "FROM orders\n"
        'GROUP BY "status"\n'
        'ORDER BY order_count DESC, "status";',
        "Groups orders by status and counts rows in each group.",
    ),
    spec(
        "Products per product line",
        "Count products grouped by product line",
        ("products",),
        ('"productLine"', "COUNT(*)"),
        'SELECT "productLine", COUNT(*) AS product_count\n'
        "FROM products\n"
        'GROUP BY "productLine"\n'
        'ORDER BY product_count DESC, "productLine";',
        "Groups products by productLine and counts products in each group.",
    ),
    spec(
        "Employees per office",
        "Count employees grouped by office",
        ("offices", "employees"),
        ('o."officeCode"', 'o."city"', 'COUNT(e."employeeNumber")'),
        'SELECT o."officeCode", o."city", COUNT(e."employeeNumber") AS employee_count\n'
        "FROM offices o\n"
        'LEFT JOIN employees e ON e."officeCode" = o."officeCode"\n'
        'GROUP BY o."officeCode", o."city"\n'
        'ORDER BY employee_count DESC, o."officeCode";',
        "Left joins offices to employees, groups by office, and counts employees.",
        joins='employees.officeCode = offices.officeCode',
    ),
    spec(
        "Total stock per product vendor",
        "Sum quantity in stock by product vendor",
        ("products",),
        ('"productVendor"', 'SUM("quantityInStock")'),
        'SELECT "productVendor", SUM("quantityInStock") AS total_stock\n'
        "FROM products\n"
        'GROUP BY "productVendor"\n'
        'ORDER BY total_stock DESC, "productVendor";',
        "Groups products by vendor and sums quantityInStock.",
    ),
    spec(
        "Average buy price per product line",
        "Average buy price grouped by product line",
        ("products",),
        ('"productLine"', 'AVG("buyPrice")'),
        'SELECT "productLine", ROUND(AVG("buyPrice"), 2) AS average_buy_price\n'
        "FROM products\n"
        'GROUP BY "productLine"\n'
        'ORDER BY average_buy_price DESC, "productLine";',
        "Groups products by productLine and calculates the average buyPrice.",
    ),
    spec(
        "Orders per customer",
        "Count orders grouped by customer",
        ("customers", "orders"),
        ('c."customerNumber"', 'c."customerName"', 'COUNT(o."orderNumber")'),
        'SELECT c."customerNumber", c."customerName", COUNT(o."orderNumber") AS order_count\n'
        "FROM customers c\n"
        'LEFT JOIN orders o ON o."customerNumber" = c."customerNumber"\n'
        'GROUP BY c."customerNumber", c."customerName"\n'
        'ORDER BY order_count DESC, c."customerName";',
        "Left joins customers to orders, groups by customer, and counts orders.",
        joins='orders.customerNumber = customers.customerNumber',
    ),
    spec(
        "Max MSRP per product line",
        "Find maximum MSRP grouped by product line",
        ("products",),
        ('"productLine"', 'MAX("MSRP")'),
        'SELECT "productLine", MAX("MSRP") AS max_msrp\n'
        "FROM products\n"
        'GROUP BY "productLine"\n'
        'ORDER BY max_msrp DESC, "productLine";',
        "Groups products by productLine and returns the maximum MSRP in each group.",
    ),
    spec(
        "Min buy price per vendor",
        "Find minimum buy price grouped by vendor",
        ("products",),
        ('"productVendor"', 'MIN("buyPrice")'),
        'SELECT "productVendor", MIN("buyPrice") AS min_buy_price\n'
        "FROM products\n"
        'GROUP BY "productVendor"\n'
        'ORDER BY min_buy_price, "productVendor";',
        "Groups products by vendor and returns the minimum buyPrice in each group.",
    ),
    spec(
        "Total number of customers",
        "Count all customers",
        ("customers",),
        ("COUNT(*)",),
        "SELECT COUNT(*) AS total_customers\nFROM customers;",
        "Counts every row in customers.",
    ),
    spec(
        "Total number of products",
        "Count all products",
        ("products",),
        ("COUNT(*)",),
        "SELECT COUNT(*) AS total_products\nFROM products;",
        "Counts every row in products.",
    ),
    spec(
        "Total revenue from payments",
        "Sum all payment amounts",
        ("payments",),
        ('SUM("amount")',),
        'SELECT SUM("amount") AS total_revenue\nFROM payments;',
        "Sums the amount column across all payments.",
    ),
    spec(
        "Average product price",
        "Calculate average product buy price",
        ("products",),
        ('AVG("buyPrice")',),
        'SELECT ROUND(AVG("buyPrice"), 2) AS average_product_price\nFROM products;',
        "Calculates the average buyPrice for all products.",
    ),
    spec(
        "Max payment amount",
        "Find maximum payment amount",
        ("payments",),
        ('MAX("amount")',),
        'SELECT MAX("amount") AS max_payment_amount\nFROM payments;',
        "Returns the largest payment amount.",
    ),
    spec(
        "Min payment amount",
        "Find minimum payment amount",
        ("payments",),
        ('MIN("amount")',),
        'SELECT MIN("amount") AS min_payment_amount\nFROM payments;',
        "Returns the smallest payment amount.",
    ),
    spec(
        "Count total orders",
        "Count all orders",
        ("orders",),
        ("COUNT(*)",),
        "SELECT COUNT(*) AS total_orders\nFROM orders;",
        "Counts every row in orders.",
    ),
    spec(
        "Total quantity in stock",
        "Sum product stock quantity",
        ("products",),
        ('SUM("quantityInStock")',),
        'SELECT SUM("quantityInStock") AS total_quantity_in_stock\nFROM products;',
        "Sums the quantityInStock column across all products.",
    ),
    spec(
        "Average MSRP",
        "Calculate average MSRP",
        ("products",),
        ('AVG("MSRP")',),
        'SELECT ROUND(AVG("MSRP"), 2) AS average_msrp\nFROM products;',
        "Calculates the average MSRP across all products.",
    ),
    spec(
        "Number of employees",
        "Count all employees",
        ("employees",),
        ("COUNT(*)",),
        "SELECT COUNT(*) AS total_employees\nFROM employees;",
        "Counts every row in employees.",
    ),
)


_LOOKUP = {normalize_question(item.question): item for item in BENCHMARK_SPECS}


def find_spec(question: str) -> BenchmarkSpec:
    normalized = normalize_question(question)
    try:
        return _LOOKUP[normalized]
    except KeyError as exc:
        raise KeyError(f"No benchmark SQL mapping found for question: {question}") from exc
