from __future__ import absolute_import, unicode_literals
from ozone.celery import app
from django.template import loader
from django.core.mail import EmailMessage


@app.task
def send_email(from_email, to_email, cc_email, subject, context, email_file):
    email = EmailMessage(
        subject=subject,
        body=loader.render_to_string(email_file, context),
        from_email=from_email,
        to=[to_email],
        cc=[cc_email]
    )
    email.content_subtype = 'html'
    email.send(fail_silently=True)