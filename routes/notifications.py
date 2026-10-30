"""Expiry reminder routes + the background expiry checker job."""
from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from config import Config
from models import db, FoodItem, Notification

notifications_bp = Blueprint("notifications", __name__)


def run_expiry_check():
    """Scan every item in the database and create reminders for anything
    expiring within REMINDER_DAYS_BEFORE (or already expired).

    Skips items that already have an unread reminder, so running this
    repeatedly never spams the user. Returns the number of reminders created.
    """
    today = date.today()
    warn_limit = today + timedelta(days=Config.REMINDER_DAYS_BEFORE)
    created = 0

    items = FoodItem.query.filter(FoodItem.expiry_date <= warn_limit).all()
    for item in items:
        if Notification.query.filter_by(food_id=item.id, is_read=False).first():
            continue  # unread reminder already exists for this item

        if item.days_to_expiry < 0:
            message = (f'"{item.food_name}" expired {abs(item.days_to_expiry)} '
                       f"day(s) ago - please discard it safely.")
        elif item.days_to_expiry == 0:
            message = f'"{item.food_name}" expires today - use it or lose it!'
        else:
            message = (f'"{item.food_name}" expires in {item.days_to_expiry} '
                       f"day(s) - plan to use it soon.")

        db.session.add(Notification(user_id=item.user_id, food_id=item.id,
                                    message=message))
        created += 1

    db.session.commit()
    return created


@notifications_bp.route("/reminders")
@login_required
def reminders():
    notes = current_user.notifications.order_by(
        Notification.is_read.asc(),
        Notification.notification_date.desc(),
    ).limit(100).all()
    return render_template("reminders.html", notifications=notes)


@notifications_bp.route("/reminders/<int:note_id>/read", methods=["POST"])
@login_required
def mark_read(note_id):
    note = db.session.get(Notification, note_id)
    if note is not None and note.user_id == current_user.id:
        note.is_read = True
        db.session.commit()
    return redirect(url_for("notifications.reminders"))


@notifications_bp.route("/reminders/read-all", methods=["POST"])
@login_required
def mark_all_read():
    current_user.notifications.filter_by(is_read=False)\
        .update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    flash("All reminders marked as read.", "info")
    return redirect(url_for("notifications.reminders"))


@notifications_bp.route("/reminders/check", methods=["POST"])
@login_required
def run_check():
    """Manual trigger so users (and viva demos) do not have to wait 12 hours."""
    created = run_expiry_check()
    if created:
        flash(f"Expiry check complete - {created} new reminder(s) created.",
              "success")
    else:
        flash("Expiry check complete - everything looks fine for now.", "info")
    return redirect(url_for("notifications.reminders"))
