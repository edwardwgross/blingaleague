from .models import Member


def auth_member(request):
    auth_member = None

    if hasattr(request.user, 'email'):
        auth_member = Member.objects.filter(
            email=request.user.email,
        ).first()

    return {'auth_member': auth_member}
