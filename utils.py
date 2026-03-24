from datetime import datetime


def get_status_counts(applications):
    # Store totals for the cards on the home page
    counts = {
        "total": len(applications),
        "Applied": 0,
        "Interview": 0,
        "Rejected": 0,
        "Offer": 0,
        "Closed": 0,
    }

    for application in applications:
        status = application["status"]

        if status in counts:
            counts[status] += 1

    return counts


def get_deadline_state(deadline_text):
    # Work out if the deadline has passed or is close
    try:
        deadline_date = datetime.strptime(deadline_text, "%Y-%m-%d").date()
    except ValueError:
        return "normal"

    today = datetime.today().date()
    days_left = (deadline_date - today).days

    if days_left < 0:
        return "overdue"

    if days_left <= 3:
        return "due-soon"

    return "normal"


def validate_application_form(company, role, status, deadline, application_link):
    # Check the main required fields
    if not company or not role or not status or not deadline:
        return "Please fill in all required fields."

    # Only check the link if the user typed one
    if application_link and not (
        application_link.startswith("http://")
        or application_link.startswith("https://")
    ):
        return "Please enter a valid application link."

    return None