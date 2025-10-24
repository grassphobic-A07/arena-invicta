def is_content_staff(user):
    return user.is_authenticated and hasattr(user, "profile") and user.profile.is_content_staff