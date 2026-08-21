from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from database import db
from models import User, EmailVerification
from utils import generate_verification_code, send_verification_email

# Create the auth Blueprint for handling authentication-related tasks
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handles new user registration.
    Saves user with password hash, generates a 6-digit verification pin,
    stores it in the database with an expiration time, and sends a verification email.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Retrieve form data
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        first_name = request.form.get('first_name').strip()
        last_name = request.form.get('last_name').strip()

        # Simple validation
        if not email or not password or not first_name or not last_name:
            flash("All fields are required.", "error")
            return render_template('register.html')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.", "error")
            return render_template('register.html')

        # Create new user instance
        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='customer',  # default role is customer
            is_verified=False  # needs verification before booking/logging in
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            
            # Generate 6-digit numeric verification code
            code = generate_verification_code()
            # Set code expiration time to 15 minutes from now
            expires_at = datetime.utcnow() + timedelta(minutes=15)
            
            # Save verification record in database
            # If an existing verification record exists for this email, delete it first
            EmailVerification.query.filter_by(email=email).delete()
            verification = EmailVerification(email=email, code=code, expires_at=expires_at)
            db.session.add(verification)
            
            db.session.commit()
            
            # Try to dispatch email, falls back to console printing
            email_sent = send_verification_email(email, code)
            
            if email_sent:
                flash("A registration verification email has been sent to your email address.", "success")
            else:
                flash("Development mode: verification code printed to the Python server console.", "info")
                
            return redirect(url_for('auth.verify', email=email))
            
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during registration: {e}", "error")

    return render_template('register.html')


@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    """
    Handles user email verification.
    Accepts code inputs via the verification form or directly via URL parameters.
    """
    email = request.args.get('email', '').strip().lower()
    code_param = request.args.get('code', '').strip()

    # Automatically verify if both email and code are provided via GET URL parameters (one-click link)
    if email and code_param:
        verification = EmailVerification.query.filter_by(email=email, code=code_param).first()
        if verification and verification.expires_at > datetime.utcnow():
            user = User.query.filter_by(email=email).first()
            if user:
                user.is_verified = True
                EmailVerification.query.filter_by(email=email).delete()
                db.session.commit()
                flash("Your email has been verified! You can now log in.", "success")
                return redirect(url_for('auth.login'))
        flash("Invalid or expired verification link.", "error")

    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        entered_code = request.form.get('code').strip()

        if not email or not entered_code:
            flash("Email and verification code are required.", "error")
            return render_template('verify.html', email=email)

        # Retrieve the code record from the database
        verification = EmailVerification.query.filter_by(email=email, code=entered_code).first()

        if not verification:
            flash("Incorrect verification code.", "error")
            return render_template('verify.html', email=email)

        # Check if the code has expired
        if verification.expires_at < datetime.utcnow():
            flash("The verification code has expired. Please register again.", "error")
            return render_template('verify.html', email=email)

        # Update user's verified status
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_verified = True
            # Clean up the verification record
            EmailVerification.query.filter_by(email=email).delete()
            db.session.commit()
            flash("Your email has been verified! You can now log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("User not found.", "error")

    return render_template('verify.html', email=email)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Authenticates registered users.
    Enforces that users must have verified their email to complete login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template('login.html')

        role = request.form.get('login_role', 'customer')
        user = User.query.filter_by(email=email).first()

        # Validate password hash
        if user and user.check_password(password):
            if role == 'admin' and user.role != 'admin':
                flash("Access denied: This account does not have administrator privileges.", "error")
                return render_template('login.html')

            # Check if user is verified
            if not user.is_verified:
                flash("Your email is not verified yet. Please verify it to log in.", "warning")
                return redirect(url_for('auth.verify', email=email))

            # Establish Flask-Login session
            login_user(user)
            flash(f"Welcome back, {user.first_name}!", "success")
            
            # If the user is an admin, redirect them to the admin panel
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            
            return redirect(url_for('main.index'))
        else:
            flash("Invalid email or password.", "error")

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Clears the active session and logs the user out."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for('main.index'))
