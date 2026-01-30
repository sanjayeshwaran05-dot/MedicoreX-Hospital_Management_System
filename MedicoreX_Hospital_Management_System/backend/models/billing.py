
"""
Hospital Management System - Billing Model
"""

from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from models.patient import db


class Bill(db.Model):
    """Bill Model"""
    __tablename__ = 'bills'
    
    id = db.Column(db.String(50), primary_key=True)
    patient_id = db.Column(db.String(50), db.ForeignKey('patients.id'), nullable=False, index=True)
    appointment_id = db.Column(db.String(50), db.ForeignKey('appointments.id'), nullable=True)
    subtotal = db.Column(db.Decimal(10, 2), nullable=False)
    discount = db.Column(db.Decimal(10, 2), default=0)
    tax = db.Column(db.Decimal(10, 2), default=0)
    total_amount = db.Column(db.Decimal(10, 2), nullable=False)
    status = db.Column(
        db.Enum('pending', 'paid', 'partial'),
        default='pending',
        nullable=False,
        index=True
    )
    payment_method = db.Column(db.Enum('cash', 'card', 'upi', 'insurance'))
    notes = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    items = db.relationship('BillItem', backref='bill', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Bill {self.id} - \u20b9{self.total_amount} ({self.status})>'
    
    def to_dict(self):
        """Convert bill object to dictionary"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'appointment_id': self.appointment_id,
            'subtotal': float(self.subtotal) if self.subtotal else 0,
            'discount': float(self.discount) if self.discount else 0,
            'tax': float(self.tax) if self.tax else 0,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'status': self.status,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items]
        }
    
    @staticmethod
    def create(data, items_data):
        """Create a new bill with items"""
        from models.patient import Patient
        from models.appointment import Appointment
        
        # Generate bill ID if not provided
        if 'id' not in data or not data['id']:
            last_bill = Bill.query.order_by(Bill.id.desc()).first()
            if last_bill:
                last_num = int(last_bill.id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            data['id'] = f'B{str(new_num).zfill(4)}'
        
        # Verify patient exists
        patient = Patient.query.get(data['patient_id'])
        if not patient:
            raise ValueError(f'Patient {data["patient_id"]} not found')
        
        # Verify appointment exists if provided
        if data.get('appointment_id'):
            appointment = Appointment.query.get(data['appointment_id'])
            if not appointment:
                raise ValueError(f'Appointment {data["appointment_id"]} not found')
        
        # Calculate totals from items
        subtotal = sum(Decimal(str(item['amount'])) for item in items_data)
        discount = Decimal(str(data.get('discount', 0)))
        tax_rate = Decimal(str(data.get('tax', 0)))
        tax_amount = (subtotal - discount) * (tax_rate / Decimal('100'))
        total = subtotal - discount + tax_amount
        
        bill = Bill(
            id=data['id'],
            patient_id=data['patient_id'],
            appointment_id=data.get('appointment_id'),
            subtotal=subtotal,
            discount=discount,
            tax=tax_amount,
            total_amount=total,
            status=data.get('status', 'pending'),
            payment_method=data.get('payment_method'),
            notes=data.get('notes')
        )
        
        db.session.add(bill)
        db.session.flush()  # Get bill ID
        
        # Create bill items
        for item_data in items_data:
            bill_item = BillItem(
                bill_id=bill.id,
                description=item_data['description'],
                amount=Decimal(str(item_data['amount']))
            )
            db.session.add(bill_item)
        
        db.session.commit()
        return bill
    
    def update(self, data, items_data=None):
        """Update bill information"""
        from models.appointment import Appointment
        
        for key, value in data.items():
            if hasattr(self, key) and key not in ['id', 'created_at', 'patient_id']:
                if key in ['subtotal', 'discount', 'tax', 'total_amount']:
                    setattr(self, key, Decimal(str(value)))
                else:
                    setattr(self, key, value)
        
        # Verify appointment exists if provided
        if data.get('appointment_id'):
            appointment = Appointment.query.get(data['appointment_id'])
            if not appointment:
                raise ValueError(f'Appointment {data["appointment_id"]} not found')
        
        # Update items if provided
        if items_data is not None:
            # Remove existing items
            BillItem.query.filter_by(bill_id=self.id).delete()
            
            # Add new items
            for item_data in items_data:
                bill_item = BillItem(
                    bill_id=self.id,
                    description=item_data['description'],
                    amount=Decimal(str(item_data['amount']))
                )
                db.session.add(bill_item)
            
            # Recalculate totals
            subtotal = sum(Decimal(str(item['amount'])) for item in items_data)
            discount = Decimal(str(data.get('discount', self.discount)))
            tax_rate = Decimal(str(data.get('tax', self.tax)))
            tax_amount = (subtotal - discount) * (tax_rate / Decimal('100'))
            total = subtotal - discount + tax_amount
            
            self.subtotal = subtotal
            self.discount = discount
            self.tax = tax_amount
            self.total_amount = total
        
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def delete(self):
        """Delete bill"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def get_all(page=1, per_page=20, search=None, status=None, patient_id=None, start_date=None, end_date=None):
        """Get all bills with optional pagination, search, and filters"""
        from models.patient import Patient
        
        query = Bill.query
        
        if search:
            # Search by patient name or bill ID
            search_term = f'%{search}%'
            patient_ids = [p.id for p in Patient.query.filter(Patient.name.like(search_term)).all()]
            query = query.filter(
                db.or_(
                    Bill.id.like(search_term),
                    Bill.patient_id.in_(patient_ids)
                )
            )
        
        if status:
            query = query.filter_by(status=status)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        if start_date:
            query = query.filter(Bill.date >= start_date)
        
        if end_date:
            query = query.filter(Bill.date <= end_date)
        
        return query.order_by(Bill.date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    @staticmethod
    def get_by_id(bill_id):
        """Get bill by ID"""
        return Bill.query.get(bill_id)
    
    @staticmethod
    def get_by_patient(patient_id, page=1, per_page=20):
        """Get bills by patient"""
        return Bill.query.filter_by(patient_id=patient_id).order_by(
            Bill.date.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_by_appointment(appointment_id):
        """Get bill by appointment"""
        return Bill.query.filter_by(appointment_id=appointment_id).first()
    
    @staticmethod
    def get_outstanding_bills():
        """Get all outstanding (unpaid) bills"""
        return Bill.query.filter(Bill.status.in_(['pending', 'partial'])).all()
    
    @staticmethod
    def get_statistics(start_date=None, end_date=None):
        """Get billing statistics"""
        query = Bill.query
        
        if start_date:
            query = query.filter(Bill.date >= start_date)
        
        if end_date:
            query = query.filter(Bill.date <= end_date)
        
        total_revenue = db.session.query(db.func.sum(Bill.total_amount)).filter(
            Bill.status == 'paid'
        ).scalar() or Decimal('0')
        
        pending_amount = db.session.query(db.func.sum(Bill.total_amount)).filter(
            Bill.status.in_(['pending', 'partial'])
        ).scalar() or Decimal('0')
        
        status_counts = {
            'paid': query.filter_by(status='paid').count(),
            'pending': query.filter_by(status='pending').count(),
            'partial': query.filter_by(status='partial').count()
        }
        
        # Revenue by month
        revenue_by_month = db.session.query(
            db.func.date_format(Bill.date, '%Y-%m').label('month'),
            db.func.sum(Bill.total_amount).label('revenue'),
            db.func.count(Bill.id).label('count')
        ).filter(Bill.status == 'paid').group_by(
            db.func.date_format(Bill.date, '%Y-%m')
        ).order_by(db.func.date_format(Bill.date, '%Y-%m').desc()).limit(12).all()
        
        return {
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'status_distribution': status_counts,
            'revenue_by_month': [
                {'month': rev[0], 'revenue': float(rev[1]), 'count': rev[2]}
                for rev in revenue_by_month
            ]
        }
    
    def mark_as_paid(self, payment_method=None):
        """Mark bill as paid"""
        self.status = 'paid'
        if payment_method:
            self.payment_method = payment_method
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self
    
    def get_items_summary(self):
        """Get summary of bill items"""
        return [
            {
                'description': item.description,
                'amount': float(item.amount)
            }
            for item in self.items
        ]


class BillItem(db.Model):
    """Bill Item Model"""
    __tablename__ = 'bill_items'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    bill_id = db.Column(db.String(50), db.ForeignKey('bills.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Decimal(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<BillItem {self.description} - \u20b9{self.amount}>'
    
    def to_dict(self):
        """Convert bill item object to dictionary"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'description': self.description,
            'amount': float(self.amount) if self.amount else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
