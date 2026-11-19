"""Feedback workflow (#47): one place that changes a feedback's status, so a single change and
a bulk action save, record and notify the same way."""
from django.db import transaction
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .models import FeedbackData

# What the sender is told when their feedback reaches a status
_SENDER_MESSAGES = {
    FeedbackData.RESOLVED: ("success", lambda: _("Feedback resolved"), lambda: _("Your feedback has been resolved.")),
    FeedbackData.REJECTED: ("warning", lambda: _("Feedback rejected"), lambda: _("Your feedback has been rejected.")),
    FeedbackData.IN_PROGRESS: ("info", lambda: _("Feedback in progress"), lambda: _("Your feedback is being handled.")),
    FeedbackData.OPEN: ("info", lambda: _("Feedback reopened"), lambda: _("Your feedback has been reopened.")),
}


def set_status(feedback, status, note=None, assignee=None):
    """Move ``feedback`` to ``status`` (saving with the usual history record) and tell its
    sender. Returns False when nothing changed."""
    if status not in dict(FeedbackData.STATUS_CHOICES):
        raise ValueError(f"Unknown feedback status: {status!r}")
    changed = feedback.status != status
    if note is not None and note != (feedback.note or ""):
        feedback.note = note
        changed = True
    if assignee is not None and assignee != feedback.assignee:
        feedback.assignee = assignee
        changed = True
    if not changed:
        return False
    notify = feedback.status != status
    feedback.status = status
    feedback.save()  # BaseModel.save: updated_by / updated_at and the history notification
    if notify:
        _notify_sender(feedback)
    return True


def resolve(feedback, note=None):
    return set_status(feedback, FeedbackData.RESOLVED, note=note)


def reopen(feedback):
    return set_status(feedback, FeedbackData.OPEN)


def _notify_sender(feedback):
    from whiteneuron.notification.models import Notification

    flag, title, message = _SENDER_MESSAGES[feedback.status]
    content = format_html("<p>{}</p>", message())
    if feedback.note:
        content += format_html("<p>{}: {}</p>", _("Note"), feedback.note)
    notification = Notification.objects.create(
        user_id=feedback.user_id, title=str(title()), content=content, action="update", flag=flag,
        obj_link=None,
    )
    # the toast too, once the change is committed (a failing channel layer never breaks it)
    transaction.on_commit(lambda: notification.alert(user_ids=[feedback.user_id]))
    return notification
