from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    Response,
)
import sqlite3
import csv
import io
from datetime import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from utils import get_status_counts, get_deadline_state, validate_application_form

# Create the Flask app
app = Flask(__name__)

# Secret key is needed for sessions and flash messages
app.secret_key = "placement_tracker_secret_key"

# Database file name
DATABASE = "database.db"


def get_db_connection():
    # Open a connection to the SQLite database
    connection = sqlite3.connect(DATABASE)
    # This lets us use column names like row["company"]
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    # Create tables if they do not already exist
    connection = get_db_connection()

    # Create users table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Create applications table
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT NOT NULL,
            application_link TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    # Add user_id column if the old table does not have it
    columns = connection.execute("PRAGMA table_info(applications)").fetchall()
    column_names = [column["name"] for column in columns]

    if "user_id" not in column_names:
        connection.execute("ALTER TABLE applications ADD COLUMN user_id INTEGER")

    connection.commit()
    connection.close()


def login_required(view_function):
    # Protect pages that need a signed-in user
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view_function(*args, **kwargs)

    return wrapped_view


def get_current_user():
    # Get the logged-in user from the database
    user_id = session.get("user_id")

    if not user_id:
        return None

    connection = get_db_connection()
    user = connection.execute(
        """
        SELECT * FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    connection.close()
    return user


def get_application_by_id(application_id):
    # Get one application by id for the logged-in user
    connection = get_db_connection()

    application = connection.execute(
        """
        SELECT * FROM applications
        WHERE id = ? AND user_id = ?
        """,
        (application_id, session.get("user_id")),
    ).fetchone()

    connection.close()
    return application


@app.route("/")
def home():
    # Send users to the right page
    if "user_id" in session:
        return redirect(url_for("index"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    # Create a new account
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        if not username or not password or not confirm_password:
            flash("Please fill in all fields.")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html")

        connection = get_db_connection()

        existing_user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if existing_user:
            connection.close()
            flash("That username is already taken.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        connection.execute(
            """
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (username, password_hash, created_at),
        )

        connection.commit()
        connection.close()

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Log the user into the system
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if not username or not password:
            flash("Please fill in all fields.")
            return render_template("login.html")

        connection = get_db_connection()
        user = connection.execute(
            """
            SELECT * FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        connection.close()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        flash("Logged in successfully.")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    # Remove session data and send the user back to login
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def index():
    # Read search, filter and sorting options from the URL
    search_text = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    sort_by = request.args.get("sort", "deadline_asc").strip()

    # Build the base query
    query = """
        SELECT * FROM applications
        WHERE user_id = ?
    """
    parameters = [session["user_id"]]

    # Add search filter
    if search_text:
        query += """
            AND (
                company LIKE ?
                OR role LIKE ?
                OR notes LIKE ?
            )
        """
        like_text = f"%{search_text}%"
        parameters.extend([like_text, like_text, like_text])

    # Add status filter
    if status_filter:
        query += " AND status = ?"
        parameters.append(status_filter)

    # Add sorting
    sort_options = {
        "deadline_asc": "deadline ASC",
        "deadline_desc": "deadline DESC",
        "company_asc": "company ASC",
        "company_desc": "company DESC",
        "status_asc": "status ASC",
        "status_desc": "status DESC",
        "created_desc": "created_at DESC",
        "created_asc": "created_at ASC",
    }

    order_by = sort_options.get(sort_by, "deadline ASC")
    query += f" ORDER BY {order_by}"

    connection = get_db_connection()
    applications = connection.execute(query, tuple(parameters)).fetchall()
    connection.close()

    # Convert database rows to dictionaries
    application_list = [dict(row) for row in applications]

    # Add deadline label info to each application
    for application in application_list:
        application["deadline_state"] = get_deadline_state(application["deadline"])

    # Build the dashboard counts
    counts = get_status_counts(application_list)

    return render_template(
        "index.html",
        applications=application_list,
        counts=counts,
        search_text=search_text,
        status_filter=status_filter,
        sort_by=sort_by,
        current_user=get_current_user(),
    )


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_application():
    # Add a new application
    if request.method == "POST":
        company = request.form["company"].strip()
        role = request.form["role"].strip()
        status = request.form["status"].strip()
        deadline = request.form["deadline"].strip()
        application_link = request.form["application_link"].strip()
        notes = request.form["notes"].strip()

        error_message = validate_application_form(
            company, role, status, deadline, application_link
        )

        if error_message:
            flash(error_message)

            application_data = {
                "company": company,
                "role": role,
                "status": status,
                "deadline": deadline,
                "application_link": application_link,
                "notes": notes,
            }

            return render_template("add.html", application=application_data)

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        connection = get_db_connection()
        connection.execute(
            """
            INSERT INTO applications (
                company, role, status, deadline, application_link, notes, created_at, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company,
                role,
                status,
                deadline,
                application_link,
                notes,
                created_at,
                session["user_id"],
            ),
        )

        connection.commit()
        connection.close()

        flash("Application added successfully.")
        return redirect(url_for("index"))

    return render_template("add.html", application=None)


