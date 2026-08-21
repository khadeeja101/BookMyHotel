from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from database import db
from models import Hotel, Room, Reservation, Payment, Review, Promotion, Service

# Create the admin Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required():
    """Helper check to enforce administrator-only access control."""
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(403)  # Forbidden access

@admin_bp.route('/')
@login_required
def dashboard():
    """
    Renders the Administrator Analytics Dashboard.
    Aggregates performance parameters:
    1. Booked Room Nights: Sum of (check_out - check_in).days for Confirmed reservations.
    2. Room Revenue: Sum of total_amount paid for Confirmed reservations.
    3. Average Daily Rate (ADR): Total Room Revenue / Booked Room Nights.
    
    Includes date filtering to view reservation details for a particular date,
    and individual hotel performance reports.
    """
    admin_required()

    # Preserving tab selection on reload
    active_tab = request.args.get('tab', 'reports')

    # Get search date filter (blank if no filter is applied)
    date_filter_str = request.args.get('date_filter', '').strip()
    
    # Retrieve all confirmed reservations to compute global stats
    confirmed_reservations = Reservation.query.filter_by(status='Confirmed').all()
    
    total_nights = 0
    total_revenue = 0.0

    for res in confirmed_reservations:
        nights = (res.check_out - res.check_in).days
        total_nights += nights
        total_revenue += res.total_amount

    # Average Daily Rate calculation
    adr = total_revenue / total_nights if total_nights > 0 else 0.0

    # Retrieve individual hotel analytics records
    hotels = Hotel.query.all()
    hotel_reports = []
    
    for hotel in hotels:
        # Filter reservations specifically for rooms in this hotel
        hotel_res = Reservation.query.join(Room).filter(
            Room.hotel_id == hotel.id,
            Reservation.status == 'Confirmed'
        ).all()

        h_nights = sum([(r.check_out - r.check_in).days for r in hotel_res])
        h_revenue = sum([r.total_amount for r in hotel_res])
        h_adr = h_revenue / h_nights if h_nights > 0 else 0.0

        # Retrieve review ratings
        reviews = Review.query.filter_by(hotel_id=hotel.id).all()
        h_avg_rating = sum([rev.rating for rev in reviews]) / len(reviews) if reviews else hotel.rating

        hotel_reports.append({
            'id': hotel.id,
            'name': hotel.name,
            'location': hotel.location,
            'reservations_count': len(hotel_res),
            'nights': h_nights,
            'revenue': round(h_revenue, 2),
            'adr': round(h_adr, 2),
            'avg_rating': round(h_avg_rating, 1)
        })

    # Query reservations for date log:
    if date_filter_str:
        try:
            filter_date = datetime.strptime(date_filter_str, '%Y-%m-%d').date()
            date_reservations = Reservation.query.filter(
                Reservation.status == 'Confirmed',
                Reservation.check_in <= filter_date,
                Reservation.check_out > filter_date
            ).all()
        except ValueError:
            # Fallback to all reservations if date format invalid
            date_reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
            date_filter_str = ""
    else:
        # No date filter applied - display all reservations
        date_reservations = Reservation.query.order_by(Reservation.created_at.desc()).all()
        date_filter_str = ""

    # Form helpers: Fetch lists of hotels for dropdown selectors
    all_hotels = Hotel.query.all()

    # Retrieve all promotions
    all_promotions = Promotion.query.all()

    return render_template(
        'admin.html',
        total_nights=total_nights,
        total_revenue=round(total_revenue, 2),
        adr=round(adr, 2),
        hotel_reports=hotel_reports,
        date_reservations=date_reservations,
        selected_date=date_filter_str,
        hotels=all_hotels,
        promotions=all_promotions,
        active_tab=active_tab
    )


