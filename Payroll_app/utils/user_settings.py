from django.http import JsonResponse
from Payroll_app.models import Log

def api_response(status='success', data=None, message=None, status_code=200):
    response = {'status': status}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    return JsonResponse(response, status=status_code)

def log_action(user_email, action, model_name, object_id, changes=None, log_type='operation'):
    Log.objects.create(
        user_email=user_email,
        action=action,
        model_name=model_name,
        object_id=object_id,
        changes=changes,
        log_type=log_type
    )

def approval_to_dict(approval):
    data = {
        'id': approval.id,
        'request_type': approval.request_type,
        'description': approval.description,
        'submitted_at': approval.submitted_at.isoformat() if approval.submitted_at else None,
        'status': approval.status,
        'employee_id': approval.employee.id if approval.employee else None,
        'employee_name': approval.employee.user.email if approval.employee and approval.employee.user else None,
        'created_by': approval.created_by.email if approval.created_by else None,
        'modified_by': approval.modified_by.email if approval.modified_by else None,
        'related_model': approval.related_model,
        'related_object_id': approval.related_object_id,
    }
    return data