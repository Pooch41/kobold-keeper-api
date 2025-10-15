from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "home.html"

class AboutView(TemplateView):
    template_name = "about.html"

class DocsView(TemplateView):
    template_name = "docs.html"

class LoginView(TemplateView):
    template_name = "login.html"