@admin_bp.route('/hotel/add', methods=['POST'])
@login_required
def add_hotel():
    """Adds a new hotel property contract to the platform database."""
    admin_required()
    
    name = request.form.get('name').strip()
    location = request.form.get('location').strip()
    description = request.form.get('description').strip()
    rating = request.form.get('rating', type=int, default=5)
    sustainability = request.form.get('sustainability_level', type=int, default=3)
    cleanliness = request.form.get('cleanliness_level', type=int, default=5)
    wifi_speed = request.form.get('wifi_speed', type=int, default=100)
    home_office = 'home_office' in request.form
    image_url = request.form.get('image_url', '').strip()

    service_name = request.form.get('service_name', '').strip()

    if not name or not location:
        flash("Hotel name and location are required.", "error")
        return redirect(url_for('admin.dashboard'))

    # Set default standard image if empty
    if not image_url:
        image_url = "/static/images/hotel_default.jpg"

    new_hotel = Hotel(
        name=name,
        location=location,
        description=description,
        rating=rating,
        sustainability_level=sustainability,
        cleanliness_level=cleanliness,
        wifi_speed=wifi_speed,
        home_office=home_office,
        image_url=image_url
    )

    try:
        db.session.add(new_hotel)
        
        # If a service add-on was selected in the form, create it with defaults if not already present
        if service_name:
            service_map = {
                'Bar': ('Bar and Restaurant', 30.00, 'Daily dining credits for restaurant and custom cocktails'),
                'Restaurant': ('Bar and Restaurant', 30.00, 'Daily dining credits for restaurant and custom cocktails'),
                'Spa': ('Spa Treatment & Relaxation', 90.00, 'Massage treatments and steam baths with sanitizing protocols'),
                'Rent a Car': ('Rent of Cars and Motorbikes', 50.00, 'On-demand door-to-door vehicle rentals'),
                'Ticket for Local Trip': ('Local Trip Tickets & Tourist Guide', 75.00, 'Bespoke guided historic and heritage tours')
            }
            mapped_info = service_map.get(service_name)
            if mapped_info:
                mapped_name, default_price, default_desc = mapped_info
                existing_service = Service.query.filter_by(name=mapped_name).first()
                if not existing_service:
                    new_service = Service(name=mapped_name, price=default_price, description=default_desc)
                    db.session.add(new_service)

        db.session.commit()
        flash(f"Hotel '{name}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to add hotel: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/hotel/edit/<int:hotel_id>', methods=['POST'])
@login_required
def edit_hotel(hotel_id):
    """Edits an existing hotel property's details."""
    admin_required()
    hotel = Hotel.query.get_or_404(hotel_id)

    hotel.name = request.form.get('name').strip()
    hotel.location = request.form.get('location').strip()
    hotel.description = request.form.get('description').strip()
    hotel.rating = request.form.get('rating', type=int, default=5)
    hotel.sustainability_level = request.form.get('sustainability_level', type=int, default=3)
    hotel.cleanliness_level = request.form.get('cleanliness_level', type=int, default=5)
    hotel.wifi_speed = request.form.get('wifi_speed', type=int, default=100)
    hotel.home_office = 'home_office' in request.form
    
    image_url = request.form.get('image_url', '').strip()
    if image_url:
        hotel.image_url = image_url

    try:
        db.session.commit()
        flash(f"Hotel '{hotel.name}' updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update hotel: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/hotel/delete/<int:hotel_id>', methods=['POST'])
@login_required
def delete_hotel(hotel_id):
    """Removes a hotel property from the booking index database."""
    admin_required()
    hotel = Hotel.query.get_or_404(hotel_id)

    try:
        db.session.delete(hotel)
        db.session.commit()
        flash(f"Hotel '{hotel.name}' deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete hotel: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/room/add', methods=['POST'])
@login_required
def add_room():
    """Adds a room category option to a specific hotel property."""
    admin_required()
    
    hotel_id = request.form.get('hotel_id', type=int)
    room_type = request.form.get('room_type').strip()
    base_rate = request.form.get('base_rate', type=float)
    max_occupancy = request.form.get('max_occupancy', type=int, default=2)
    total_rooms = request.form.get('total_rooms', type=int, default=10)
    amenities = request.form.get('amenities', '').strip()
    description = request.form.get('description', '').strip()

    if not hotel_id or not room_type or not base_rate:
        flash("Hotel selection, Room category type, and Daily base rate are required.", "error")
        return redirect(url_for('admin.dashboard'))

    new_room = Room(
        hotel_id=hotel_id,
        room_type=room_type,
        base_rate=base_rate,
        max_occupancy=max_occupancy,
        total_rooms=total_rooms,
        available_rooms=total_rooms,
        amenities=amenities,
        description=description
    )

    try:
        db.session.add(new_room)
        db.session.commit()
        flash(f"Room category '{room_type}' added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to add room: {e}", "error")

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/promotion/add', methods=['POST'])
@login_required
def add_promotion():
    """Creates a new promotion code discount coupon for guests."""
    admin_required()
    
    hotel_id = request.form.get('hotel_id', type=int)
    code = request.form.get('code', '').strip().upper()
    discount_percent = request.form.get('discount_percent', type=float)
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    description = request.form.get('description', '').strip()

    if not hotel_id or not code or not discount_percent or not start_date_str or not end_date_str:
        flash("All fields are required to create a promotion coupon.", "error")
        return redirect(url_for('admin.dashboard'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid promotion date format.", "error")
        return redirect(url_for('admin.dashboard'))

    new_promo = Promotion(
        hotel_id=hotel_id,
        code=code,
        discount_percent=discount_percent,
        start_date=start_date,
        end_date=end_date,
        description=description
    )

    try:
        db.session.add(new_promo)
        db.session.commit()
        flash(f"Promotion coupon '{code}' ({discount_percent}% off) created successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create promotion coupon: {e}", "error")

    return redirect(url_for('admin.dashboard', tab='promotions'))


@admin_bp.route('/promotion/edit/<int:promo_id>', methods=['POST'])
@login_required
def edit_promotion(promo_id):
    """Updates an existing promotion coupon details."""
    admin_required()
    promo = Promotion.query.get_or_404(promo_id)
    
    hotel_id = request.form.get('hotel_id', type=int)
    code = request.form.get('code', '').strip().upper()
    discount_percent = request.form.get('discount_percent', type=float)
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    description = request.form.get('description', '').strip()

    if not hotel_id or not code or not discount_percent or not start_date_str or not end_date_str:
        flash("All fields are required to update a promotion coupon.", "error")
        return redirect(url_for('admin.dashboard', tab='promotions'))

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash("Invalid promotion date format.", "error")
        return redirect(url_for('admin.dashboard', tab='promotions'))

    promo.hotel_id = hotel_id
    promo.code = code
    promo.discount_percent = discount_percent
    promo.start_date = start_date
    promo.end_date = end_date
    promo.description = description

    try:
        db.session.commit()
        flash(f"Promotion coupon '{code}' updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update promotion coupon: {e}", "error")

    return redirect(url_for('admin.dashboard', tab='promotions'))


@admin_bp.route('/promotion/delete/<int:promo_id>', methods=['POST'])
@login_required
def delete_promotion(promo_id):
    """Deletes an existing promotion coupon."""
    admin_required()
    promo = Promotion.query.get_or_404(promo_id)
    try:
        db.session.delete(promo)
        db.session.commit()
        flash(f"Promotion coupon '{promo.code}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete promotion coupon: {e}", "error")
    return redirect(url_for('admin.dashboard', tab='promotions'))


@admin_bp.route('/booking/edit/<int:reservation_id>', methods=['POST'])
@login_required
def edit_booking(reservation_id):
    """Edits reservation check-in/out dates, price, and status (admin override)."""
    admin_required()
    res = Reservation.query.get_or_404(reservation_id)
    
    check_in_str = request.form.get('check_in')
    check_out_str = request.form.get('check_out')
    total_amount_str = request.form.get('total_amount')
    status = request.form.get('status')
    
    try:
        res.check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        res.check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        res.total_amount = float(total_amount_str)
        res.status = status
        db.session.commit()
        flash(f"Reservation #{reservation_id} updated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to update reservation: {e}", "error")
        
    return redirect(url_for('admin.dashboard', tab='dateLog'))


@admin_bp.route('/booking/delete/<int:reservation_id>', methods=['POST'])
@login_required
def delete_booking(reservation_id):
    """Completely deletes a reservation from the database (admin override)."""
    admin_required()
    reservation = Reservation.query.get_or_404(reservation_id)
    try:
        db.session.delete(reservation)
        db.session.commit()
        flash(f"Reservation #{reservation_id} has been completely deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to delete reservation: {e}", "error")
    return redirect(url_for('admin.dashboard', tab='dateLog'))
