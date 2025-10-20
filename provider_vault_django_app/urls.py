"""
URL configuration for provider_vault_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from .views import (
    auth,
    check_match,
    check_password,
    documents_view,
    download_document,
    home,
    index,
    login,
    login_to_database,
    main_page,
    register,
    register_to_database,
    settings_view,
    upload_document,
)

urlpatterns = [
    path("", home, name="home"),
    path("main_page/", main_page, name="main_page"),
    path("register/", register, name="register"),
    path("login/", login, name="login"),
    path("login_to_database/", login_to_database, name="login_to_database"),
    path("register_to_database/", register_to_database, name="register_to_database"),
    path("auth/", auth, name="auth"),
    path(
        "check_match/", check_match, name="check_match"
    ),  # HTMX endpoint for element text matching
    path(
        "check_password/", check_password, name="check_password"
    ),  # HTMX endpoint for password validation
    # Document management URLs
    path("index/", index, name="index"),
    path("upload/", upload_document, name="upload_document"),
    path("download/<str:filename>", download_document, name="download_document"),
    path("settings/", settings_view, name="settings"),
    path("documents/", documents_view, name="documents"),
]
