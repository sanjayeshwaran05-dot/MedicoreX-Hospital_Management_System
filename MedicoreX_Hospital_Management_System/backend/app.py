
"""
AngalaEswari Hospital Management System - Main Application
Flask Backend Server
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
import logging
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, resources={
    r"/api/*": {
        "origins": app.config['CORS_ORIGINS'],
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize database
from models.patient import db
migrate = Migrate(app, db)

# Initialize logging
logging.basicConfig(
    level=app.config['LOG_LEVEL'],
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[
        logging.FileHandler(app.config['LOG_FILE']),
        logging.StreamHandler()
    ]
)(venv)

logger = logging.getLogger(__name__)

# Import models
from models.patient import Patient, AuditLog
from models.doctor import Doctor
from models.appointment import Appointment
from models.billing import Bill, BillItem

# Import routes
from routes.patient_routes import patient_bp
from routes.doctor_routes import doctor_bp
from routes.appointment_routes import appointment_bp
from routes.billing_routes import billing_bp

# Register blueprints
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(appointment_bp)
app.register_blueprint(billing_bp)


# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'service': 'AngalaEswari Hospital Management System API',
            'database': 'connected'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


# Root endpoint
@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Welcome to AngalaEswari Hospital Management System API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/api/health',
            'patients': '/api/v1/patients',
            'doctors': '/api/v1/doctors',
            'appointments': '/api/v1/appointments',
            'billing': '/api/v1/billing'
        },
        'documentation': '/api/docs'
    }), 200


# API documentation endpoint
@app.route('/api/docs', methods=['GET'])
def api_docs():
    """API documentation endpoint"""
    docs = {
        'title': 'AngalaEswari Hospital Management System API',
        'version': '1.0.0',
        'description': 'RESTful API for managing hospital operations',
        'base_url': '/api/v1',
        'endpoints': {
            'patients': {
                'GET /api/v1/patients': 'Get all patients with pagination',
                'GET /api/v1/patients/<id>': 'Get a specific patient',
                'POST /api/v1/patients': 'Create a new patient',
                'PUT /api/v1/patients/<id>': 'Update a patient',
                'DELETE /api/v1/patients/<id>': 'Delete a patient',
                'GET /api/v1/patients/<id>/appointments': 'Get patient appointments',
                'GET /api/v1/patients/<id>/bills': 'Get patient bills',
                'GET /api/v1/patients/statistics': 'Get patient statistics'
            },
            'doctors': {
                'GET /api/v1/doctors': 'Get all doctors with pagination',
                'GET /api/v1/doctors/active': 'Get active doctors',
                'GET /api/v1/doctors/<id>': 'Get a specific doctor',
                'GET /api/v1/doctors/<id>/performance': 'Get doctor performance',
                'POST /api/v1/doctors': 'Create a new doctor',
                'PUT /api/v1/doctors/<id>': 'Update a doctor',
                'DELETE /api/v1/doctors/<id>': 'Delete a doctor',
                'GET /api/v1/doctors/<id>/appointments': 'Get doctor appointments',
                'GET /api/v1/doctors/specializations': 'Get specializations'
            },
            'appointments': {
                'GET /api/v1/appointments': 'Get all appointments with pagination',
                'GET /api/v1/appointments/<id>': 'Get a specific appointment',
                'POST /api/v1/appointments': 'Create a new appointment',
                'PUT /api/v1/appointments/<id>': 'Update an appointment',
                'DELETE /api/v1/appointments/<id>': 'Delete an appointment',
                'PATCH /api/v1/appointments/<id>/confirm': 'Confirm appointment',
                'PATCH /api/v1/appointments/<id>/cancel': 'Cancel appointment',
                'PATCH /api/v1/appointments/<id>/complete': 'Complete appointment',
                'GET /api/v1/appointments/check-availability': 'Check doctor availability'
            },
            'billing': {
                'GET /api/v1/billing/bills': 'Get all bills with pagination',
                'GET /api/v1/billing/bills/<id>': 'Get a specific bill',
                'POST /api/v1/billing/bills': 'Create a new bill',
                'PUT /api/v1/billing/bills/<id>': 'Update a bill',
                'DELETE /api/v1/billing/bills/<id>': 'Delete a bill',
                'PATCH /api/v1/billing/bills/<id>/pay': 'Mark bill as paid',
                'GET /api/v1/billing/bills/outstanding': 'Get outstanding bills',
                'GET /api/v1/billing/statistics': 'Get billing statistics',
                'GET /api/v1/billing/revenue-summary': 'Get revenue summary'
            }
        },
        'response_formats': {
            'success': {'status': 'success', 'data': {...}},
            'error': {'error': 'Error message', 'details': 'Detailed information'}
        }
    }
    return jsonify(docs), 200


# Dashboard statistics endpoint
@app.route('/api/v1/dashboard/statistics', methods=['GET'])
def dashboard_statistics():
    """Get overall dashboard statistics"""
    try:
        # Patient statistics
        total_patients = Patient.query.count()
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_patients = Patient.query.filter(Patient.created_at >= thirty_days_ago).count()
        
        # Doctor statistics
        total_doctors = Doctor.query.count()
        active_doctors = Doctor.query.filter_by(status='Active').count()
        
        # Appointment statistics
        total_appointments = Appointment.query.count()
        today_appointments = Appointment.query.filter(
            Appointment.date == datetime.utcnow().date()
        ).count()
        
        # Billing statistics
        total_revenue = db.session.query(db.func.sum(Bill.total_amount)).filter(
            Bill.status == 'paid'
        ).scalar() or 0
        pending_bills = Bill.query.filter(Bill.status.in_(['pending', 'partial'])).count()
        
        return jsonify({
            'patients': {
                'total': total_patients,
                'new_this_month': new_patients
            },
            'doctors': {
                'total': total_doctors,
                'active': active_doctors
            },
            'appointments': {
                'total': total_appointments,
                'today': today_appointments
            },
            'billing': {
                'total_revenue': float(total_revenue),
                'pending_bills': pending_bills
            },
            'last_updated': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error fetching dashboard statistics: {str(e)}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Resource not found',
        'status': 404,
        'message': 'The requested resource was not found on this server'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'status': 500,
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'status': 405,
        'message': 'The method is not allowed for the requested URL'
    }), 405


# Request logging middleware
@app.before_request
def log_request_info():
    """Log incoming requests"""
    logger.info(f"{request.method} {request.path} - {request.remote_addr}")


@app.after_request
def log_response_info(response):
    """Log outgoing responses"""
    logger.info(f"{request.method} {request.path} - Status: {response.status_code}")
    return response


# Initialize database
def init_db():
    """Initialize the database"""
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            
            # Check if default admin exists
            from sqlalchemy import text
            result = db.session.execute(text("SELECT COUNT(*) FROM users")).scalar()
            if result == 0:
                logger.info("Creating default admin user")
                # Default admin will be created by SQL script
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise


# CLI commands
@app.cli.command()
def init():
    """Initialize the application"""
    init_db()
    logger.info("Application initialized successfully")


@app.cli.command()
def reset_db():
    """Reset the database"""
    db.drop_all()
    db.create_all()
    logger.info("Database reset successfully")


@app.cli.command()
def seed_data():
    """Seed the database with sample data"""
    logger.info("Seeding database with sample data...")
    # Sample data will be loaded from SQL script
    logger.info("Sample data seeded successfully")


if __name__ == '__main__':
    # Initialize configuration
    Config.init_app(app)
    
    # Initialize database
    init_db()
    
    # Run the application
    logger.info("Starting AngalaEswari Hospital Management System API Server...")
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config['DEBUG']
    )

