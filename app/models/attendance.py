"""Attendance models for the mobile CORE OS attendance tracker."""
from datetime import datetime, timezone

from app.extensions import db


class AttendanceSubject(db.Model):
    __tablename__ = 'attendance_subjects'

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    faculty = db.Column(db.String(120), nullable=False, default='Faculty')
    minimum_percentage = db.Column(db.Float, nullable=False, default=75.0)
    max_classes_per_day = db.Column(db.Integer, nullable=False, default=1)
    color_value = db.Column(db.Integer, nullable=False, default=0xFF10B981)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship('User', back_populates='attendance_subjects')
    entries = db.relationship(
        'AttendanceEntry',
        back_populates='subject',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    __table_args__ = (
        db.Index('ix_attendance_subject_user_name', 'user_id', 'name'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'faculty': self.faculty,
            'minimum_percentage': self.minimum_percentage,
            'max_classes_per_day': self.max_classes_per_day,
            'color_value': self.color_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AttendanceEntry(db.Model):
    __tablename__ = 'attendance_entries'

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    subject_id = db.Column(
        db.String(64),
        db.ForeignKey('attendance_subjects.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(16), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship('User', back_populates='attendance_entries')
    subject = db.relationship('AttendanceSubject', back_populates='entries')

    __table_args__ = (
        db.Index('ix_attendance_entry_user_subject_date', 'user_id', 'subject_id', 'date'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'status': self.status,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
