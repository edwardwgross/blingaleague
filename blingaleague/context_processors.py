from .models import Member, FakeMember


def auth_member(request):
    auth_member = None

    if hasattr(request.user, 'email'):
        auth_member = Member.objects.filter(
            email=request.user.email,
        ).first()

        if not auth_member:
            fake_member = FakeMember.objects.filter(
                email=request.user.email,
            ).first()

            if fake_member:
                auth_member = fake_member.associated_member

    return {'auth_member': auth_member}
