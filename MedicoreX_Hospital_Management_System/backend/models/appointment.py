
"""
Hospital Management System - Appointment Model
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from models.patient import db


class Appointment(db.Model):
    """Appointment Model"""
    __tablename__ = 'appointments'
    
    id = db.Column(db.String(50), primary_key=True)
    patient_id = db.Column(db.String(50), db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.String(50), db.ForeignKey('doctors.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum('pending', 'confirmed', 'completed', 'cancelled'),
        default='pending',
        nullable=False,
        index=True
    )
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    bills = db.relationship('Bill', backref='appointment', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.patient_id} with {self.doctor_id} on {self.date}>'
    
    def to_dict(self):
        """Convert appointment object to dictionary"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.strftime('%H:%M') if self.time else None,
            'reason': self.reason,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def create(data):
        """Create a new appointment"""
        # Generate appointment ID if not provided
        if 'id' not in data or not data['id']:
            last_appointment = Appointment.query.order_by(Appointment.id.desc()).first()
            if last_appointment:
                last_num = int(last_appointment.id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            data['id'] = f'A{str(new_num).zfill(4)}'
        
        appointment = Appointment(
            id=data['id'],
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date() if isinstance(data['date'], str) else data['date'],
            time=datetime.strptime(data['time'], '%H:%M').time() if isinstance(data['time'], str) else data['time'],
            reason=data['reason'],
            status=data.get('status', 'pending'),
            notes=data.get('notes')
        )
        
        db.session.add(appointment)
        db.session.commit()
        return appointment
    
    def update(self, data):
        """Update appointment information"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at', 'patient_id', 'doctor_id']:
                if key in ['date', 'time']:
                    if isinstance(value, str):
                        if key == 'date':
                            setattr(self, key, datetime.strptime(value, '%Y-%m-%d').date())
                        elif key == 'time':
                            setattr(self, key, datetime.strptime(value, '%H:%M').time())
                    else:
                        setattr(self, key, value)
                else:
                    setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete appointment"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_all(page=1, per_page=20, search=None, status=None, date=None, doctor_id=None, patient_id=None):
        """Get all appointments with optional pagination, search, and filters"""
        query = Appointment.query
        
        if search:
            # Search by patient name or doctor name
            from models.patient import Patient
            from models.doctor import Doctor
            search_term = f'%{search}%'
            
            patient_ids = [p.id for p in Patient.query.filter(Patient.name.like(search_term)).all()]
            doctor_ids = [d.id for d in Doctor.query.filter(Doctor.name.like(search_term)).all()]
            
            query = query.filter(
                db.or_(
                    Appointment.id.like(search_term),
                    Appointment.patient_id.in_(patient_ids),
                    Appointment.doctor_id.in_(doctor_ids)
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        
        if date:
            query = query.filter_by(date=date)
        
        if doctor_id:
            query = query.filter_by(doctor_id=doctor_id)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        return query.order_by(Appointment.date.desc(), Appointment.time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_by_id(appointment_id):
        """Get appointment by ID"""
        return Appointment.query.get(appointment_id)
    
    @staticmethod
    def get_by_patient(patient_id, page=1, per_page=20):
        """Get appointments by patient"""
        return Appointment.query.filter_by(patient_id=patient_id).order_by(
            Appointment.date.desc(), Appointment.time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_by_doctor(doctor_id, page=1, per_page=20):
        """Get appointments by doctor"""
        return Appointment.query.filter_by(doctor_id=doctor_id).order_by(
            Appointment.date.desc(), Appointment.time.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_by_date(date):
        """Get appointments for a specific date"""
        return Appointment.query.filter_by(date=date).order_by(Appointment.time).all()
    
    @staticmethod
    def get_upcoming_appointments(doctor_id=None, patient_id=None):
        """Get upcoming appointments"""
        from datetime import date
        query = Appointment.query.filter(Appointment.date >= date.today())
        
        if doctor_id:
            query = query.filter_by(doctor_id=doctor_id)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        return query.filter(
            Appointment.status.in_(['pending', 'confirmed'])
        ).order_by(Appointment.date, Appointment.time).all()
    
    @staticmethod
    def check_availability(doctor_id, date, time):
        """Check if doctor is available at given date and time"""
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date,
            time=time
        ).filter(
            Appointment.status.in_(['pending', 'confirmed'])
        ).first()
        
        return existing is None
    
    @staticmethod
    def get_statistics(start_date=None, end_date=None):
        """Get appointment statistics"""
        query = Appointment.query
        
        if start_date:
            query = query.filter(Appointment.date >= start_date)
        
        if end_date:
            query = query.filter(Appointment.date <= end_date)
        
        total_appointments = query.count()
        
        status_counts = {
            'pending': query.filter_by(status='pending').count(),
            'confirmed': query.filter_by(status='confirmed').count(),
            'completed': query.filter_by(status='completed').count(),
            'cancelled': query.filter_by(status='cancelled').count()
        }
        
        # Appointments by date (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
        appointments_by_date = db.session.query(
            Appointment.date,
            db.func.count(Appointment.id).label('count')
        ).filter(
            Appointment.date >= thirty_days_ago
        ).group_by(Appointment.date).all()
        
        return {
            'total_appointments': total_appointments,
            'status_distribution': status_counts,
            'appointments_by_date': [
                {'date': str(apt[0]), 'count': apt[1]} 
                for apt in appointments_by_date
            ]
        }
    
    def cancel(self):
        """Cancel appointment"""
        self.status = 'cancelled'
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def confirm(self):
        """Confirm appointment"""
        self.status = 'confirmed'
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def complete(self):
        """Mark appointment as completed"""
        self.status = 'completed'
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
