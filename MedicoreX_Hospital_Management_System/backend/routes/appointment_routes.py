
"""
Hospital Management System - Appointment Routes
API Endpoints for Appointment Management
"""

from flask import Blueprint, request, jsonify
from models.appointment import Appointment
from models.patient import Patient, AuditLog
from models.doctor import Doctor
from models.billing import Bill
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
appointment_bp = Blueprint('appointment', __name__, url_prefix='/api/v1/appointments')


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


@appointment_bp.route('', methods=['GET'])
def get_appointments():
    """Get all appointments with pagination, search, and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search')
        status = request.args.get('status')
        date = request.args.get('date')
        doctor_id = request.args.get('doctor_id')
        patient_id = request.args.get('patient_id')
        
        # Parse date if provided
        parsed_date = None
        if date:
            from datetime import datetime
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        pagination = Appointment.get_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            date=parsed_date,
            doctor_id=doctor_id,
            patient_id=patient_id
        )
        
        return jsonify({
            'appointments': [apt.to_dict() for apt in pagination.items],
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


@appointment_bp.route('/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get a specific appointment by ID"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # Include patient and doctor details
        appointment_dict = appointment.to_dict()
        patient = Patient.get_by_id(appointment.patient_id)
        doctor = Doctor.get_by_id(appointment.doctor_id)
        
        appointment_dict['patient'] = patient.to_dict() if patient else None
        appointment_dict['doctor'] = doctor.to_dict() if doctor else None
        
        return jsonify({'appointment': appointment_dict}), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('', methods=['POST'])
@validate_json
def create_appointment():
    """Create a new appointment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'doctor_id', 'date', 'time', 'reason']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Verify patient exists
        patient = Patient.get_by_id(data['patient_id'])
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Verify doctor exists and is active
        doctor = Doctor.get_by_id(data['doctor_id'])
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        if doctor.status != 'Active':
            return jsonify({'error': 'Doctor is not available for appointments'}), 400
        
        # Check availability
        from datetime import datetime
        appointment_date = datetime.strptime(data['date'], '%Y-%m-%d').date() if isinstance(data['date'], str) else data['date']
        
        if not Appointment.check_availability(data['doctor_id'], appointment_date, data['time']):
            return jsonify({
                'error': 'Doctor is not available at the specified date and time'
            }), 400
        
        appointment = Appointment.create(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='CREATE',
            entity_type='appointment',
            entity_id=appointment.id,
            new_data=appointment.to_dict()
        )
        
        logger.info(f"Created new appointment: {appointment.id}")
        return jsonify({
            'message': 'Appointment booked successfully',
            'appointment': appointment.to_dict()
        }), 201
    except ValueError as e:
        return handle_error(e, 400, str(e))
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>', methods=['PUT'])
@validate_json
def update_appointment(appointment_id):
    """Update appointment information"""
    try:
        data = request.get_json()
        appointment = Appointment.get_by_id(appointment_id)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # If changing date/time or doctor, check availability
        if 'date' in data or 'time' in data or 'doctor_id' in data:
            new_date = data.get('date', appointment.date)
            new_time = data.get('time', appointment.time)
            new_doctor = data.get('doctor_id', appointment.doctor_id)
            
            # Parse date if string
            from datetime import datetime
            if isinstance(new_date, str):
                new_date = datetime.strptime(new_date, '%Y-%m-%d').date()
            
            if not Appointment.check_availability(new_doctor, new_date, new_time):
                return jsonify({
                    'error': 'Requested time slot is not available'
                }), 400
        
        old_data = appointment.to_dict()
        updated_appointment = appointment.update(data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='UPDATE',
            entity_type='appointment',
            entity_id=appointment_id,
            old_data=old_data,
            new_data=updated_appointment.to_dict()
        )
        
        logger.info(f"Updated appointment: {appointment_id}")
        return jsonify({
            'message': 'Appointment updated successfully',
            'appointment': updated_appointment.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Delete an appointment"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        # Check if appointment has bills
        bills = Bill.query.filter_by(appointment_id=appointment_id).count()
        if bills > 0:
            return jsonify({
                'error': 'Cannot delete appointment with existing bills',
                'details': {'bills': bills}
            }), 400
        
        old_data = appointment.to_dict()
        appointment.delete()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='DELETE',
            entity_type='appointment',
            entity_id=appointment_id,
            old_data=old_data
        )
        
        logger.info(f"Deleted appointment: {appointment_id}")
        return jsonify({'message': 'Appointment deleted successfully'}), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>/confirm', methods=['PATCH'])
def confirm_appointment(appointment_id):
    """Confirm an appointment"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        if appointment.status == 'confirmed':
            return jsonify({'error': 'Appointment is already confirmed'}), 400
        
        if appointment.status == 'cancelled':
            return jsonify({'error': 'Cannot confirm a cancelled appointment'}), 400
        
        appointment.confirm()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='CONFIRM',
            entity_type='appointment',
            entity_id=appointment_id,
            old_data={'status': 'pending'},
            new_data={'status': 'confirmed'}
        )
        
        logger.info(f"Confirmed appointment: {appointment_id}")
        return jsonify({
            'message': 'Appointment confirmed successfully',
            'appointment': appointment.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>/cancel', methods=['PATCH'])
def cancel_appointment(appointment_id):
    """Cancel an appointment"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        if appointment.status == 'cancelled':
            return jsonify({'error': 'Appointment is already cancelled'}), 400
        
        if appointment.status == 'completed':
            return jsonify({'error': 'Cannot cancel a completed appointment'}), 400
        
        appointment.cancel()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='CANCEL',
            entity_type='appointment',
            entity_id=appointment_id,
            old_data={'status': appointment.status},
            new_data={'status': 'cancelled'}
        )
        
        logger.info(f"Cancelled appointment: {appointment_id}")
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': appointment.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>/complete', methods=['PATCH'])
def complete_appointment(appointment_id):
    """Mark an appointment as completed"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        if appointment.status == 'completed':
            return jsonify({'error': 'Appointment is already completed'}), 400
        
        if appointment.status == 'cancelled':
            return jsonify({'error': 'Cannot complete a cancelled appointment'}), 400
        
        appointment.complete()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='COMPLETE',
            entity_type='appointment',
            entity_id=appointment_id,
            old_data={'status': appointment.status},
            new_data={'status': 'completed'}
        )
        
        logger.info(f"Completed appointment: {appointment_id}")
        return jsonify({
            'message': 'Appointment marked as completed',
            'appointment': appointment.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/<appointment_id>/bill', methods=['GET'])
def get_appointment_bill(appointment_id):
    """Get bill for a specific appointment"""
    try:
        appointment = Appointment.get_by_id(appointment_id)
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        bill = Bill.get_by_appointment(appointment_id)
        
        if not bill:
            return jsonify({
                'message': 'No bill found for this appointment',
                'bill': None
            }), 200
        
        return jsonify({'bill': bill.to_dict()}), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/check-availability', methods=['GET'])
def check_availability():
    """Check doctor availability for a specific date and time"""
    try:
        doctor_id = request.args.get('doctor_id')
        date = request.args.get('date')
        time = request.args.get('time')
        
        if not all([doctor_id, date, time]):
            return jsonify({
                'error': 'doctor_id, date, and time are required'
            }), 400
        
        # Verify doctor exists
        doctor = Doctor.get_by_id(doctor_id)
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        if doctor.status != 'Active':
            return jsonify({
                'available': False,
                'reason': 'Doctor is not active'
            }), 200
        
        from datetime import datetime
        parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
        
        is_available = Appointment.check_availability(doctor_id, parsed_date, time)
        
        return jsonify({
            'available': is_available,
            'doctor_id': doctor_id,
            'date': date,
            'time': time
        }), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/statistics', methods=['GET'])
def get_appointment_statistics():
    """Get appointment statistics"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        
        if start_date:
            from datetime import datetime
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if end_date:
            from datetime import datetime
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        stats = Appointment.get_statistics(start_date=parsed_start, end_date=parsed_end)
        return jsonify({'statistics': stats}), 200
    except Exception as e:
        return handle_error(e)


@appointment_bp.route('/search', methods=['GET'])
def search_appointments():
    """Search appointments by various criteria"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Appointment.get_all(page=page, per_page=per_page, search=query)
        
        return jsonify({
            'appointments': [apt.to_dict() for apt in pagination.items],
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
