-- Sample schema for testing the Query Optimizer tool.
-- Deliberately includes an unindexed column (customer_id on orders) so you
-- have something obvious to detect and fix.

CREATE DATABASE IF NOT EXISTS query_optimizer_demo;
USE query_optimizer_demo;

DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    signup_date DATE NOT NULL
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,       -- intentionally NOT indexed at first
    order_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Seed a few thousand rows so EXPLAIN actually shows meaningful row counts.
DELIMITER //
CREATE PROCEDURE seed_demo_data()
BEGIN
    DECLARE i INT DEFAULT 0;
    WHILE i < 2000 DO
        INSERT INTO customers (name, email, signup_date)
        VALUES (CONCAT('Customer ', i), CONCAT('customer', i, '@example.com'),
                DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND()*1000) DAY));
        SET i = i + 1;
    END WHILE;

    SET i = 0;
    WHILE i < 10000 DO
        INSERT INTO orders (customer_id, order_date, status, total)
        VALUES (FLOOR(1 + RAND()*2000),
                DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND()*365) DAY),
                ELT(FLOOR(1+RAND()*3), 'pending', 'shipped', 'delivered'),
                ROUND(RAND()*500, 2));
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL seed_demo_data();
DROP PROCEDURE seed_demo_data;

-- Try this query in the tool BEFORE adding an index - it should flag a full
-- table scan on `orders`:
--   SELECT * FROM orders WHERE customer_id = 42;
--
-- Then run:  CREATE INDEX idx_orders_customer_id ON orders (customer_id);
-- ...and re-analyze the same query to see the finding disappear.
