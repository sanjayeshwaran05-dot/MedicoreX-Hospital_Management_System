
"""
Hospital Management System - Patient Model
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Patient(db.Model):
    """Patient Model"""
    __tablename__ = 'patients'
    
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.Enum('Male', 'Female', 'Other'), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100))
    blood_group = db.Column(db.Enum('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'))
    address = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True, cascade='all, delete-orphan')
    bills = db.relationship('Bill', backref='patient', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Patient {self.id} - {self.name}>'
    
    def to_dict(self):
        """Convert patient object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'phone': self.phone,
            'email': self.email,
            'blood_group': self.blood_group,
            'address': self.address,
            'medical_history': self.medical_history,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def create(data):
        """Create a new patient"""
        # Generate patient ID if not provided
        if 'id' not in data or not data['id']:
            last_patient = Patient.query.order_by(Patient.id.desc()).first()
            if last_patient:
                last_num = int(last_patient.id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            data['id'] = f'P{str(new_num).zfill(4)}'
        
        patient = Patient(
            id=data['id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            phone=data['phone'],
            email=data.get('email'),
            blood_group=data.get('blood_group'),
            address=data.get('address'),
            medical_history=data.get('medical_history')
        )
        
        db.session.add(patient)
        db.session.commit()
        return patient
    
    def update(self, data):
        """Update patient information"""
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at']:
                setattr(self, key, value)
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete patient"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_all(page=1, per_page=20, search=None):
        """Get all patients with optional pagination and search"""
        query = Patient.query
        
        if search:
            search_term = f'%{search}%'
            query = query.filter(
                db.or_(
                    Patient.name.like(search_term),
                    Patient.id.like(search_term),
                    Patient.phone.like(search_term),
                    Patient.email.like(search_term)
                )
            )
        
        return query.order_by(Patient.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_by_id(patient_id):
        """Get patient by ID"""
        return Patient.query.get(patient_id)
    
    @staticmethod
    def get_by_phone(phone):
        """Get patient by phone number"""
        return Patient.query.filter_by(phone=phone).first()
    
    @staticmethod
    def get_statistics():
        """Get patient statistics"""
        total_patients = Patient.query.count()
        
        # New patients in last 30 days
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        new_patients = Patient.query.filter(Patient.created_at >= thirty_days_ago).count()
        
        # Patients by blood group
        blood_groups = {}
        for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            count = Patient.query.filter_by(blood_group=bg).count()
            blood_groups[bg] = count
        
        # Patients by gender
        gender_distribution = {
            'Male': Patient.query.filter_by(gender='Male').count(),
            'Female': Patient.query.filter_by(gender='Female').count(),
            'Other': Patient.query.filter_by(gender='Other').count()
        }
        
        return {
            'total_patients': total_patients,
            'new_patients': new_patients,
            'blood_groups': blood_groups,
            'gender_distribution': gender_distribution
        }


class AuditLog(db.Model):
    """Audit Log Model for tracking changes"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(50))
    old_data = db.Column(db.JSON)
    new_data = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type} at {self.timestamp}>'
    
    @staticmethod
    def log(user_id, action, entity_type, entity_id, old_data=None, new_data=None):
        """Create an audit log entry"""
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data
        )
        db.session.add(log)
        db.session.commit()
        return log
