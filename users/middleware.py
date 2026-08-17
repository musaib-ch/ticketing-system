from django.shortcuts import redirect
from django.urls import reverse

class ProfileCompletionMiddleware:
    """
    Middleware that forces users to complete their profile (first name, last name, email, employee number, location)
    before they can access any other page.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if any required field is missing
            u = request.user
            profile_incomplete = not all([u.first_name, u.last_name, u.email, u.employee_number, u.location])
            
            # Allow them to access the profile page, logout, or static files
            allowed_paths = [
                reverse('profile_setup'),
                reverse('logout'),
                '/admin/',
            ]
            
            # If incomplete and they are trying to access a restricted page, bounce them to profile setup
            if profile_incomplete and not any(request.path.startswith(p) for p in allowed_paths):
                from django.contrib import messages
                messages.warning(request, "Please complete your profile details below before accessing other pages.")
                return redirect('profile_setup')
                
        response = self.get_response(request)
        return response
