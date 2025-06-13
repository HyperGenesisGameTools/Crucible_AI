import sqlite3
from sqlite3 import Error
import datetime
import random
from faker import Faker

# --- CONFIGURATION ---
DB_FILE = "project_tasks.db"
NUM_FAKE_PROJECTS = 3
NUM_FAKE_USERS = 5
NUM_FAKE_TASKS = 20

def create_connection(db_file):
    """ Create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # Enable foreign key constraint enforcement
        conn.execute("PRAGMA foreign_keys = 1")
        print(f"Successfully connected to SQLite database: {db_file}")
        return conn
    except Error as e:
        print(e)
    return conn

def create_table(conn, create_table_sql):
    """ Create a table from the create_table_sql statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def setup_database_schema(conn):
    """Creates all necessary tables for the application."""
    # SQL statements to create tables with timestamp triggers
    sql_create_projects_table = """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc'))
    );
    """

    sql_create_users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc'))
    );
    """

    sql_create_tasks_table = """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL CHECK(status IN ('To Do', 'In Progress', 'Done')),
        priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
        due_date TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc')),
        project_id INTEGER,
        assignee_id INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
        FOREIGN KEY (assignee_id) REFERENCES users (id) ON DELETE SET NULL
    );
    """
    
    # Trigger to update the 'updated_at' timestamp on tasks table
    sql_create_tasks_update_trigger = """
    CREATE TRIGGER IF NOT EXISTS update_tasks_updated_at
    AFTER UPDATE ON tasks
    FOR EACH ROW
    BEGIN
        UPDATE tasks SET updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'utc') WHERE id = OLD.id;
    END;
    """

    print("Creating database schema...")
    create_table(conn, sql_create_projects_table)
    create_table(conn, sql_create_users_table)
    create_table(conn, sql_create_tasks_table)
    create_table(conn, sql_create_tasks_update_trigger)
    print("Schema setup complete.")


def populate_fake_data(conn):
    """Populates the database with fake data for projects, users, and tasks."""
    fake = Faker()
    cursor = conn.cursor()

    print(f"Populating database with {NUM_FAKE_PROJECTS} projects, {NUM_FAKE_USERS} users, and {NUM_FAKE_TASKS} tasks...")

    # --- Populate Projects ---
    project_ids = []
    project_names = ['AI Agent Development', 'Website Redesign', 'Q3 Marketing Campaign', 'Mobile App Launch', 'Data Warehouse Migration']
    random.shuffle(project_names)
    for i in range(NUM_FAKE_PROJECTS):
        try:
            name = project_names[i]
            cursor.execute("INSERT INTO projects (name) VALUES (?)", (name,))
            project_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError:
            # In case the randomly chosen name already exists
            print(f"Project '{name}' already exists. Skipping.")
            cursor.execute("SELECT id FROM projects WHERE name=?", (name,))
            project_ids.append(cursor.fetchone()[0])


    # --- Populate Users ---
    user_ids = []
    for _ in range(NUM_FAKE_USERS):
        try:
            name = fake.name()
            email = fake.unique.email()
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
            user_ids.append(cursor.lastrowid)
        except sqlite3.IntegrityError:
             print(f"User with email '{email}' already exists. Skipping.")
             cursor.execute("SELECT id FROM users WHERE email=?", (email,))
             user_ids.append(cursor.fetchone()[0])


    # --- Populate Tasks ---
    task_statuses = ['To Do', 'In Progress', 'Done']
    task_priorities = ['Low', 'Medium', 'High']
    for _ in range(NUM_FAKE_TASKS):
        title = fake.catch_phrase()
        description = fake.text(max_nb_chars=200)
        status = random.choice(task_statuses)
        priority = random.choice(task_priorities)
        # Make some tasks have a due date in the near future
        due_date = fake.future_date(end_date="+60d").isoformat() if random.random() > 0.3 else None
        project_id = random.choice(project_ids)
        # Allow some tasks to be unassigned
        assignee_id = random.choice(user_ids + [None]) 

        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, due_date, project_id, assignee_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, status, priority, due_date, project_id, assignee_id))

    conn.commit()
    print("Fake data population complete.")


def main():
    """Main function to orchestrate DB creation and population."""
    conn = create_connection(DB_FILE)

    if conn is not None:
        # Set up the tables and triggers
        setup_database_schema(conn)

        # Populate with fake data
        populate_fake_data(conn)

        # Close the connection
        conn.close()
        print("Database connection closed.")
    else:
        print("Error! cannot create the database connection.")


if __name__ == '__main__':
    main()
