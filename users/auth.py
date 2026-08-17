from django.contrib.auth.backends import BaseBackend
from .models import User, Team
import openpyxl
import os
from django.conf import settings

class DummyADBackend(BaseBackend):
    """
    Simulates Active Directory Authentication using mock_ad.xlsx.
    """
    def authenticate(self, request, username=None, password=None):
        excel_path = os.path.join(settings.BASE_DIR, 'mock_ad.xlsx')
        if not os.path.exists(excel_path):
            print("Mock AD Excel file not found!")
            return None

        try:
            wb = openpyxl.load_workbook(excel_path)
            ws = wb.active
        except Exception as e:
            print(f"Error reading Mock AD Excel: {e}")
            return None

        # Headers: Username, Password, Email, FirstName, LastName, Department, Role
        ad_user_data = None
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and row[0].lower() == username.lower():
                if row[1] == password:
                    ad_user_data = {
                        'ad_username': row[0],
                        'email': row[2],
                        'first_name': row[3],
                        'last_name': row[4],
                        'department': row[5],
                        'role': row[6]
                    }
                break
        
        if not ad_user_data:
            return None
        
        # Auto-create or update user
        user, created = User.objects.get_or_create(username=username)
        
        user.first_name = ad_user_data['first_name']
        user.last_name = ad_user_data['last_name']
        user.email = ad_user_data['email']
        user.role = ad_user_data['role']
        
        if ad_user_data['role'] == 'admin':
            user.is_staff = True
            user.is_superuser = True
            
        if ad_user_data['department']:
            team, _ = Team.objects.get_or_create(name=ad_user_data['department'])
            # A user can belong to multiple departments; retain that relationship.
            user.save()
            user.teams.add(team)

        user.save()
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
