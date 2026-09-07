import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Users"

# Define columns matching typical AD export
ws.append(["Username", "Password", "Email", "FirstName", "LastName", "Department", "Role"])

# Add mock users
users = [
    # Username, Password, Email, First, Last, Department, Role
    ["admin_emp", "adminpass", "admin@company.com", "Admin", "User", "IT", "admin"],
    ["rep_hr", "reppass", "hr_rep@company.com", "Sarah", "HR-Rep", "HR", "functional_rep"],
    ["rep_it", "reppass", "it_rep@company.com", "Mike", "IT-Rep", "IT", "functional_rep"],
    ["john_doe", "userpass", "john.doe@company.com", "John", "Doe", "Sales", "employee"],
    ["jane_smith", "userpass", "jane.smith@company.com", "Jane", "Smith", "Marketing", "employee"],
]

for user in users:
    ws.append(user)

wb.save("mock_ad.xlsx")
print("Successfully created mock_ad.xlsx")