@app.route("/edit/<int:application_id>", methods=["GET", "POST"])
@login_required
def edit_application(application_id):
    # Get the chosen application
    application = get_application_by_id(application_id)

    if application is None:
        flash("Application not found.")
        return redirect(url_for("index"))

    if request.method == "POST":
        company = request.form["company"].strip()
        role = request.form["role"].strip()
        status = request.form["status"].strip()
        deadline = request.form["deadline"].strip()
        application_link = request.form["application_link"].strip()
        notes = request.form["notes"].strip()

        error_message = validate_application_form(
            company, role, status, deadline, application_link
        )

        if error_message:
            flash(error_message)

            updated_application = {
                "id": application_id,
                "company": company,
                "role": role,
                "status": status,
                "deadline": deadline,
                "application_link": application_link,
                "notes": notes,
                "created_at": application["created_at"],
            }

            return render_template("edit.html", application=updated_application)

        connection = get_db_connection()
        connection.execute(
            """
            UPDATE applications
            SET company = ?, role = ?, status = ?, deadline = ?, application_link = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                company,
                role,
                status,
                deadline,
                application_link,
                notes,
                application_id,
                session["user_id"],
            ),
        )

        connection.commit()
        connection.close()

        flash("Application updated successfully.")
        return redirect(url_for("index"))

    return render_template("edit.html", application=application)


@app.route("/delete/<int:application_id>", methods=["POST"])
@login_required
def delete_application(application_id):
    # Delete one application for the logged-in user
    connection = get_db_connection()

    connection.execute(
        """
        DELETE FROM applications
        WHERE id = ? AND user_id = ?
        """,
        (application_id, session["user_id"]),
    )

    connection.commit()
    connection.close()

    flash("Application deleted successfully.")
    return redirect(url_for("index"))


@app.route("/export")
@login_required
def export_csv():
    # Export the user's applications as CSV
    search_text = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "").strip()
    sort_by = request.args.get("sort", "deadline_asc").strip()

    query = """
        SELECT company, role, status, deadline, application_link, notes, created_at
        FROM applications
        WHERE user_id = ?
    """
    parameters = [session["user_id"]]

    if search_text:
        query += """
            AND (
                company LIKE ?
                OR role LIKE ?
                OR notes LIKE ?
            )
        """
        like_text = f"%{search_text}%"
        parameters.extend([like_text, like_text, like_text])

    if status_filter:
        query += " AND status = ?"
        parameters.append(status_filter)

    sort_options = {
        "deadline_asc": "deadline ASC",
        "deadline_desc": "deadline DESC",
        "company_asc": "company ASC",
        "company_desc": "company DESC",
        "status_asc": "status ASC",
        "status_desc": "status DESC",
        "created_desc": "created_at DESC",
        "created_asc": "created_at ASC",
    }

    order_by = sort_options.get(sort_by, "deadline ASC")
    query += f" ORDER BY {order_by}"

    connection = get_db_connection()
    applications = connection.execute(query, tuple(parameters)).fetchall()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    writer.writerow(
        ["Company", "Role", "Status", "Deadline", "Application Link", "Notes", "Created At"]
    )

    # Write the application rows
    for application in applications:
        writer.writerow(
            [
                application["company"],
                application["role"],
                application["status"],
                application["deadline"],
                application["application_link"],
                application["notes"],
                application["created_at"],
            ]
        )

    csv_data = output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


if __name__ == "__main__":
    # Create tables before starting the app
    init_db()
    # Run the Flask app in debug mode
    app.run(debug=True)