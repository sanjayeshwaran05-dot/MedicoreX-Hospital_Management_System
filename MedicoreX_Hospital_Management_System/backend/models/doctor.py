
"""
Hospital Management System - Doctor Model
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Import db from patient model to avoid circular imports
from models.patient import db


class Doctor(db.Model):
    """Doctor Model"""
    __tablename__ = 'doctors'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100), nullable=False, index=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    qualification = db.Column(db.String(100), nullable=False)
    consultation_fee = db.Column(db.Decimal(10, 2), nullable=False)
    status = db.Column(db.Enum('Active', 'On Leave', 'Inactive'), default='Active', index=True)
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='doctor', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Doctor {self.id} - {self.name} ({self.specialization})>'
    
    def to_dict(self):
        """Convert doctor object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'specialization': self.specialization,
            'phone': self.phone,
            'email': self.email,
            'experience': self.experience,
            'qualification': self.qualification,
            'consultation_fee': float(self.consultation_fee) if self.consultation_fee else 0,
            'status': self.status,
            'address': self.address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def create(data):
        """Create a new doctor"""
        # Generate doctor ID if not provided
        if 'id' not in data or not data['id']:
            last_doctor = Doctor.query.order_by(Doctor.id.desc()).first()
            if last_doctor:
                last_num = int(last_doctor.id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            data['id'] = f'D{str(new_num).zfill(4)}'
        
        doctor = Doctor(
            id=data['id'],
            name=data['name'],
            specialization=data['specialization'],
            phone=data['phone'],
            email=data['email'],
            experience=data['experience'],
            qualification=data['qualification'],
            consultation_fee=data['consultation_fee'],
            status=data.get('status', 'Active'),
            address=data.get('address')
        )
        
        db.session.add(doctor)
        db.session.commit()
        return doctor
    
    def update(self, data):
        """Update doctor information"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete doctor"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_all(page=1, per_page=20, search=None, specialization=None, status=None):
        """Get all doctors with optional pagination, search, and filters"""
        query = Doctor.query
        
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    Doctor.name.like(search_term),
                    Doctor.id.like(search_term),
                    Doctor.specialization.like(search_term),
                    Doctor.email.like(search_term)
                )
            )
        
        if specialization:
            query = query.filter_by(specialization=specialization)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(Doctor.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_by_id(doctor_id):
        """Get doctor by ID"""
        return Doctor.query.get(doctor_id)
    
    @staticmethod
    def get_by_email(email):
        """Get doctor by email"""
        return Doctor.query.filter_by(email=email).first()
    
    @staticmethod
    def get_by_specialization(specialization):
        """Get doctors by specialization"""
        return Doctor.query.filter_by(specialization=specialization).all()
    
    @staticmethod
    def get_active_doctors():
        """Get all active doctors"""
        return Doctor.query.filter_by(status='Active').all()
    
    @staticmethod
    def get_specializations():
        """Get list of all specializations"""
        specializations = db.session.query(
            Doctor.specialization,
            db.func.count(Doctor.id).label('count')
        ).group_by(Doctor.specialization).all()
        
        return [{'specialization': spec[0], 'count': spec[1]} for spec in specializations]
    
    @staticmethod
    def get_statistics():
        """Get doctor statistics"""
        total_doctors = Doctor.query.count()
        active_doctors = Doctor.query.filter_by(status='Active').count()
        
        # Doctors by status
        status_distribution = {
            'Active': Doctor.query.filter_by(status='Active').count(),
            'On Leave': Doctor.query.filter_by(status='On Leave').count(),
            'Inactive': Doctor.query.filter_by(status='Inactive').count()
        }
        
        # Average consultation fee
        avg_fee = db.session.query(db.func.avg(Doctor.consultation_fee)).scalar() or 0
        
        # Top specializations
        top_specializations = Doctor.get_specializations()
        top_specializations.sort(key=lambda x: x['count'], reverse=True)
        top_specializations = top_specializations[:10]
        
        return {
            'total_doctors': total_doctors,
            'active_doctors': active_doctors,
            'status_distribution': status_distribution,
            'average_consultation_fee': float(avg_fee),
            'top_specializations': top_specializations
        }
    
    def get_performance(self):
        """Get doctor performance statistics"""
        total_appointments = len(self.appointments)
        completed_appointments = len([apt for apt in self.appointments if apt.status == 'completed'])
        
        # Calculate revenue from appointments
        revenue = 0
        for apt in self.appointments:
            for bill in apt.bills:
                revenue += float(bill.total_amount) if bill.total_amount else 0
        
        return {
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'completion_rate': (completed_appointments / total_appointments * 100) if total_appointments > 0 else 0,
            'total_revenue': revenue
        }
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
