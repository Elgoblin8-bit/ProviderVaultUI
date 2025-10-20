import json
import os
import mimetypes
from django.shortcuts import render
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
    FileResponse,
    Http404,
)
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.conf import settings
import dotenv
from .models import Users
from django.core.cache import cache
from django.contrib.auth import authenticate
from django.utils.crypto import get_random_string

dotenv.load_dotenv()


# Create your views here.
def home(request):
    return render(request, "home.html")


def main_page(request):
    return render(request, "main_page.html")


def register(request):
    return render(request, "register.html")


def login(request):
    return render(request, "login.html")


def auth(request):
    token = request.GET.get("token")
    email = cache.get(f"mfa:{token}")
    if email is None:
        return HttpResponseForbidden("You do not have permission to access this page!")

    return render(request, "auth_page.html")


@require_POST
def login_to_database(request):
    """
    View to handle user login.

    Expects POST with 'email' and 'password'.
    """
    data = json.loads(request.body)
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return JsonResponse({"message": "Please enter both email and password!"})

    check_password_requirements_message = check_password_requirements(password)
    if check_password_requirements_message != "":
        return JsonResponse({"message": check_password_requirements_message})

    try:
        user = authenticate(request, email=email, password=password)

        if user is None:
            return JsonResponse({"message": "Invalid email or password!"})

        django_cache_token = get_random_string(32)
        cache.set(f"mfa:{django_cache_token}", email, timeout=300)
        return JsonResponse(
            {"message": "Passwords match!", "token": django_cache_token}
        )
    except Exception as e:
        print(f"Login Error: {str(e)}")
        return JsonResponse({"message": "An error occurred"})


@require_POST
def register_to_database(request):
    """
    View to handle user registration.

    Expects POST with 'email' and 'password'.
    """
    data = json.loads(request.body)
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return JsonResponse({"message": "Please enter both email and password!"})
    try:
        user = Users.objects.create_user(email=email, user_type="User")
        user.set_password(password)
        user.save()
        return JsonResponse({"message": "Registration Successful!"})
    except Exception as e:
        print(f"Registration Error: {str(e)}")
        return JsonResponse({"message": "An error occurred"})


@require_POST
def check_match(request):
    """
    View to check if two fields (e.g., password and confirm_password) match.
    Expects POST with 'password' and 'confirm_password'.
    """
    password = request.POST.get("password", "")
    confirm_password = request.POST.get("confirm_password", "")
    if password and confirm_password and password != confirm_password:
        return HttpResponse("Passwords do not match!", content_type="text/html")
    elif not password or not confirm_password:
        return HttpResponse("Please enter a Password!", content_type="text/html")
    return HttpResponse("", content_type="text/html")


@require_POST
def check_password(request):
    """
    View to validate password constraints.

    Expects POST with 'password'.
    """

    password = request.POST.get("password", "")
    check_password_requirements_message = check_password_requirements(password)
    return HttpResponse(check_password_requirements_message, content_type="text/html")


def check_password_requirements(password) -> str:
    """
    Helper function to validate password constraints.

    Returns a string with the error message if any constraint is violated,
    otherwise returns an empty string.
    """
    if len(password) < 8:
        return "Password must be at least 8 characters long!"
    elif not any(character.islower() for character in password) or not any(
        character.isupper() for character in password
    ):
        return "Password must contain both uppercase and lowercase letters!"
    elif not any(character.isdigit() for character in password):
        return "Password must include at least one number!"
    elif not any(character in "!@#$%^&*" for character in password):
        return "Password must include at least one special character (!@#$%^&*)!"

    return ""


def index(request):
    return render(request, "ui.html")

# Allowed file types with their MIME types
ALLOWED_FILE_TYPES = {
    'pdf': 'application/pdf',
    'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'txt': 'text/plain',
    'json': 'application/json',
    'csv': 'text/csv',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'xls': 'application/vnd.ms-excel',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'gif': 'image/gif',
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file(file):
    """Validate file type and size"""
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f'File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB'

    # Get file extension
    file_ext = file.name.split('.')[-1].lower()

    # Check if file type is allowed
    if file_ext not in ALLOWED_FILE_TYPES:
        return False, f'File type ".{file_ext}" is not allowed. Allowed types: {", ".join(ALLOWED_FILE_TYPES.keys())}'

    # Verify MIME type
    content_type = file.content_type
    expected_mime = ALLOWED_FILE_TYPES[file_ext]

    # Some browsers may send different MIME types, so we'll be lenient
    if content_type and not content_type.startswith(expected_mime.split('/')[0]):
        # Allow if it's a generic binary or octet-stream
        if content_type not in ['application/octet-stream', 'binary/octet-stream']:
            return False, f'Invalid content type for .{file_ext} file'

    return True, 'Valid file'

@csrf_exempt
def upload_document(request):
    if request.method == 'POST':
        # Handle file upload
        if 'document' in request.FILES:
            uploaded_file = request.FILES['document']

            # Validate the file
            is_valid, message = validate_file(uploaded_file)
            if not is_valid:
                return JsonResponse({'success': False, 'message': message}, status=400)



            # Save the file
            try:
                # Create uploads directory if it doesn't exist
                upload_dir = 'uploads'
                os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)

                # Generate safe filename
                filename = uploaded_file.name
                file_path = os.path.join(upload_dir, filename)

                # Save file using Django's storage system
                saved_path = default_storage.save(file_path, uploaded_file)

                return JsonResponse({
                    'success': True,
                    'message': f'Document "{uploaded_file.name}" uploaded successfully!',
                    'filename': uploaded_file.name,
                    'size': uploaded_file.size,
                    'file_type': uploaded_file.name.split('.')[-1].lower(),
                    'path': saved_path
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error saving file: {str(e)}'
                }, status=500)

        return JsonResponse({'success': False, 'message': 'No file uploaded'}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

def download_document(request, filename):
    """Handle file downloads"""
    try:
        # Construct the file path
        file_path = os.path.join(settings.MEDIA_ROOT, 'uploads', filename)

        # Check if file exists
        if not os.path.exists(file_path):
            raise Http404(f"File '{filename}' not found")

        # Open and return the file
        file_handle = open(file_path, 'rb')

        # Determine the content type
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = 'application/octet-stream'

        # Create the response
        response = FileResponse(file_handle, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        raise Http404(f"Error downloading file: {str(e)}")

def settings_view(request):
    return render(request, "settings.html")

def documents_view(request):
    """Display all available documents in a separate window"""
    try:
        # Get all files from the uploads directory
        uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        documents = []

        if os.path.exists(uploads_dir):
            for filename in os.listdir(uploads_dir):
                file_path = os.path.join(uploads_dir, filename)
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    file_ext = filename.split('.')[-1].lower() if '.' in filename else ''

                    documents.append({
                        'name': filename,
                        'size': file_stats.st_size,
                        'size_kb': round(file_stats.st_size / 1024, 2),
                        'modified': file_stats.st_mtime,
                        'type': file_ext,
                    })

            # Sort by modified date (newest first)
            documents.sort(key=lambda x: x['modified'], reverse=True)

        return render(request, "documents.html", {'documents': documents})

    except Exception as e:
        return render(request, "documents.html", {'documents': [], 'error': str(e)})