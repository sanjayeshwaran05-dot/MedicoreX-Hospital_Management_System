
"""
Hospital Management System - Doctor Routes
API Endpoints for Doctor Management
"""

from flask import Blueprint, request, jsonify
from models.doctor import Doctor
from models.patient import AuditLog
from models.appointment import Appointment
from models.billing import Bill
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
doctor_bp = Blueprint('doctor', __name__, url_prefix='/api/v1/doctors')


def validate_json(f):
    """Decorator to validate JSON request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function


def handle_error(e, status_code=500, message='An error occurred'):
    """Handle errors consistently"""
    logger.error(f"Error: {str(e)}")
    return jsonify({
        'error': message,
        'details': str(e) if request.args.get('debug') else None
    }), status_code


@doctor_bp.route('', methods=['GET'])
def get_doctors():
    """Get all doctors with pagination, search, and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search')
        specialization = request.args.get('specialization')
        status = request.args.get('status')
        
        pagination = Doctor.get_all(
            page=page,
            per_page=per_page,
            search=search,
            specialization=specialization,
            status=status
        )
        
        return jsonify({
            'doctors': [doctor.to_dict() for doctor in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/active', methods=['GET'])
def get_active_doctors():
    """Get all active doctors"""
    try:
        doctors = Doctor.get_active_doctors()
        return jsonify({
            'doctors': [doctor.to_dict() for doctor in doctors],
            'total': len(doctors)
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>', methods=['GET'])
def get_doctor(doctor_id):
    """Get a specific doctor by ID"""
    try:
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        return jsonify({'doctor': doctor.to_dict()}), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>/performance', methods=['GET'])
def get_doctor_performance(doctor_id):
    """Get doctor performance statistics"""
    try:
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        performance = doctor.get_performance()
        return jsonify({
            'doctor_id': doctor_id,
            'performance': performance
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('', methods=['POST'])
@validate_json
def create_doctor():
    """Create a new doctor"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'specialization', 'phone', 'email', 'experience', 'qualification', 'consultation_fee']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if email already exists
        existing_doctor = Doctor.get_by_email(data['email'])
        if existing_doctor:
            return jsonify({'error': 'Doctor with this email already exists'}), 400
        
        doctor = Doctor.create(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='CREATE',
            entity_type='doctor',
            entity_id=doctor.id,
            new_data=doctor.to_dict()
        )
        
        logger.info(f"Created new doctor: {doctor.id}")
        return jsonify({
            'message': 'Doctor created successfully',
            'doctor': doctor.to_dict()
        }), 201
    except ValueError as e:
        return handle_error(e, 400, str(e))
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>', methods=['PUT'])
@validate_json
def update_doctor(doctor_id):
    """Update doctor information"""
    try:
        data = request.get_json()
        doctor = Doctor.get_by_id(doctor_id)
        
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        # Check if email is being changed and already exists
        if 'email' in data and data['email'] != doctor.email:
            existing_doctor = Doctor.get_by_email(data['email'])
            if existing_doctor:
                return jsonify({'error': 'Doctor with this email already exists'}), 400
        
        old_data = doctor.to_dict()
        updated_doctor = doctor.update(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='UPDATE',
            entity_type='doctor',
            entity_id=doctor_id,
            old_data=old_data,
            new_data=updated_doctor.to_dict()
        )
        
        logger.info(f"Updated doctor: {doctor_id}")
        return jsonify({
            'message': 'Doctor updated successfully',
            'doctor': updated_doctor.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    """Delete a doctor"""
    try:
        doctor = Doctor.get_by_id(doctor_id)
        
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        # Check if doctor has appointments
        appointments = Appointment.query.filter_by(doctor_id=doctor_id).count()
        if appointments > 0:
            return jsonify({
                'error': 'Cannot delete doctor with existing appointments',
                'details': {'appointments': appointments}
            }), 400
        
        old_data = doctor.to_dict()
        doctor.delete()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='DELETE',
            entity_type='doctor',
            entity_id=doctor_id,
            old_data=old_data
        )
        
        logger.info(f"Deleted doctor: {doctor_id}")
        return jsonify({'message': 'Doctor deleted successfully'}), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>/appointments', methods=['GET'])
def get_doctor_appointments(doctor_id):
    """Get all appointments for a specific doctor"""
    try:
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Appointment.get_by_doctor(doctor_id, page=page, per_page=per_page)
        
        return jsonify({
            'appointments': [apt.to_dict() for apt in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total
            }
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>/upcoming', methods=['GET'])
def get_doctor_upcoming_appointments(doctor_id):
    """Get upcoming appointments for a specific doctor"""
    try:
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        appointments = Appointment.get_upcoming_appointments(doctor_id=doctor_id)
        
        return jsonify({
            'appointments': [apt.to_dict() for apt in appointments],
            'total': len(appointments)
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/specializations', methods=['GET'])
def get_specializations():
    """Get list of all specializations"""
    try:
        specializations = Doctor.get_specializations()
        return jsonify({
            'specializations': specializations,
            'total': len(specializations)
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/by-specialization/<specialization>', methods=['GET'])
def get_doctors_by_specialization(specialization):
    """Get doctors by specialization"""
    try:
        doctors = Doctor.get_by_specialization(specialization)
        return jsonify({
            'specialization': specialization,
            'doctors': [doctor.to_dict() for doctor in doctors],
            'total': len(doctors)
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/statistics', methods=['GET'])
def get_doctor_statistics():
    """Get doctor statistics"""
    try:
        stats = Doctor.get_statistics()
        return jsonify({'statistics': stats}), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/search', methods=['GET'])
def search_doctors():
    """Search doctors by various criteria"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Doctor.get_all(page=page, per_page=per_page, search=query)
        
        return jsonify({
            'doctors': [doctor.to_dict() for doctor in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total
            },
            'query': query
        }), 200
    except Exception as e:
        return handle_error(e)


@doctor_bp.route('/<doctor_id>/status', methods=['PATCH'])
@validate_json
def update_doctor_status(doctor_id):
    """Update doctor status"""
    try:
        data = request.get_json()
        if 'status' not in data:
            return jsonify({'error': 'status is required'}), 400
        
        valid_statuses = ['Active', 'On Leave', 'Inactive']
        if data['status'] not in valid_statuses:
            return jsonify({
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        old_status = doctor.status
        doctor.update({'status': data['status']})
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='UPDATE_STATUS',
            entity_type='doctor',
            entity_id=doctor_id,
            old_data={'status': old_status},
            new_data={'status': data['status']}
        )
        
        logger.info(f"Updated doctor status: {doctor_id} from {old_status} to {data['status']}")
        return jsonify({
            'message': 'Doctor status updated successfully',
            'doctor': doctor.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)
