import os
from datetime import date, timedelta
from flask import Flask, render_template, redirect
from flask_login import LoginManager
from database import db
from config import Config
from models import User, Hotel, Room, Service, Promotion, Reservation
from utils import mail

def create_app():
    """
    Application factory pattern. Initializes the Flask app, configurations,
    database connection, login systems, and SMTP services.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions with the Flask app context
    db.init_app(app)
    mail.init_app(app)

    # Initialize Flask-Login system
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """Loads a User object from the database using their numeric ID."""
        return User.query.get(int(user_id))

    # Import and register modular Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.booking import booking_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # Global error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        """Custom forbidden access page."""
        return render_template('base.html', error_title="403 Forbidden", error_msg="You do not have permission to access this page."), 403

    @app.errorhandler(404)
    def not_found_error(error):
        """Custom resource not found page."""
        return redirect('/')

    @app.errorhandler(500)
    def internal_error(error):
        """Custom internal server error page."""
        db.session.rollback()
        return render_template('base.html', error_title="500 Internal Server Error", error_msg="An unexpected error occurred on our server. Please try again later."), 500

    # Initialize and pre-seed the database within the application context
    with app.app_context():
        db.create_all()
        seed_database()

    return app


def seed_database():
    """
    Pre-populates the database with default hotels, room configurations,
    optional paid guest services, discounts, and a default admin user.
    Runs only if the database tables are empty.
    """
    # 1. Seed Default Services if empty
    if Service.query.count() == 0:
        services = [
            Service(name="Bar and Restaurant", description="Daily dining credits for restaurant and custom cocktails", price=30.00),
            Service(name="Rent of Cars and Motorbikes", description="On-demand door-to-door vehicle rentals", price=50.00),
            Service(name="Local Trip Tickets & Tourist Guide", description="Bespoke guided historic and heritage tours", price=75.00),
            Service(name="Spa Treatment & Relaxation", description="Massage treatments and steam baths with sanitizing protocols", price=90.00)
        ]
        for s in services:
            db.session.add(s)
        db.session.commit()
        print("[Database Seed] Add-on Services pre-populated.")

    # 2. Seed Default Hotels if empty
    if Hotel.query.count() == 0:
        hotels = [
            Hotel(
                name="The Marriott Dubai Marina",
                location="Dubai",
                description="A luxurious 5-star experience overlooking the pristine Arabian Gulf. Features complete sanitization routines, super-fast Wi-Fi, and historic city tours. Fully work-friendly.",
                rating=5,
                sustainability_level=3,
                cleanliness_level=5,
                wifi_speed=150,
                home_office=True,
                image_url="/static/images/marriott.jpg"
            ),
            Hotel(
                name="The Hilton Paris Opera",
                location="Paris",
                description="Experience classic French elegance with a modern touch. Located close to the historical center, featuring curated local trip guides and eco-friendly energy structures.",
                rating=5,
                sustainability_level=5,  # Eco-friendly (triggers 10% tax break)
                cleanliness_level=5,
                wifi_speed=100,
                home_office=True,
                image_url="/static/images/hilton.jpg"
            ),
            Hotel(
                name="The Hyatt Regency Tokyo",
                location="Tokyo",
                description="Perfect blend of Japanese tradition and technology in Shinjuku. Offering premium cleanliness standards, high-speed business networking, and organic guest-chef dining options.",
                rating=5,
                sustainability_level=4,  # Eco-friendly (triggers 10% tax break)
                cleanliness_level=5,
                wifi_speed=200,
                home_office=True,
                image_url="/static/images/hyatt.jpg"
            ),
            Hotel(
                name="The Four Seasons London Park Lane",
                location="London",
                description="A quiet botanical-rich retreat in the heart of Mayfair. Features dynamic luxury services, premium spa programs, and antibacterial-sanitized rooms.",
                rating=5,
                sustainability_level=2,
                cleanliness_level=5,
                wifi_speed=120,
                home_office=False,
                image_url="/static/images/fourseasons.jpg"
            )
        ]
        for h in hotels:
            db.session.add(h)
        db.session.commit()
        print("[Database Seed] 4 Major Hotels pre-populated.")

        # Seed Rooms for each of these hotels
        all_hotels = Hotel.query.all()
        for hotel in all_hotels:
            rooms = [
                Room(
                    hotel_id=hotel.id,
                    room_type="Single Room",
                    base_rate=120.00,
                    max_occupancy=1,
                    total_rooms=10,
                    available_rooms=10,
                    amenities="Wi-Fi, Work Desk, Sanitized Toiletries, Shower",
                    description="Cozy, single room designed for digital nomads. Includes dedicated workspace, home-office layout, and robust Wi-Fi."
                ),
                Room(
                    hotel_id=hotel.id,
                    room_type="Double Room",
                    base_rate=180.00,
                    max_occupancy=2,
                    total_rooms=15,
                    available_rooms=15,
                    amenities="Wi-Fi, Air Conditioning, TV, Mini-Fridge, Bath",
                    description="Spacious double room equipped with antibacterial hygiene products, home-office desk, and a balcony view."
                ),
                Room(
                    hotel_id=hotel.id,
                    room_type="Executive Suite",
                    base_rate=350.00,
                    max_occupancy=4,
                    total_rooms=5,
                    available_rooms=5,
                    amenities="Wi-Fi, Kitchenette, King Bed, Living Room, Spa Access, Safe",
                    description="Elite suite featuring a fully-equipped kitchen (eat-in option), privacy layouts, workspace, and premium amenities."
                )
            ]
            for r in rooms:
                db.session.add(r)
        
        # Seed default Promotions
        # Marriott promo coupon
        marriott_hotel = Hotel.query.filter(Hotel.name.like("%Marriott%")).first()
        if marriott_hotel:
            promo1 = Promotion(
                hotel_id=marriott_hotel.id,
                code="MARRIOTT20",
                discount_percent=20.0,
                start_date=date.today() - timedelta(days=5),
                end_date=date.today() + timedelta(days=60),
                description="Seasonal promotion: get 20% discount on all bookings!"
            )
            db.session.add(promo1)

        # Hyatt promo coupon
        hyatt_hotel = Hotel.query.filter(Hotel.name.like("%Hyatt%")).first()
        if hyatt_hotel:
            promo2 = Promotion(
                hotel_id=hyatt_hotel.id,
                code="TOKYO15",
                discount_percent=15.0,
                start_date=date.today() - timedelta(days=5),
                end_date=date.today() + timedelta(days=60),
                description="Tokyo Welcome Deal: save 15% on rooms."
            )
            db.session.add(promo2)

        db.session.commit()
        print("[Database Seed] Hotel room configurations and default promotions added.")

    # 3. Seed Default Administrator Account if empty
    admin_user = User.query.filter_by(role='admin').first()
    if not admin_user:
        admin = User(
            email="admin@bookmyhotel.com",
            first_name="Khadeeja",
            last_name="Administrator",
            role="admin",
            is_verified=True  # Automatically verified
        )
        admin.set_password("adminpassword")
        db.session.add(admin)
        db.session.commit()
        print("[Database Seed] Admin account created: email=admin@bookmyhotel.com, password=adminpassword")
    else:
        if admin_user.first_name != "Khadeeja":
            admin_user.first_name = "Khadeeja"
            db.session.commit()
            print("[Database Seed] Admin name updated to Khadeeja")

    # 4. Seed reservations for Marriott Dubai Marina in Dec 2026
    marriott = Hotel.query.filter(Hotel.name.like("%Marriott%")).first()
    if marriott:
        dec_start = date(2026, 12, 1)
        dec_end = date(2026, 12, 31)
        existing_dec_res = Reservation.query.join(Room).filter(
            Room.hotel_id == marriott.id,
            Reservation.check_in >= dec_start,
            Reservation.check_in <= dec_end
        ).first()
        
        if not existing_dec_res:
            customer = User.query.filter_by(role='customer').first()
            if not customer:
                customer = User(
                    email="customer@example.com",
                    first_name="Sarrah",
                    last_name="Khan",
                    role="customer",
                    is_verified=True
                )
                customer.set_password("customerpassword")
                db.session.add(customer)
                db.session.commit()
            
            marriott_room = Room.query.filter_by(hotel_id=marriott.id).first()
            if marriott_room:
                checkout_days = [25, 26, 27, 28, 25]
                for day in checkout_days:
                    nights = day - 22
                    res = Reservation(
                        user_id=customer.id,
                        room_id=marriott_room.id,
                        check_in=date(2026, 12, 22),
                        check_out=date(2026, 12, day),
                        total_amount=marriott_room.base_rate * nights,
                        status="Confirmed"
                    )
                    db.session.add(res)
                db.session.commit()
                print(f"[Database Seed] Seeded exactly 5 bookings with mixed checkout dates for Marriott room: {marriott_room.room_type}")

    # Seed November 2026 reservations for Four Seasons (3 reservations)
    fourseasons = Hotel.query.filter(Hotel.name.like("%Four Seasons%")).first()
    if fourseasons:
        nov_start = date(2026, 11, 1)
        nov_end = date(2026, 11, 30)
        fs_rooms = Room.query.filter_by(hotel_id=fourseasons.id).all()
        
        existing_fs_res = Reservation.query.join(Room).filter(
            Room.hotel_id == fourseasons.id,
            Reservation.check_in >= nov_start,
            Reservation.check_in <= nov_end
        ).first()
        
        if not existing_fs_res and len(fs_rooms) >= 3:
            customer = User.query.filter_by(role='customer').first()
            if not customer:
                customer = User(
                    email="customer@example.com",
                    first_name="Sarrah",
                    last_name="Khan",
                    role="customer",
                    is_verified=True
                )
                customer.set_password("customerpassword")
                db.session.add(customer)
                db.session.commit()
                
            bookings_data = [
                # Single Room
                (fs_rooms[0], date(2026, 11, 3), date(2026, 11, 6)),
                # Double Room
                (fs_rooms[1], date(2026, 11, 8), date(2026, 11, 12)),
                # Executive Suite
                (fs_rooms[2], date(2026, 11, 18), date(2026, 11, 22)),
            ]
            
            for room, check_in, check_out in bookings_data:
                nights = (check_out - check_in).days
                res = Reservation(
                    user_id=customer.id,
                    room_id=room.id,
                    check_in=check_in,
                    check_out=check_out,
                    total_amount=room.base_rate * nights,
                    status="Confirmed"
                )
                db.session.add(res)
            
            db.session.commit()
            print("[Database Seed] Exactly 3 reservations created for The Four Seasons London Park Lane.")

    # Seed Hyatt Regency Tokyo reservation (1 reservation)
    hyatt = Hotel.query.filter(Hotel.name.like("%Hyatt%")).first()
    if hyatt:
        hyatt_room = Room.query.filter_by(hotel_id=hyatt.id).first()
        if hyatt_room:
            existing_hyatt_res = Reservation.query.join(Room).filter(
                Room.hotel_id == hyatt.id,
                Reservation.status == 'Confirmed'
            ).first()
            if not existing_hyatt_res:
                customer = User.query.filter_by(role='customer').first()
                if customer:
                    res = Reservation(
                        user_id=customer.id,
                        room_id=hyatt_room.id,
                        check_in=date(2026, 11, 15),
                        check_out=date(2026, 11, 18),
                        total_amount=hyatt_room.base_rate * 3,
                        status="Confirmed"
                    )
                    db.session.add(res)
                    db.session.commit()
                    print("[Database Seed] 1 reservation created for The Hyatt Regency Tokyo.")


app = create_app()

if __name__ == '__main__':
    # Start local development server on port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
