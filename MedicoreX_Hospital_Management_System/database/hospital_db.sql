-- AngalaEswari Hospital Management System - Database Schema
-- MySQL/MariaDB Database


-- Create Database
CREATE DATABASE IF NOT EXISTS hospital_db;
USE hospital_db;


-- Users Table (for authentication)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    user_type ENUM('admin', 'doctor', 'receptionist') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);


-- Patients Table
CREATE TABLE IF NOT EXISTS patients (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100),
    blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'),
    address TEXT,
    medical_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_phone (phone)
);


-- Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    phone VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    experience INT NOT NULL,
    qualification VARCHAR(100) NOT NULL,
    consultation_fee DECIMAL(10, 2) NOT NULL,
    status ENUM('Active', 'On Leave', 'Inactive') DEFAULT 'Active',
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_specialization (specialization),
    INDEX idx_status (status)
);


-- Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    doctor_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    reason TEXT NOT NULL,
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
    INDEX idx_date (date),
    INDEX idx_status (status),
    INDEX idx_patient (patient_id),
    INDEX idx_doctor (doctor_id)
);


-- Bills Table
CREATE TABLE IF NOT EXISTS bills (
    id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    appointment_id VARCHAR(50),
    subtotal DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(10, 2) DEFAULT 0,
    tax DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'paid', 'partial') DEFAULT 'pending',
    payment_method ENUM('cash', 'card', 'upi', 'insurance'),
    notes TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL,
    INDEX idx_date (date),
    INDEX idx_status (status),
    INDEX idx_patient (patient_id)
);


-- Bill Items Table (for detailed billing)
CREATE TABLE IF NOT EXISTS bill_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE
);


-- Audit Log Table (for tracking changes)
CREATE TABLE IF NOT EXISTS audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(50),
    old_data JSON,
    new_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);


-- Insert Default Admin User (password: admin123)
INSERT INTO users (username, password, user_type) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYqVqxqZ/1yO', 'admin');


-- Insert Sample Doctors
INSERT INTO doctors (id, name, specialization, phone, email, experience, qualification, consultation_fee, status) VALUES
('D001', 'Dr. Rajesh Kumar', 'Cardiology', '9876543210', 'rajesh@hospital.com', 15, 'MBBS, MD', 500, 'Active'),
('D002', 'Dr. Priya Sharma', 'Pediatrics', '9876543211', 'priya@hospital.com', 10, 'MBBS, MD', 400, 'Active'),
('D003', 'Dr. Amit Verma', 'Orthopedics', '9876543212', 'amit@hospital.com', 12, 'MBBS, MS', 450, 'Active'),
('D004', 'Dr. Sunita Gupta', 'Gynecology', '9876543213', 'sunita@hospital.com', 8, 'MBBS, MD', 350, 'Active'),
('D005', 'Dr. Vijay Singh', 'Neurology', '9876543214', 'vijay@hospital.com', 20, 'MBBS, MD', 600, 'Active');


-- Insert Sample Patients
INSERT INTO patients (id, name, age, gender, phone, email, blood_group, address, medical_history) VALUES
('P001', 'Rahul Sharma', 35, 'Male', '9988776655', 'rahul@email.com', 'B+', '123 Main St, Delhi', 'Hypertension, Diabetes'),
('P002', 'Anita Desai', 28, 'Female', '9988776656', 'anita@email.com', 'A+', '456 Park Ave, Mumbai', 'No significant history'),
('P003', 'Vikram Patel', 45, 'Male', '9988776657', 'vikram@email.com', 'O+', '789 Church St, Bangalore', 'Previous knee surgery'),
('P004', 'Meera Nair', 32, 'Female', '9988776658', 'meera@email.com', 'AB+', '321 Market Rd, Chennai', 'Allergic to penicillin'),
('P005', 'Suresh Kumar', 50, 'Male', '9988776659', 'suresh@email.com', 'A-', '654 River St, Kolkata', 'Heart disease, taking medication');


-- Insert Sample Appointments
INSERT INTO appointments (id, patient_id, doctor_id, date, time, reason, status) VALUES
('A001', 'P001', 'D001', '2024-12-20', '09:00', 'Regular checkup', 'confirmed'),
('A002', 'P002', 'D002', '2024-12-20', '10:00', 'Child vaccination', 'pending'),
('A003', 'P003', 'D003', '2024-12-21', '14:00', 'Knee pain consultation', 'confirmed'),
('A004', 'P004', 'D004', '2024-12-21', '11:00', 'Prenatal checkup', 'confirmed'),
('A005', 'P005', 'D001', '2024-12-22', '09:30', 'Cardiac evaluation', 'pending');


