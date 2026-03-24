from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
from utils import get_status_counts, get_deadline_state, validate_application_form

# Create the Flask app
app = Flask(__name__)

# Secret key is needed for flash messages
app.secret_key = "placement_tracker_secret_key"

# Database file name
DATABASE = "database.db"


def get_db_connection():
    # Open a connection to the SQLite database
    connection = sqlite3.connect(DATABASE)
    # This lets us use column names like application["company"]
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    # Connect to the database
    connection = get_db_connection()

    # Create the applications table if it does not already exist
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
            created_at TEXT NOT NULL
        )
        """
    )

    # Save the table creation
    connection.commit()
    # Close the database connection
    connection.close()


def get_application_by_id(application_id):
    # Get one application using its id
    connection = get_db_connection()

    application = connection.execute(
        """
        SELECT * FROM applications
        WHERE id = ?
        """,
        (application_id,),
    ).fetchone()

    connection.close()
    return application


@app.route("/")
def index():
    # Connect to the database
    connection = get_db_connection()

    # Get all saved applications and sort them by deadline
    applications = connection.execute(
        """
        SELECT * FROM applications
        ORDER BY deadline ASC
        """
    ).fetchall()

    connection.close()

    # Convert rows to dictionaries so we can add extra values
    application_list = [dict(row) for row in applications]

    # Add deadline state for each application
    for application in application_list:
        application["deadline_state"] = get_deadline_state(application["deadline"])

    # Get counts for dashboard cards
    counts = get_status_counts(application_list)

    # Show the home page
    return render_template(
        "index.html",
        applications=application_list,
        counts=counts,
    )


@app.route("/add", methods=["GET", "POST"])
def add_application():
    # Check if the user submitted the form
    if request.method == "POST":
        # Get each value from the form and remove extra spaces
        company = request.form["company"].strip()
        role = request.form["role"].strip()
        status = request.form["status"].strip()
        deadline = request.form["deadline"].strip()
        application_link = request.form["application_link"].strip()
        notes = request.form["notes"].strip()

        # Validate the form
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

        # Save the date and time when the application was added
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Connect to the database
        connection = get_db_connection()

        # Insert the new application into the table
        connection.execute(
            """
            INSERT INTO applications (
                company, role, status, deadline, application_link, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company, role, status, deadline, application_link, notes, created_at),
        )

        # Save the new row
        connection.commit()
        # Close the connection
        connection.close()

        # Show a success message
        flash("Application added successfully.")
        # Go back to the home page
        return redirect(url_for("index"))

    # If it is a normal GET request, just show the add page
    return render_template("add.html", application=None)


@app.route("/edit/<int:application_id>", methods=["GET", "POST"])
def edit_application(application_id):
    # Get the selected application
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

        # Validate the form
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

        # Update the row in the database
        connection.execute(
            """
            UPDATE applications
            SET company = ?, role = ?, status = ?, deadline = ?, application_link = ?, notes = ?
            WHERE id = ?
            """,
            (company, role, status, deadline, application_link, notes, application_id),
        )

        connection.commit()
        connection.close()

        flash("Application updated successfully.")
        return redirect(url_for("index"))

    return render_template("edit.html", application=application)


@app.route("/delete/<int:application_id>", methods=["POST"])
def delete_application(application_id):
    # Delete one application by id
    connection = get_db_connection()

    connection.execute(
        """
        DELETE FROM applications
        WHERE id = ?
        """,
        (application_id,),
    )

    connection.commit()
    connection.close()

    flash("Application deleted successfully.")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Create the table before starting the app
    init_db()
    # Run the Flask app in debug mode
    app.run(debug=True)