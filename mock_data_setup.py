import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG
from datetime import datetime, timedelta
import random
from typing import List, Dict
import faker

# Initialize faker
fake = faker.Faker()

def create_database_connection():
    """Create database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        if connection.is_connected():
            cursor = connection.cursor()
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            cursor.execute(f"USE {DB_CONFIG['database']}")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_tables(connection):
    """Create the required tables"""
    cursor = connection.cursor()
    
    # Create departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        dept_id INT PRIMARY KEY AUTO_INCREMENT,
        dept_name VARCHAR(50) NOT NULL UNIQUE,
        hod_name VARCHAR(100),
        budget DECIMAL(10, 2),
        established_date DATE,
        contact_email VARCHAR(100),
        CONSTRAINT chk_budget CHECK (budget > 0)
    )
    """)
    
    # Create courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        course_id INT PRIMARY KEY AUTO_INCREMENT,
        dept_id INT,
        course_name VARCHAR(100) NOT NULL,
        credits INT NOT NULL,
        max_capacity INT,
        course_fee DECIMAL(8, 2),
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
        CONSTRAINT chk_credits CHECK (credits BETWEEN 1 AND 6),
        CONSTRAINT chk_capacity CHECK (max_capacity > 0)
    )
    """)
    
    # Create students table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INT PRIMARY KEY AUTO_INCREMENT,
        dept_id INT,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE,
        enrollment_date DATE,
        gpa DECIMAL(3, 2),
        semester INT,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (dept_id) REFERENCES departments(dept_id),
        CONSTRAINT chk_gpa CHECK (gpa BETWEEN 0 AND 4.0),
        CONSTRAINT chk_semester CHECK (semester BETWEEN 1 AND 8)
    )
    """)
    
    # Create enrollments table for many-to-many relationship
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        enrollment_id INT PRIMARY KEY AUTO_INCREMENT,
        student_id INT,
        course_id INT,
        enrollment_date DATE,
        grade DECIMAL(3, 2),
        FOREIGN KEY (student_id) REFERENCES students(student_id),
        FOREIGN KEY (course_id) REFERENCES courses(course_id),
        CONSTRAINT chk_grade CHECK (grade BETWEEN 0 AND 4.0)
    )
    """)
    
    connection.commit()

def generate_mock_data(connection):
    """Generate and insert mock data"""
    cursor = connection.cursor()
    
    # Department data
    departments = [
        ("Computer Science", 500000),
        ("Electrical Engineering", 450000),
        ("Mechanical Engineering", 475000),
        ("Civil Engineering", 400000),
        ("Chemical Engineering", 425000),
        ("Physics", 350000),
        ("Mathematics", 300000),
        ("Biology", 375000)
    ]
    
    # Insert departments
    for dept_name, budget in departments:
        cursor.execute("""
        INSERT INTO departments (dept_name, hod_name, budget, established_date, contact_email)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            dept_name,
            fake.name(),
            budget,
            fake.date_between(start_date='-20y', end_date='-1y'),
            f"{dept_name.lower().replace(' ', '.')}@college.edu"
        ))
    
    # Get department IDs
    cursor.execute("SELECT dept_id FROM departments")
    dept_ids = [x[0] for x in cursor.fetchall()]
    
    # Course data - multiple courses per department
    for dept_id in dept_ids:
        num_courses = random.randint(5, 8)
        for _ in range(num_courses):
            cursor.execute("""
            INSERT INTO courses (dept_id, course_name, credits, max_capacity, course_fee, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                dept_id,
                fake.unique.catch_phrase(),
                random.randint(1, 6),
                random.randint(30, 100),
                random.uniform(500, 2000),
                random.choice([True, True, True, False])  # 75% chance of being active
            ))
    
    # Student data
    for _ in range(50):
        dept_id = random.choice(dept_ids)
        cursor.execute("""
        INSERT INTO students (dept_id, first_name, last_name, email, enrollment_date, gpa, semester, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            dept_id,
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
            fake.date_between(start_date='-4y', end_date='today'),
            round(random.uniform(2.0, 4.0), 2),
            random.randint(1, 8),
            random.choice([True, True, True, False])  # 75% chance of being active
        ))
    
    # Get student and course IDs for enrollments
    cursor.execute("SELECT student_id FROM students")
    student_ids = [x[0] for x in cursor.fetchall()]
    
    cursor.execute("SELECT course_id FROM courses")
    course_ids = [x[0] for x in cursor.fetchall()]
    
    # Create enrollments - each student takes multiple courses
    for student_id in student_ids:
        num_courses = random.randint(3, 6)
        selected_courses = random.sample(course_ids, num_courses)
        for course_id in selected_courses:
            cursor.execute("""
            INSERT INTO enrollments (student_id, course_id, enrollment_date, grade)
            VALUES (%s, %s, %s, %s)
            """, (
                student_id,
                course_id,
                fake.date_between(start_date='-2y', end_date='today'),
                round(random.uniform(2.0, 4.0), 2)
            ))
    
    connection.commit()

def main():
    """Main function to set up the mock database"""
    connection = create_database_connection()
    if connection is None:
        return
    
    try:
        create_tables(connection)
        generate_mock_data(connection)
        print("Mock database setup completed successfully!")
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    main() 