"""Feedback workflow (#47): one place that changes a feedback's status, so a single change and
a bulk action save, record and notify the same way."""
from collections import defaultdict

from django.db import transaction
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from django.utils.text import Truncator
from django.utils.translation import gettext as _, ngettext, pgettext

from .models import FeedbackData

# flag, title and sentence the sender gets when their feedback reaches a status
_SENDER_MESSAGES = {
    FeedbackData.RESOLVED: ("success", lambda: _("Feedback resolved"), lambda: _("Your feedback has been resolved.")),
    FeedbackData.REJECTED: ("warning", lambda: _("Feedback rejected"), lambda: _("Your feedback has been rejected.")),
    FeedbackData.IN_PROGRESS: ("info", lambda: _("Feedback in progress"), lambda: _("Your feedback is being handled.")),
    FeedbackData.OPEN: ("info", lambda: _("Feedback reopened"), lambda: _("Your feedback has been reopened.")),
}


def set_status(feedback, status, note=None, notify=True):
    """Move ``feedback`` to ``status`` (saved with the usual history record) and, with
    ``notify``, tell its sender. Returns False when nothing changed."""
    if status not in dict(FeedbackData.STATUS_CHOICES):
        raise ValueError(f"Unknown feedback status: {status!r}")
    status_changed = feedback.status != status
    note_changed = note is not None and note != (feedback.note or "")
    if not (status_changed or note_changed):
        return False
    if note_changed:
        feedback.note = note
    feedback.status = status
    feedback.save()  # BaseModel.save: updated_by / updated_at and the history notification
    if notify and status_changed:
        notify_senders([feedback])
    return True


def resolve(feedback, note=None):
    return set_status(feedback, FeedbackData.RESOLVED, note=note)


def reopen(feedback, note=None):
    return set_status(feedback, FeedbackData.OPEN, note=note)


def _record_link(feedback):
    """(name, admin URL or None) of the record the feedback is about; the URL only when the
    sender may still view it."""
    obj = feedback.content_object
    if obj is None:
        return None, None
    ct = feedback.content_type
    url = None
    if feedback.user.has_perm(f"{ct.app_label}.view_{ct.model}") or feedback.user.has_perm(f"{ct.app_label}.change_{ct.model}"):
        try:
            url = reverse(f"admin:{ct.app_label}_{ct.model}_change", args=[feedback.object_id])
        except NoReverseMatch:
            url = None
    return str(obj), url


def _describe(feedback):
    """One feedback, as the sender reads it: the record, their own words, the note."""
    name, url = _record_link(feedback)
    parts = []
    if name:
        record = format_html('<a href="{}">{}</a>', url, name) if url else name
        # context: plain "About" is the About page's title ("Thông tin ứng dụng")
        parts.append(format_html("<p>{}: {}</p>", pgettext("feedback about a record", "About"), record))
    parts.append(format_html("<p>{}: <q>{}</q></p>", _("You wrote"), Truncator(feedback.message).words(30)))
    if feedback.note:
        parts.append(format_html("<p>{}: {}</p>", _("Note"), feedback.note))
    return format_html_join("", "{}", ((p,) for p in parts)), url


def notify_senders(feedbacks):
    """One notification (and toast) per sender and status: a bulk action on many feedbacks of
    the same person sends one message listing them, not one each."""
    from whiteneuron.notification.models import Notification

    groups = defaultdict(list)
    for feedback in feedbacks:
        groups[(feedback.user_id, feedback.status)].append(feedback)
    sent = []
    for (user_id, status), items in groups.items():
        flag, title, sentence = _SENDER_MESSAGES[status]
        if len(items) == 1:
            body, link = _describe(items[0])
            content = format_html("<p>{}</p>{}", sentence(), body)
            heading = str(title())
        else:
            link = None
            heading = ngettext("%(count)d feedback: %(title)s", "%(count)d feedbacks: %(title)s", len(items)) % {
                "count": len(items), "title": title()}
            content = format_html("<p>{}</p>{}", sentence(), format_html_join(
                "", "<hr>{}", ((_describe(fb)[0],) for fb in items)))
        notification = Notification.objects.create(
            user_id=user_id, title=heading[:255], content=content, action="update", flag=flag, obj_link=link,
        )
        # the toast too, once the change is committed (a failing channel layer never breaks it)
        transaction.on_commit(lambda n=notification, uid=user_id: n.alert(user_ids=[uid]))
        sent.append(notification)
    return sent
