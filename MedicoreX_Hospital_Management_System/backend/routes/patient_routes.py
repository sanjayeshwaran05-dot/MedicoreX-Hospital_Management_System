
"""
Hospital Management System - Patient Routes
API Endpoints for Patient Management
"""

from flask import Blueprint, request, jsonify
from models.patient import Patient, AuditLog
from models.doctor import Doctor
from models.appointment import Appointment
from models.billing import Bill
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
patient_bp = Blueprint('patient', __name__, url_prefix='/api/v1/patients')


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


@patient_bp.route('', methods=['GET'])
def get_patients():
    """Get all patients with pagination and search"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search')
        
        pagination = Patient.get_all(page=page, per_page=per_page, search=search)
        
        return jsonify({
            'patients': [patient.to_dict() for patient in pagination.items],
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


@patient_bp.route('/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get a specific patient by ID"""
    try:
        patient = Patient.get_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        return jsonify({'patient': patient.to_dict()}), 200
    except Exception as e:
        return handle_error(e)


@patient_bp.route('', methods=['POST'])
@validate_json
def create_patient():
    """Create a new patient"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'age', 'gender', 'phone']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if phone number already exists
        existing_patient = Patient.get_by_phone(data['phone'])
        if existing_patient:
            return jsonify({'error': 'Patient with this phone number already exists'}), 400
        
        patient = Patient.create(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,  # Will be set after auth implementation
            action='CREATE',
            entity_type='patient',
            entity_id=patient.id,
            new_data=patient.to_dict()
        )
        
        logger.info(f"Created new patient: {patient.id}")
        return jsonify({
            'message': 'Patient created successfully',
            'patient': patient.to_dict()
        }), 201
    except ValueError as e:
        return handle_error(e, 400, str(e))
    except Exception as e:
        return handle_error(e)


@patient_bp.route('/<patient_id>', methods=['PUT'])
@validate_json
def update_patient(patient_id):
    """Update patient information"""
    try:
        data = request.get_json()
        patient = Patient.get_by_id(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if phone number is being changed and already exists
        if 'phone' in data and data['phone'] != patient.phone:
            existing_patient = Patient.get_by_phone(data['phone'])
            if existing_patient:
                return jsonify({'error': 'Patient with this phone number already exists'}), 400
        
        old_data = patient.to_dict()
        updated_patient = patient.update(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='UPDATE',
            entity_type='patient',
            entity_id=patient.id,
            old_data=old_data,
            new_data=updated_patient.to_dict()
        )
        
        logger.info(f"Updated patient: {patient.id}")
        return jsonify({
            'message': 'Patient updated successfully',
            'patient': updated_patient.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@patient_bp.route('/<patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    """Delete a patient"""
    try:
        patient = Patient.get_by_id(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Check if patient has appointments or bills
        appointments = Appointment.query.filter_by(patient_id=patient_id).count()
        bills = Bill.query.filter_by(patient_id=patient_id).count()
        
        if appointments > 0 or bills > 0:
            return jsonify({
                'error': 'Cannot delete patient with existing appointments or bills',
                'details': {
                    'appointments': appointments,
                    'bills': bills
                }
            }), 400
        
        old_data = patient.to_dict()
        patient.delete()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='DELETE',
            entity_type='patient',
            entity_id=patient_id,
            old_data=old_data
        )
        
        logger.info(f"Deleted patient: {patient_id}")
        return jsonify({'message': 'Patient deleted successfully'}), 200
    except Exception as e:
        return handle_error(e)


@patient_bp.route('/<patient_id>/appointments', methods=['GET'])
def get_patient_appointments(patient_id):
    """Get all appointments for a specific patient"""
    try:
        patient = Patient.get_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Appointment.get_by_patient(patient_id, page=page, per_page=per_page)
        
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


@patient_bp.route('/<patient_id>/bills', methods=['GET'])
def get_patient_bills(patient_id):
    """Get all bills for a specific patient"""
    try:
        patient = Patient.get_by_id(patient_id)
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Bill.get_by_patient(patient_id, page=page, per_page=per_page)
        
        return jsonify({
            'bills': [bill.to_dict() for bill in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total
            }
        }), 200
    except Exception as e:
        return handle_error(e)


@patient_bp.route('/statistics', methods=['GET'])
def get_patient_statistics():
    """Get patient statistics"""
    try:
        stats = Patient.get_statistics()
        return jsonify({'statistics': stats}), 200
    except Exception as e:
        return handle_error(e)


@patient_bp.route('/search', methods=['GET'])
def search_patients():
    """Search patients by various criteria"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Patient.get_all(page=page, per_page=per_page, search=query)
        
        return jsonify({
            'patients': [patient.to_dict() for patient in pagination.items],
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


@patient_bp.route('/export', methods=['GET'])
def export_patients():
    """Export patient data"""
    try:
        patients = Patient.query.all()
        patient_data = [patient.to_dict() for patient in patients]
        
        return jsonify({
            'message': 'Patient data exported successfully',
            'total': len(patient_data),
            'patients': patient_data
        }), 200
    except Exception as e:
        return handle_error(e)
