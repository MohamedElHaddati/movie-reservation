from django.conf import settings
from django.core.mail import send_mail


def send_ticket_email(recipient, reservation_id, pdf_path):
    subject = f'Cinebook Ticket #{reservation_id}'
    message = f'Your reservation is confirmed. Your ticket PDF was generated at: {pdf_path}'
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
