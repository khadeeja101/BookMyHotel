from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

# Junction table representing the many-to-many relationship between Reservations and extra Services.
reservation_services = db.Table('reservation_services',
    db.Column('reservation_id', db.Integer, db.ForeignKey('reservations.id', ondelete='CASCADE'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model, UserMixin):
    """
    Represents users registered in the system. Can be either 'customer' or 'admin'.
    Inherits from UserMixin to support Flask-Login user sessions.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    # Role specifies authorization access: 'customer' or 'admin'
    role = db.Column(db.String(20), default='customer', nullable=False)
    # Email verification status. Users must verify their email to make bookings.
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    reservations = db.relationship('Reservation', backref='user', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Hashes the password before storing it in the database."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifies if the input password matches the stored hash."""
        return check_password_hash(self.password_hash, password)


class Hotel(db.Model):
    """
    Represents a hotel property. The system supports major brands
    (Marriott, Hilton, Hyatt, Four Seasons) in various locations.
    """
    __tablename__ = 'hotels'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=False)  # e.g., Dubai, London, Paris, Tokyo
    rating = db.Column(db.Integer, default=5, nullable=False)  # Star rating
    
    # Sustainability and Cleanliness Ratings
    sustainability_level = db.Column(db.Integer, default=3, nullable=False)  # Leaf badge score
    cleanliness_level = db.Column(db.Integer, default=5, nullable=False)  # Sanitized score
    
    # Work-friendly amenities
    wifi_speed = db.Column(db.Integer, default=100, nullable=False)  # Wi-Fi speed in Mbps
    home_office = db.Column(db.Boolean, default=True, nullable=False)  # Workspace setup
    
    image_url = db.Column(db.String(256), nullable=True)

    # Relationships
    rooms = db.relationship('Room', backref='hotel', lazy=True, cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='hotel', lazy=True, cascade="all, delete-orphan")
    promotions = db.relationship('Promotion', backref='hotel', lazy=True, cascade="all, delete-orphan")


class Room(db.Model):
    """
    Represents room categories in a hotel.
    Each room type has its base daily pricing and availability.
    """
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id', ondelete='CASCADE'), nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # e.g., 'Single', 'Double', 'Suite'
    base_rate = db.Column(db.Float, nullable=False)  # Price per night
    max_occupancy = db.Column(db.Integer, default=2, nullable=False)
    total_rooms = db.Column(db.Integer, default=10, nullable=False)
    available_rooms = db.Column(db.Integer, default=10, nullable=False)
    amenities = db.Column(db.String(256), nullable=True)  # Comma separated amenities
    description = db.Column(db.Text, nullable=True)

    # Relationships
    reservations = db.relationship('Reservation', backref='room', lazy=True)


class Service(db.Model):
    """
    Represents extra optional services.
    """
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)  # One-time service fee


class Reservation(db.Model):
    """
    Represents a guest reservation booking details.
    """
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id', ondelete='CASCADE'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    # Booking status can be: 'Confirmed' or 'Cancelled'
    status = db.Column(db.String(20), default='Confirmed', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    payments = db.relationship('Payment', backref='reservation', lazy=True, cascade="all, delete-orphan")
    services = db.relationship('Service', secondary=reservation_services, lazy='subquery',
                               backref=db.backref('reservations', lazy=True))


class Payment(db.Model):
    """
    Records payment processing transaction details.
    Tracks if transactions are Paid or Refunded (in case of cancellations).
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # e.g., 'Card', 'PayPal'
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Paid', nullable=False)  # 'Paid', 'Refunded'
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Promotion(db.Model):
    """
    Promotions and discount rules. Admins can specify codes and percentage discounts.
    """
    __tablename__ = 'promotions'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id', ondelete='CASCADE'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Coupon code
    discount_percent = db.Column(db.Float, nullable=False)  # e.g. 20 for 20% discount
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(256), nullable=True)


class Review(db.Model):
    """
    Customer ratings and feedback regarding hotel stays.
    """
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ContactMessage(db.Model):
    """
    Messages and inquiries sent from the contact/support form.
    """
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False)  # 'Pending', 'Resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class EmailVerification(db.Model):
    """
    Stores verification codes sent to users to verify their registration email.
    """
    __tablename__ = 'email_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)  # 6-digit pin code
    expires_at = db.Column(db.DateTime, nullable=False)
