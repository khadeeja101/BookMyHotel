import random
import string
import sys
from flask import current_app
from flask_mail import Mail, Message

# Global mail instance
mail = Mail()

def generate_verification_code():
    """Generates a random 6-digit numeric verification code for registration."""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code):
    """
    Attempts to send a registration verification pin to the user's email address.
    If the SMTP configuration is invalid or missing, it falls back to printing 
    the code directly to the server terminal console for easy local testing.
    """
    subject = "BookMyHotel.com - Verify Your Registration"
    body = f"""
    Hello!

    Thank you for registering at BookMyHotel.com. 
    To activate your account, please enter the following 6-digit verification code on the verification screen:

    ===========================
    VERIFICATION CODE: {code}
    ===========================

    If you did not request this, please ignore this email.

    Warm regards,
    The BookMyHotel Team
    """

    # Check if SMTP credentials are set
    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        # Log to terminal console clearly
        print_console_fallback(email, code, "Registration Verification")
        return False

    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
    except Exception as e:
        # If SMTP fails (e.g. timeout or auth error), log to console as fallback and print error
        print(f"[SMTP WARNING] Failed to send email to {email} due to error: {e}", file=sys.stderr)
        print_console_fallback(email, code, "Registration Verification (SMTP Fail Fallback)")
        return False


def send_booking_email(email, reservation_details):
    """
    Attempts to send a booking confirmation email to the guest.
    If SMTP parameters are missing, it logs the confirmation details directly to the console.
    """
    subject = f"BookMyHotel.com - Booking Confirmation #{reservation_details.get('id')}"
    body = f"""
    Dear Guest,

    Your booking at BookMyHotel.com has been successfully confirmed!

    --- Reservation Summary ---
    Booking ID: {reservation_details.get('id')}
    Hotel Name: {reservation_details.get('hotel_name')}
    Location: {reservation_details.get('location')}
    Room Type: {reservation_details.get('room_type')}
    Check-In Date: {reservation_details.get('check_in')}
    Check-Out Date: {reservation_details.get('check_out')}
    Services Selected: {", ".join(reservation_details.get('services', []))}
    Discount Code Applied: {reservation_details.get('promo_code', 'None')}
    Total Amount Paid: ${reservation_details.get('total_amount'):.2f} (Securely Processed)
    
    Cancellation Policy:
    Flexible cancellation: cancel up to 24 hours prior to check-in for a full refund.
    Refunds are processed automatically to the original payment method upon cancellation.

    Thank you for choosing BookMyHotel.com. We hope you enjoy your stay!

    Warm regards,
    The BookMyHotel Team
    """

    if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
        print_booking_console_fallback(email, reservation_details)
        return False

    try:
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"[SMTP WARNING] Failed to send booking confirmation email to {email}: {e}", file=sys.stderr)
        print_booking_console_fallback(email, reservation_details)
        return False


def print_console_fallback(email, code, title):
    """Prints a clear, easy-to-read block in the system console containing the verification code."""
    border = "=" * 60
    print(f"\n{border}")
    print(f" {title.upper()} ")
    print(f"{border}")
    print(f" Sent To: {email}")
    print(f" Verification Code: {code}")
    print(f" URL Link: http://localhost:5000/auth/verify?email={email}&code={code}")
    print(f"{border}\n")


def print_booking_console_fallback(email, details):
    """Prints a clear, easy-to-read block in the system console containing the booking details."""
    border = "*" * 60
    print(f"\n{border}")
    print(" BOOKING CONFIRMATION EMAIL FALLBACK (PRINTED TO CONSOLE) ")
    print(f"{border}")
    print(f" Sent To: {email}")
    print(f" Booking ID: {details.get('id')}")
    print(f" Hotel: {details.get('hotel_name')} ({details.get('location')})")
    print(f" Room Type: {details.get('room_type')}")
    print(f" Dates: {details.get('check_in')} to {details.get('check_out')}")
    print(f" Services: {', '.join(details.get('services', []))}")
    print(f" Total Paid: ${details.get('total_amount'):.2f}")
    print(f"{border}\n")
