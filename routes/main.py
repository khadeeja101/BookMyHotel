import calendar
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user, login_required
from database import db
from models import Hotel, Room, Service, Review, ContactMessage, Promotion, Reservation

from sqlalchemy import or_

# Create the main Blueprint for core user activities
main_bp = Blueprint('main', __name__)

@main_bp.route('/index')
@main_bp.route('/index.html')
def index_redirect():
    return redirect(url_for('main.index'))

@main_bp.route('/home')
@main_bp.route('/dashboard')
@main_bp.route('/')
def index():
    """
    Renders the scrollable homepage landing page containing search forms,
    stats, curated selections, difference points, and promotions.
    """
    # Fetch unique locations for search dropdown suggestion
    all_locations = db.session.query(Hotel.location).distinct().all()
    locations = [loc[0] for loc in all_locations]
    
    # Query all hotels to pass for Curated Selection display
    hotels = Hotel.query.all()
    for hotel in hotels:
        # Precompute pricing and reviews for display
        hotel.temp_min_price = min([r.base_rate for r in hotel.rooms]) if hotel.rooms else 0
        reviews = Review.query.filter_by(hotel_id=hotel.id).all()
        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else hotel.rating
        hotel.temp_avg_rating = round(avg_rating, 1)
        hotel.temp_review_count = len(reviews)

    # Query active promotions
    promotions = Promotion.query.all()

    return render_template(
        'index.html',
        locations=locations,
        hotels=hotels,
        promotions=promotions
    )


@main_bp.route('/hotels')
def browse_hotels():
    """
    Renders the detailed search results page with sidebar filters
    and horizontal hotel listing cards.
    """
    location = request.args.get('location', '').strip()
    price_max = request.args.get('price_max', '').strip()
    rating = request.args.get('rating', '').strip()
    wifi_min = request.args.get('wifi_min', '').strip()
    home_office = request.args.get('home_office', '').strip()
    eco_friendly = request.args.get('eco_friendly', '').strip()
    room_type = request.args.get('room_type', '').strip()
    region = request.args.get('region', '').strip()  # 'Asia' or 'Europe' or 'All'
    category = request.args.get('category', '').strip()  # 'Luxury' or 'Boutique' or 'All'

    # Base query for all hotels
    query = Hotel.query

    # Apply filters dynamically
    if location:
        query = query.filter(Hotel.location.ilike(f"%{location}%"))
    
    if rating:
        query = query.filter(Hotel.rating >= int(rating))
        
    if wifi_min:
        query = query.filter(Hotel.wifi_speed >= int(wifi_min))
        
    if home_office:
        query = query.filter(Hotel.home_office == True)
        
    if eco_friendly:
        query = query.filter(Hotel.sustainability_level >= int(eco_friendly))
        
    if region and region.lower() != 'all':
        if region.lower() == 'asia':
            query = query.filter(Hotel.location.in_(['Dubai', 'Tokyo']))
        elif region.lower() == 'europe':
            query = query.filter(Hotel.location.in_(['Paris', 'London']))
            
    if category and category.lower() != 'all':
        if category.lower() == 'luxury':
            query = query.filter(or_(Hotel.name.ilike('%Marriott%'), Hotel.name.ilike('%Four Seasons%')))
        elif category.lower() == 'boutique':
            query = query.filter(or_(Hotel.name.ilike('%Hilton%'), Hotel.name.ilike('%Hyatt%')))

    # Fetch hotels matching the criteria
    hotels = query.all()
    filtered_hotels = []

    # Post-filtering for price and room type because they are related to Room sub-records
    for hotel in hotels:
        rooms = hotel.rooms
        
        if room_type:
            rooms = [r for r in rooms if r.room_type.lower() == room_type.lower()]
            if not rooms:
                continue

        if price_max:
            rooms = [r for r in rooms if r.base_rate <= float(price_max)]
            if not rooms:
                continue

        reviews = Review.query.filter_by(hotel_id=hotel.id).all()
        avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else hotel.rating
        hotel.temp_avg_rating = round(avg_rating, 1)
        hotel.temp_review_count = len(reviews)
        hotel.temp_min_price = min([r.base_rate for r in hotel.rooms]) if hotel.rooms else 0
        
        filtered_hotels.append(hotel)

    # Fetch unique locations for search dropdown suggestion
    all_locations = db.session.query(Hotel.location).distinct().all()
    locations = [loc[0] for loc in all_locations]

    total_hotels_count = Hotel.query.count()

    return render_template(
        'hotels.html',
        hotels=filtered_hotels,
        total_hotels_count=total_hotels_count,
        locations=locations,
        selected_location=location,
        selected_price=price_max,
        selected_rating=rating,
        selected_wifi=wifi_min,
        selected_home_office=home_office,
        selected_eco=eco_friendly,
        selected_room_type=room_type,
        selected_region=region,
        selected_category=category
    )


