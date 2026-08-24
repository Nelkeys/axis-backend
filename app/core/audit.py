from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.admin import AdminUser

def log_audit(
    db: Session,
    admin: AdminUser,
    action: str,
    entity_type: str,
    entity_id: int = None,
    ip_address: str = None,
    details: dict = None
):
    """
    Appends an audit log to the current database transaction.
    It will be committed when the endpoint calls db.commit().
    """
    log = AuditLog(
        admin_id=admin.id if admin else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details
    )
    db.add(log)