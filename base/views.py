# user_management/views.py
from django.shortcuts import render

def landing_page(request):
    return render(request, 'landing_page.html')

def farmers(request):
    return render(request, 'farmers.html')

def roasters(request):
    return render(request, 'roasters.html')

def create_account(request):
    return render(request, 'create_account.html')

def farmer_dashboard(request):
    return render(request, 'farmer_dashboard.html')
