import random
import string
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db
from models import Hotel, Room, Service, Reservation, Payment, Promotion, reservation_services, Review
from utils import send_booking_email

# Create the booking Blueprint
booking_bp = Blueprint('booking', __name__, url_prefix='/booking')

def calculate_stay_amount(room, check_in_date, check_out_date):
    """
    Helper function to calculate the total room charge by summing the dynamic 
    daily room rate for each night of the stay.
    """
    total_room_cost = 0.0
    current_day = check_in_date
    
    # Iterate through each night of the stay (up to check_out - 1)
    while current_day < check_out_date:
        daily_rate = room.base_rate
        
        # Weekend surcharge (+20% on Friday/Saturday nights)
        if current_day.weekday() in [4, 5]:
            daily_rate *= 1.2
            
        # Seasonal surcharge (+15% in Summer June-August, +10% in Winter December)
        if current_day.month in [6, 7, 8]:
            daily_rate *= 1.15
        elif current_day.month == 12:
            daily_rate *= 1.10
            
        total_room_cost += daily_rate
        current_day += timedelta(days=1)
        
    return round(total_room_cost, 2)


@booking_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """
    Manages the booking creation and dummy payment transaction.
    GET: Displays the reservation summary, dynamic prices, selected amenities,
         promo code forms, and transparent cancellation policy warnings.
    POST: Processes the payment details, reserves the room, processes refunds if error, 
          and registers transactions.
    """
    # Enforce verified email constraint
    if not current_user.is_verified:
        flash("You must verify your email before booking a reservation.", "warning")
        return redirect(url_for('auth.verify', email=current_user.email))

    if request.method == 'POST':
        # Retrieve form data
        room_id = request.form.get('room_id', type=int)
        check_in_str = request.form.get('check_in')
        check_out_str = request.form.get('check_out')
        promo_code = request.form.get('promo_code', '').strip().upper()
        selected_services_ids = request.form.getlist('services')  # List of strings
        payment_method = request.form.get('payment_method', 'Card')
        
        # Dummy card/paypal checkout inputs
        card_number = request.form.get('card_number')
        paypal_email = request.form.get('paypal_email')

        # Form validations
        if not room_id or not check_in_str or not check_out_str:
            flash("Invalid checkout details.", "error")
            return redirect(url_for('main.index'))

        try:
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('main.index'))

        if check_in >= check_out:
            flash("Check-out date must be after check-in date.", "error")
            return redirect(url_for('main.index'))
            
        if check_in < date.today():
            flash("Check-in date cannot be in the past.", "error")
            return redirect(url_for('main.index'))

        # Fetch room and hotel details
        room = Room.query.get_or_404(room_id)
        hotel = room.hotel

        # Check real-time room availability:
        # Check if the number of overlapping bookings leaves at least one room free
        booked_rooms_count = db.session.query(Reservation).filter(
            Reservation.room_id == room.id,
            Reservation.status == 'Confirmed',
            Reservation.check_in < check_out,
            Reservation.check_out > check_in
        ).count()

        if booked_rooms_count >= room.total_rooms:
            flash(f"Sorry, all rooms of type '{room.room_type}' are sold out for your selected dates.", "error")
            return redirect(url_for('main.hotel_details', hotel_id=hotel.id))

        # Calculate pricing components
        room_cost = calculate_stay_amount(room, check_in, check_out)
        
        # Calculate selected services cost
        services_cost = 0.0
        services_list = []
        for s_id in selected_services_ids:
            service = Service.query.get(int(s_id))
            if service:
                services_cost += service.price
                services_list.append(service)

        subtotal = room_cost + services_cost
        discount = 0.0

        # Apply promotion code discount if valid
        if promo_code:
            promotion = Promotion.query.filter(
                Promotion.hotel_id == hotel.id,
                Promotion.code == promo_code,
                Promotion.start_date <= check_in,
                Promotion.end_date >= check_in
            ).first()
            if promotion:
                discount = subtotal * (promotion.discount_percent / 100.0)
            else:
                flash(f"Promotion code '{promo_code}' is invalid or expired for these dates.", "warning")

        # Sustainable Tourism Incentive: 
        # If the hotel has a high eco-rating (level >= 4), apply a 10% eco-tax-break incentive
        eco_discount = 0.0
        if hotel.sustainability_level >= 4:
            eco_discount = subtotal * 0.10
            discount += eco_discount

        total_amount = max(0.0, subtotal - discount)

        # Generate a secure dummy transaction ID
        txn_id = "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

        # Build reservation and payment records
        new_reservation = Reservation(
            user_id=current_user.id,
            room_id=room.id,
            check_in=check_in,
            check_out=check_out,
            total_amount=round(total_amount, 2),
            status='Confirmed'
        )

        # Add services linked to this reservation
        for service in services_list:
            new_reservation.services.append(service)

        try:
            db.session.add(new_reservation)
            db.session.flush()  # Generates the reservation ID

            # Create dummy payment log
            new_payment = Payment(
                reservation_id=new_reservation.id,
                payment_method=payment_method,
                amount=new_reservation.total_amount,
                status='Paid',
                transaction_id=txn_id
            )
            db.session.add(new_payment)
            db.session.commit()

            # Prepare confirmation details
            services_names = [s.name for s in services_list]
            if eco_discount > 0:
                services_names.append("Eco-Friendly Tax Break (-10%)")
            
            confirmation_details = {
                'id': new_reservation.id,
                'hotel_name': hotel.name,
                'location': hotel.location,
                'room_type': room.room_type,
                'check_in': check_in.strftime('%Y-%m-%d'),
                'check_out': check_out.strftime('%Y-%m-%d'),
                'services': services_names,
                'promo_code': promo_code if promo_code else ('ECO-SAVER' if eco_discount > 0 else 'None'),
                'total_amount': new_reservation.total_amount
            }

            # Send email, printing fallback automatically if SMTP credentials fail
            send_booking_email(current_user.email, confirmation_details)
            
            flash("Reservation completed successfully! A booking confirmation email has been sent.", "success")
            return redirect(url_for('booking.receipt', reservation_id=new_reservation.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Failed to complete reservation payment: {e}", "error")
            return redirect(url_for('main.hotel_details', hotel_id=hotel.id))

    # GET Request: Renders checkout preview page
    room_id = request.args.get('room_id', type=int)
    check_in_str = request.args.get('check_in')
    check_out_str = request.args.get('check_out')

    if not room_id or not check_in_str or not check_out_str:
        flash("Please select a hotel, room type, and date range first.", "warning")
        return redirect(url_for('main.index'))

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid dates entered.", "error")
        return redirect(url_for('main.index'))

    room = Room.query.get_or_404(room_id)
    hotel = room.hotel
    
    # Calculate costs
    room_cost = calculate_stay_amount(room, check_in, check_out)
    nights = (check_out - check_in).days
    
    services = Service.query.all()
    
    # Eco indicator for warning/points UI alert
    is_eco_friendly = hotel.sustainability_level >= 4

    return render_template(
        'payment.html',
        room=room,
        hotel=hotel,
        check_in=check_in_str,
        check_out=check_out_str,
        nights=nights,
        room_cost=room_cost,
        services=services,
        is_eco_friendly=is_eco_friendly
    )


@booking_bp.route('/my-bookings')
@login_required
def my_bookings():
    """
    Renders the customer reservation dashboard.
    Splits reservation entries into Active/Future bookings and Past history.
    """
    today = date.today()
    
    # Retrieve all user bookings
    all_reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.check_in.desc()).all()
    
    future_bookings = []
    past_bookings = []
    
    for res in all_reservations:
        # Populate dynamic review link triggers
        reviews = Review.query.filter_by(user_id=current_user.id, hotel_id=res.room.hotel_id).first()
        res.temp_has_reviewed = True if reviews else False
        
        if res.check_in >= today and res.status == 'Confirmed':
            future_bookings.append(res)
        else:
            past_bookings.append(res)

    return render_template(
        'bookings.html',
        future_bookings=future_bookings,
        past_bookings=past_bookings,
        today=today
    )


@booking_bp.route('/<int:reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(reservation_id):
    """
    Cancels a confirmed future reservation and initiates a dummy refund.
    Transparently displays the refund result to the customer.
    """
    reservation = Reservation.query.get_or_404(reservation_id)

    # Security check: Ensure reservation belongs to the current user (unless admin)
    if reservation.user_id != current_user.id and current_user.role != 'admin':
        flash("Unauthorized cancellation request.", "error")
        return redirect(url_for('booking.my_bookings'))

    # Cancellation policy check: Must be cancelled at least 24 hours prior to check-in
    cancellation_deadline = reservation.check_in - timedelta(days=1)
    if date.today() > cancellation_deadline:
        flash("cancellation failed: Bookings must be cancelled at least 24 hours prior to check-in as per the hotel policy.", "error")
        return redirect(url_for('booking.my_bookings'))

    if reservation.status == 'Cancelled':
        flash("This reservation is already cancelled.", "warning")
        return redirect(url_for('booking.my_bookings'))

    # Update reservation status
    reservation.status = 'Cancelled'

    try:
        # Find associated payment transactions to issue a refund
        payments = Payment.query.filter_by(reservation_id=reservation.id, status='Paid').all()
        refund_amount = 0.0
        
        for payment in payments:
            payment.status = 'Refunded'
            refund_amount += payment.amount

        db.session.commit()
        
        # Alert message displaying refund transaction success
        flash(f"Reservation #{reservation.id} cancelled successfully! A full refund of ${refund_amount:.2f} has been processed back to your payment account.", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred during booking cancellation: {e}", "error")

    if current_user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('booking.my_bookings'))


@booking_bp.route('/receipt/<int:reservation_id>')
@login_required
def receipt(reservation_id):
    """
    Renders the checkout payment receipt receipt page after a successful booking.
    """
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # Enforce access control
    if reservation.user_id != current_user.id:
        abort(403)
        
    payment = Payment.query.filter_by(reservation_id=reservation.id).first()
    
    return render_template(
        'receipt.html',
        reservation=reservation,
        payment=payment
    )