-- Insert Sample Bills
INSERT INTO bills (id, patient_id, appointment_id, subtotal, discount, tax, total_amount, status, payment_method) VALUES
('B001', 'P001', 'A001', 500, 50, 0, 450, 'paid', 'card'),
('B002', 'P002', 'A002', 400, 0, 0, 400, 'pending', NULL);


-- Insert Sample Bill Items
INSERT INTO bill_items (bill_id, description, amount) VALUES
('B001', 'Consultation Fee', 500),
('B002', 'Consultation Fee', 400);


-- Create Views for Common Queries


-- View: Active Patients with Recent Appointments
CREATE OR REPLACE VIEW active_patients_view AS
SELECT 
    p.*,
    COUNT(a.id) as total_appointments,
    MAX(a.date) as last_appointment_date
FROM patients p
LEFT JOIN appointments a ON p.id = a.patient_id
GROUP BY p.id;


-- View: Doctor Performance
CREATE OR REPLACE VIEW doctor_performance_view AS
SELECT 
    d.*,
    COUNT(a.id) as total_appointments,
    SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as completed_appointments,
    SUM(b.total_amount) as total_revenue
FROM doctors d
LEFT JOIN appointments a ON d.id = a.doctor_id
LEFT JOIN bills b ON a.id = b.appointment_id
GROUP BY d.id;


-- View: Monthly Revenue
CREATE OR REPLACE VIEW monthly_revenue_view AS
SELECT 
    DATE_FORMAT(date, '%Y-%m') as month,
    SUM(total_amount) as total_revenue,
    COUNT(id) as total_bills,
    SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_bills
FROM bills
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY month DESC;


-- Create Stored Procedures


-- Procedure: Create New Patient
DELIMITER //
CREATE PROCEDURE sp_create_patient(
    IN p_name VARCHAR(100),
    IN p_age INT,
    IN p_gender VARCHAR(10),
    IN p_phone VARCHAR(15),
    IN p_email VARCHAR(100),
    IN p_blood_group VARCHAR(5),
    IN p_address TEXT,
    IN p_medical_history TEXT
)
BEGIN
    DECLARE new_id VARCHAR(50);
    SET new_id = CONCAT('P', LPAD(NEXT_ID(), 8, '0'));
    INSERT INTO patients (id, name, age, gender, phone, email, blood_group, address, medical_history)
    VALUES (new_id, p_name, p_age, p_gender, p_phone, p_email, p_blood_group, p_address, p_medical_history);
    SELECT new_id as patient_id;
END //


DELIMITER ;


-- Helper function for generating IDs
DELIMITER //
CREATE FUNCTION NEXT_ID() RETURNS INT
DETERMINISTIC
BEGIN
    DECLARE next_val INT;
    SELECT IFNULL(MAX(CAST(SUBSTRING(id, 2) AS UNSIGNED)), 0) + 1 INTO next_val
    FROM patients;
    RETURN next_val;
END //


DELIMITER ;


-- Triggers for Audit Log


DELIMITER //
CREATE TRIGGER tr_patient_audit_insert
AFTER INSERT ON patients
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (action, entity_type, entity_id, new_data)
    VALUES ('INSERT', 'patient', NEW.id, JSON_OBJECT(
        'name', NEW.name,
        'age', NEW.age,
        'gender', NEW.gender,
        'phone', NEW.phone
    ));
END //


CREATE TRIGGER tr_patient_audit_update
AFTER UPDATE ON patients
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (action, entity_type, entity_id, old_data, new_data)
    VALUES ('UPDATE', 'patient', NEW.id, 
        JSON_OBJECT('name', OLD.name, 'phone', OLD.phone),
        JSON_OBJECT('name', NEW.name, 'phone', NEW.phone)
    );
END //


DELIMITER ;


-- Indexes for Performance Optimization
CREATE INDEX idx_appointments_date_status ON appointments(date, status);
CREATE INDEX idx_bills_date_status ON bills(date, status);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);


-- Grant Permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON hospital_db.* TO 'hospital_user'@'localhost' IDENTIFIED BY 'secure_password';
-- FLUSH PRIVILEGES;