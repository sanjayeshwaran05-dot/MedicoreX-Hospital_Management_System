
"""
Hospital Management System - Billing Routes
API Endpoints for Billing Management
"""

from flask import Blueprint, request, jsonify
from models.billing import Bill
from models.patient import Patient, AuditLog
from models.appointment import Appointment
from models.doctor import Doctor
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/api/v1/billing')


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


@billing_bp.route('/bills', methods=['GET'])
def get_bills():
    """Get all bills with pagination, search, and filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search')
        status = request.args.get('status')
        patient_id = request.args.get('patient_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        
        if start_date:
            from datetime import datetime
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            from datetime import datetime
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d')
        
        pagination = Bill.get_all(
            page=page,
            per_page=per_page,
            search=search,
            status=status,
            patient_id=patient_id,
            start_date=parsed_start,
            end_date=parsed_end
        )
        
        return jsonify({
            'bills': [bill.to_dict() for bill in pagination.items],
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


@billing_bp.route('/bills/<bill_id>', methods=['GET'])
def get_bill(bill_id):
    """Get a specific bill by ID"""
    try:
        bill = Bill.get_by_id(bill_id)
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        # Include patient and appointment details
        bill_dict = bill.to_dict()
        patient = Patient.get_by_id(bill.patient_id)
        
        bill_dict['patient'] = patient.to_dict() if patient else None
        
        if bill.appointment_id:
            appointment = Appointment.get_by_id(bill.appointment_id)
            if appointment:
                doctor = Doctor.get_by_id(appointment.doctor_id)
                bill_dict['appointment'] = {
                    'id': appointment.id,
                    'date': appointment.date.isoformat() if appointment.date else None,
                    'doctor': doctor.to_dict() if doctor else None
                }
        
        return jsonify({'bill': bill_dict}), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills', methods=['POST'])
@validate_json
def create_bill():
    """Create a new bill"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'items']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate items
        if not isinstance(data['items'], list) or len(data['items']) == 0:
            return jsonify({'error': 'At least one bill item is required'}), 400
        
        for item in data['items']:
            if 'description' not in item or 'amount' not in item:
                return jsonify({'error': 'Each item must have description and amount'}), 400
        
        # Verify patient exists
        patient = Patient.get_by_id(data['patient_id'])
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Verify appointment exists if provided
        if data.get('appointment_id'):
            appointment = Appointment.get_by_id(data['appointment_id'])
            if not appointment:
                return jsonify({'error': 'Appointment not found'}), 404
        
        bill = Bill.create(data, data['items'])
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='CREATE',
            entity_type='bill',
            entity_id=bill.id,
            new_data=bill.to_dict()
        )
        
        logger.info(f"Created new bill: {bill.id}")
        return jsonify({
            'message': 'Bill created successfully',
            'bill': bill.to_dict()
        }), 201
    except ValueError as e:
        return handle_error(e, 400, str(e))
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills/<bill_id>', methods=['PUT'])
@validate_json
def update_bill(bill_id):
    """Update bill information"""
    try:
        data = request.get_json()
        bill = Bill.get_by_id(bill_id)
        
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        # Cannot update paid bills
        if bill.status == 'paid':
            return jsonify({'error': 'Cannot update a paid bill'}), 400
        
        # Verify appointment exists if provided
        if data.get('appointment_id'):
            appointment = Appointment.get_by_id(data['appointment_id'])
            if not appointment:
                return jsonify({'error': 'Appointment not found'}), 404
        
        items_data = data.get('items')
        old_data = bill.to_dict()
        updated_bill = bill.update(data, items_data)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='UPDATE',
            entity_type='bill',
            entity_id=bill_id,
            old_data=old_data,
            new_data=updated_bill.to_dict()
        )
        
        logger.info(f"Updated bill: {bill_id}")
        return jsonify({
            'message': 'Bill updated successfully',
            'bill': updated_bill.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills/<bill_id>', methods=['DELETE'])
def delete_bill(bill_id):
    """Delete a bill"""
    try:
        bill = Bill.get_by_id(bill_id)
        
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        # Cannot delete paid bills
        if bill.status == 'paid':
            return jsonify({'error': 'Cannot delete a paid bill'}), 400
        
        old_data = bill.to_dict()
        bill.delete()
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='DELETE',
            entity_type='bill',
            entity_id=bill_id,
            old_data=old_data
        )
        
        logger.info(f"Deleted bill: {bill_id}")
        return jsonify({'message': 'Bill deleted successfully'}), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills/<bill_id>/pay', methods=['PATCH'])
@validate_json
def mark_bill_as_paid(bill_id):
    """Mark a bill as paid"""
    try:
        data = request.get_json()
        bill = Bill.get_by_id(bill_id)
        
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        if bill.status == 'paid':
            return jsonify({'error': 'Bill is already paid'}), 400
        
        payment_method = data.get('payment_method')
        valid_methods = ['cash', 'card', 'upi', 'insurance']
        
        if payment_method and payment_method not in valid_methods:
            return jsonify({
                'error': f'Invalid payment method. Must be one of: {", ".join(valid_methods)}'
            }), 400
        
        old_status = bill.status
        bill.mark_as_paid(payment_method)
        
        # Log audit
        AuditLog.log(
            user_id=None,
            action='MARK_PAID',
            entity_type='bill',
            entity_id=bill_id,
            old_data={'status': old_status},
            new_data={'status': 'paid', 'payment_method': payment_method}
        )
        
        logger.info(f"Marked bill as paid: {bill_id}")
        return jsonify({
            'message': 'Bill marked as paid successfully',
            'bill': bill.to_dict()
        }), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills/outstanding', methods=['GET'])
def get_outstanding_bills():
    """Get all outstanding (unpaid) bills"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Bill.get_all(
            page=page,
            per_page=per_page,
            status='pending'
        )
        
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


@billing_bp.route('/patients/<patient_id>/bills', methods=['GET'])
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


@billing_bp.route('/appointments/<appointment_id>/bill', methods=['GET'])
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


@billing_bp.route('/statistics', methods=['GET'])
def get_billing_statistics():
    """Get billing statistics"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        
        if start_date:
            from datetime import datetime
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            from datetime import datetime
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d')
        
        stats = Bill.get_statistics(start_date=parsed_start, end_date=parsed_end)
        return jsonify({'statistics': stats}), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/bills/<bill_id>/items', methods=['GET'])
def get_bill_items(bill_id):
    """Get items for a specific bill"""
    try:
        bill = Bill.get_by_id(bill_id)
        if not bill:
            return jsonify({'error': 'Bill not found'}), 404
        
        items = bill.get_items_summary()
        
        return jsonify({
            'bill_id': bill_id,
            'items': items,
            'total_amount': float(bill.total_amount)
        }), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/search', methods=['GET'])
def search_bills():
    """Search bills by various criteria"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        pagination = Bill.get_all(page=page, per_page=per_page, search=query)
        
        return jsonify({
            'bills': [bill.to_dict() for bill in pagination.items],
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


@billing_bp.route('/export', methods=['GET'])
def export_bills():
    """Export billing data"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        
        if start_date:
            from datetime import datetime
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d')
        
        if end_date:
            from datetime import datetime
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d')
        
        query = Bill.query
        
        if parsed_start:
            query = query.filter(Bill.date >= parsed_start)
        
        if parsed_end:
            query = query.filter(Bill.date <= parsed_end)
        
        bills = query.all()
        bill_data = [bill.to_dict() for bill in bills]
        
        return jsonify({
            'message': 'Billing data exported successfully',
            'total': len(bill_data),
            'bills': bill_data
        }), 200
    except Exception as e:
        return handle_error(e)


@billing_bp.route('/revenue-summary', methods=['GET'])
def get_revenue_summary():
    """Get revenue summary for dashboard"""
    try:
        stats = Bill.get_statistics()
        
        return jsonify({
            'total_revenue': stats['total_revenue'],
            'pending_amount': stats['pending_amount'],
            'paid_bills': stats['status_distribution']['paid'],
            'pending_bills': stats['status_distribution']['pending'],
            'partial_bills': stats['status_distribution']['partial'],
            'revenue_by_month': stats['revenue_by_month'][:6]  # Last 6 months
        }), 200
    except Exception as e:
        return handle_error(e)
