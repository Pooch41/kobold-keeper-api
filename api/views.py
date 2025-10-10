from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def about(request):
    return render(request, "about.html")


def docs(request):
    return render(request, "docs.html")


def login(request):
    return render(request, "login.html")
