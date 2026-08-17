# HR Servicedesk

A modern, highly customizable IT/HR Ticketing System built with Django. Featuring a sleek glassmorphic UI, dynamic portal branding, advanced role-based access control, and dynamic ticket routing.

## Features

- **Dynamic Portal Branding**: Fully customizable UI directly from the admin dashboard (Portal Name, Theme Colors, Logos, Background Images).
- **Glassmorphic UI**: Beautiful, premium, and fully responsive frontend using CSS Grid and Flexbox.
- **Role-Based Access Control**:
  - **Employee**: Can submit queries and view their own tickets.
  - **Department Rep**: Can view and manage tickets routed to their department.
  - **Admin**: Can view all tickets, manage users, create departments, and manage global branding.
- **Department Routing**: Tickets are routed to functional departments based on user-selected categories.
- **Intelligent Dashboards**: Live queue management with sorting, SLAs, auto-closure rules, and canned responses.

---

## Setup & Installation Instructions

To run this project on a new PC, follow these steps.

### Prerequisites

1. **Python**: Ensure Python 3.10+ is installed on your machine.
   - You can download Python here: [python.org/downloads](https://www.python.org/downloads/)
   - *Note: During installation, make sure to check the box that says **"Add Python to PATH"**.*
2. **Git** (Optional but recommended): For cloning the repository.

### 1. Clone the Repository (or Copy the Project Folder)

If you have the project as a folder, simply navigate into it using your terminal or command prompt:

```bash
cd path/to/"Ticketing System"
```

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to isolate the project's dependencies from your system's Python packages.

```bash
# Create a virtual environment named 'venv'
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

With your virtual environment activated, install all the required Python packages from the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations

Set up the SQLite database by running Django's migration commands:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (Admin)

To access the portal as an administrator (so you can configure branding, users, and departments), you must create a superuser account:

```bash
python manage.py createsuperuser
```
*(Follow the on-screen prompts to set your username, email, and password)*

### 6. Run the Development Server

You are now ready to run the application! Start the Django development server:

```bash
python manage.py runserver
```

Open your web browser and navigate to: **http://127.0.0.1:8000/**

You can log in with the superuser credentials you created in step 5. Once logged in, head to **Admin Tools > Portal Branding** to customize your portal's look and feel, and **Admin Tools > Departments** to start setting up queues!
