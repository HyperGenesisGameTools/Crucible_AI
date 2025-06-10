# Project Task Database Setup (`setup_db.py`)

This utility script initializes and populates a local SQLite database designed to store data for an agentic project management system. It creates the necessary relational schema and fills it with realistic, randomly generated data to provide a ready-to-use foundation for application development and testing.

---

## What It Does

The `setup_db.py` script performs the following actions:

1.  **Creates a Database File**: It generates a new SQLite database file named `project_tasks.db` in the same directory.
2.  **Defines the Schema**: It creates three interconnected tables: `projects`, `users`, and `tasks`. It also sets up foreign key constraints to ensure data integrity and a trigger to automatically update the `updated_at` timestamp on tasks.
3.  **Populates with Fake Data**: Using the `Faker` library, it populates the database with a pre-configured number of sample projects, users, and tasks, making the system immediately usable for development.

---

## Database Schema

The script establishes the following three tables:

* **`projects`**: Stores high-level project containers.
    * `id`, `name`, `created_at`
* **`users`**: Contains records of team members who can be assigned tasks.
    * `id`, `name`, `email`, `created_at`
* **`tasks`**: The central table holding individual task details. It links to a project and can be assigned to a user.
    * `id`, `title`, `description`, `status`, `priority`, `due_date`, `created_at`, `updated_at`, `project_id` (Foreign Key), `assignee_id` (Foreign Key)

---

## How to Use

Follow these steps to set up and populate your database.

### 1. Prerequisites

Ensure you have **Python 3** installed on your system.

### 2. Install Dependencies

This script requires the `Faker` library to generate sample data. You can install it using pip:

```bash
pip install Faker
```

### 3. Run the Script

Execute the script from your terminal:

```bash
python setup_db.py
```

Upon successful execution, you will see output messages confirming the database connection, schema creation, and data population. A new file, **`project_tasks.db`**, will appear in your project directory.
