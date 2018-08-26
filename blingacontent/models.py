import base64

from email.mime.text import MIMEText

from pathlib import Path

from django.conf import settings
from django.core import urlresolvers
from django.core.cache import caches
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models
from django.template.loader import render_to_string

from slugify import slugify

from blingaleague.models import Member, FakeMember
from blingaleague.utils import fully_cached_property, clear_cached_properties

from .utils import get_gmail_service


class Meme(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['name']


class Gazette(models.Model):
    headline = models.CharField(max_length=500)
    publish_flag = models.BooleanField(default=False)
    published_date = models.DateField(default=None, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    slug = models.CharField(blank=True, null=True, max_length=200)
    use_markdown = models.BooleanField(default=True)
    email_sent = models.BooleanField(default=False)

    @fully_cached_property
    def published_date_str(self):
        if self.published_date is None:
            return 'not published'

        return self.published_date.strftime('%Y-%m-%d')

    @fully_cached_property
    def previous(self):
        if not self.publish_flag:
            return None

        return Gazette.objects.filter(
            publish_flag=True,
            published_date__lte=self.published_date,
        ).order_by(
            '-published_date',
            '-headline',
        ).exclude(
            pk=self.pk,
        ).first()

    @fully_cached_property
    def next(self):
        if not self.publish_flag:
            return None

        return Gazette.objects.filter(
            publish_flag=True,
            published_date__gte=self.published_date,
        ).order_by(
            'published_date',
            'headline',
        ).exclude(
            pk=self.pk,
        ).first()

    @fully_cached_property
    def full_url(self):
        return "{}{}".format(
            settings.FULL_SITE_URL,
            urlresolvers.reverse_lazy('blingacontent.gazette_detail', args=(self.slug,)),
        )

    def to_html(self, for_email=False):
        html_str = render_to_string(
            'blingacontent/gazette_body.html',
            {
                'gazette': self,
                'for_email': for_email,
            },
        )

        if for_email:
            css_path = Path(settings.STATIC_ROOT) / 'blingaleague' / 'css' / 'blingaleague.css'
            css_fh = open(css_path, 'r')
            html_str = "<html><head><style>{}</style></head><body style=\"font-size:16px\">{}</body></html>".format(
                css_fh.read(),
                html_str,
            )

        return html_str

    def send(self):
        gmail_service = get_gmail_service()

        recipients = []
        for member in Member.objects.filter(defunct=False):
            recipients.append("{} {} <{}>".format(
                member.first_name,
                member.last_name,
                member.email,
            ))

        for fake_member in FakeMember.objects.filter(active=True):
            recipients.append("{} <{}>".format(
                fake_member.name,
                fake_member.email,
            ))

        message = MIMEText(self.to_html(for_email=True), 'html')
        message['to'] = ', '.join(sorted(recipients))
        message['from'] = 'Blingaleague Commissioner <blingaleaguecommissioner@gmail.com>'
        message['subject'] = "The Sanderson Gazette - {}".format(self)

        message64 = base64.urlsafe_b64encode(message.as_string().encode())

        gmail_service.users().messages().send(
            userId='me',
            body={
                'raw': message64.decode(),
            },
        ).execute()

    def clean(self):
        errors = {}

        if self.publish_flag and not self.published_date:
            errors.setdefault(NON_FIELD_ERRORS, []).append(
                ValidationError(
                    message='Published date required to publish',
                    code='published_date_required',
                ),
            )

        if errors:
            raise ValidationError(errors)

        super().clean()

    def save(self, *args, **kwargs):
        self.slug = slugify(
            "{}-{}".format(
                self.published_date_str,
                self.headline,
            ),
        )

        if self.publish_flag and not self.email_sent:
            self.send()
            self.email_sent = True

        super().save(*args, **kwargs)

    def __str__(self):
        return_str = "{} - {}".format(
            self.published_date_str,
            self.headline,
        )

        if self.published_date and not self.publish_flag:
            return_str = "{} (not published)".format(return_str)

        return return_str

    def __repr__(self):
        return str(self)

    class Meta:
        ordering = ['publish_flag', '-published_date']
