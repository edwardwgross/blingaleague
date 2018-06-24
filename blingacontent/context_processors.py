from .models import Meme


def memes(request):
    return {'memes': Meme.objects.all().order_by('name')}