@main_bp.route('/hotel/<int:hotel_id>')
def hotel_details(hotel_id):
    """
    Displays the property details for a specific hotel, including its reviews,
    available room types, and add-on services like spa, rentals, etc.
    """
    hotel = Hotel.query.get_or_404(hotel_id)
    rooms = Room.query.filter_by(hotel_id=hotel.id).all()
    services = Service.query.all()
    reviews = Review.query.filter_by(hotel_id=hotel.id).order_by(Review.created_at.desc()).all()
    
    # Calculate average rating
    avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else hotel.rating
    
    # Get active promotions for this hotel
    promotions = Promotion.query.filter(
        Promotion.hotel_id == hotel.id,
        Promotion.end_date >= date.today()
    ).all()

    return render_template(
        'hotel.html',
        hotel=hotel,
        rooms=rooms,
        services=services,
        reviews=reviews,
        avg_rating=round(avg_rating, 1),
        review_count=len(reviews),
        promotions=promotions
    )


@main_bp.route('/hotel/<int:hotel_id>/calendar')
def hotel_calendar_api(hotel_id):
    """
    API endpoint that returns room rates and availability on a day-by-day basis 
    for a chosen month and room type. Renders a calendar visual on the frontend.
    """
    room_id = request.args.get('room_id', type=int)
    year = request.args.get('year', default=datetime.today().year, type=int)
    month = request.args.get('month', default=datetime.today().month, type=int)

    if not room_id:
        return jsonify({'error': 'Room ID is required'}), 400

    room = Room.query.filter_by(id=room_id, hotel_id=hotel_id).first()
    if not room:
        return jsonify({'error': 'Room category not found'}), 404

    # Calculate days in the selected month
    num_days = calendar.monthrange(year, month)[1]
    
    calendar_days = []
    
    for day in range(1, num_days + 1):
        target_date = date(year, month, day)
        
        # Calculate dynamic daily pricing:
        # 1. Base rate
        daily_rate = room.base_rate
        
        # 2. Weekend surcharge: +20% on Friday (4) and Saturday (5)
        weekday = target_date.weekday()
        if weekday in [4, 5]:
            daily_rate *= 1.2
            
        # 3. Seasonal markup: High tourist demand in Summer (June, July, August) +15%
        # Winter holidays (December) +10%
        if target_date.month in [6, 7, 8]:
            daily_rate *= 1.15
        elif target_date.month == 12:
            daily_rate *= 1.10

        # Calculate booked occupancy for this specific day:
        # Find active reservations that overlap with this target date.
        # Condition: check_in <= target_date < check_out
        booked_rooms_count = db.session.query(Reservation).filter(
            Reservation.room_id == room.id,
            Reservation.status == 'Confirmed',
            Reservation.check_in <= target_date,
            Reservation.check_out > target_date
        ).count()
        
        # Calculate availability
        available_rooms = max(0, room.total_rooms - booked_rooms_count)
        status = "Available" if available_rooms > 0 else "Sold Out"

        calendar_days.append({
            'date': target_date.strftime('%Y-%m-%d'),
            'day': day,
            'rate': round(daily_rate, 2),
            'available': available_rooms,
            'total_rooms': room.total_rooms,
            'status': status
        })

    return jsonify({
        'room_type': room.room_type,
        'year': year,
        'month': month,
        'days': calendar_days
    })


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """
    Renders and handles contact inquiries via the support contact form.
    """
    if request.method == 'POST':
        name = request.form.get('name').strip()
        email = request.form.get('email').strip().lower()
        subject = request.form.get('subject').strip()
        message = request.form.get('message').strip()

        if not name or not email or not subject or not message:
            flash("Please fill out all fields in the contact form.", "error")
            return render_template('contact.html')

        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message,
            status='Pending'
        )

        try:
            db.session.add(new_message)
            db.session.commit()
            flash("Thank you for contacting us! We will respond to your query shortly.", "success")
            return redirect(url_for('main.contact'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred sending message: {e}", "error")

    return render_template('contact.html')


@main_bp.route('/hotel/<int:hotel_id>/review', methods=['POST'])
@login_required
def submit_review(hotel_id):
    """
    Allows checked-in or registered customers to publish ratings and feedback for a hotel.
    """
    rating = request.form.get('rating', type=int)
    comment = request.form.get('comment', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash("Invalid rating. Please select 1 to 5 stars.", "error")
        return redirect(url_for('main.hotel_details', hotel_id=hotel_id))

    new_review = Review(
        user_id=current_user.id,
        hotel_id=hotel_id,
        rating=rating,
        comment=comment
    )

    try:
        db.session.add(new_review)
        db.session.commit()
        flash("Thank you for your feedback! Your review has been added.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to submit review: {e}", "error")

    return redirect(url_for('main.hotel_details', hotel_id=hotel_id))
