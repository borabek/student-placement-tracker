# Student Placement Tracker

A full-stack Flask web application for managing placement and internship applications in one place.

## Overview

Student Placement Tracker helps users organise their job applications with a clean dashboard, deadline tracking, search and filtering tools, and secure user accounts. The project was built to solve a practical problem faced by students applying for placements and internships.

## Features

- User registration and login
- Add, edit and delete applications
- Search by company, role, or notes
- Filter by application status
- Sort by deadline, company, status, or date added
- Dashboard summary cards
- Deadline alerts for overdue and due soon applications
- Export applications to CSV
- Simple responsive user interface

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS

## Why This Project

Applying for placements usually means tracking many deadlines, statuses, notes, and links at the same time. This project was designed to make that process easier by giving users one place to manage everything clearly.

## Main Learning Outcomes

This project helped strengthen skills in:

- Flask routing and templating
- SQLite database design
- User authentication and session handling
- CRUD operations
- Form validation
- Search, filtering, and sorting logic
- CSV file export
- Front-end layout and styling

## Project Structure

```text
student-placement-tracker/
│
├── app.py
├── utils.py
├── requirements.txt
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── add.html
    ├── edit.html
    ├── login.html
    ├── register.html
    └── _form.html
