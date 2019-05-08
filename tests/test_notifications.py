from asyncio import wait
from importlib import reload

import pytest


@pytest.fixture
def notification_group():
    from os_credits.perun.attributes import (
        DenbiCreditsGranted,
        DenbiCreditsUsed,
        ToEmail,
    )
    from os_credits.perun.group import Group
    from .conftest import TEST_INITIAL_CREDITS_GRANTED

    test_group = Group("TestGroup")
    test_group.email = ToEmail(value=["admin@project"])
    test_group.credits_used = DenbiCreditsUsed(value=str(TEST_INITIAL_CREDITS_GRANTED))
    test_group.credits_granted = DenbiCreditsGranted(
        value=str(TEST_INITIAL_CREDITS_GRANTED)
    )
    return test_group


@pytest.fixture
def NotificationClass():
    from os_credits.notifications import EmailNotificationBase, EmailRecipient

    class NotificationTest1(EmailNotificationBase):
        body_template = "$credits_granted - $project"
        subject_template = "Test: $credits_used"
        to = {"test3@local", EmailRecipient.PROJECT_MAINTAINERS}
        cc = {EmailRecipient.CLOUD_GOVERNANCE}
        bcc = {"test2@local"}

        def __init__(self, group):
            super().__init__(group, "")

    return NotificationTest1


def test_detect_invalid_notifications(notification_group):
    from os_credits.notifications import EmailNotificationBase
    from os_credits.exceptions import (
        BrokenTemplateError,
        MissingTemplateError,
        MissingToError,
    )

    with pytest.raises(MissingTemplateError):

        class EmptySubjectTemplate(EmailNotificationBase):
            body_template = "Hallo welt"
            subject_template = ""
            to = {"test@local"}

    with pytest.raises(MissingTemplateError):

        class MissingSubjectTemplate(EmailNotificationBase):
            body_template = "Hallo welt"
            to = {"test@local"}

    with pytest.raises(MissingToError):

        class MissingTo(EmailNotificationBase):
            body_template = "Hallo $welt"
            subject_template = "Broken $template"

    with pytest.raises(MissingToError):

        class InvalidTo(EmailNotificationBase):
            body_template = "Hallo $welt"
            subject_template = "Broken $template"
            to = set()

    with pytest.raises(BrokenTemplateError):

        class BrokenTemplate(EmailNotificationBase):
            body_template = "Hallo $100 welt"
            subject_template = "Broken $ template"
            to = {"test@local"}

            def __init__(self, group):
                super().__init__(group, "")

        BrokenTemplate(notification_group).construct_message()


def test_notification_to_overwrite(NotificationClass, notification_group):
    from os_credits.settings import config

    overwrite_mail = "overwrite@mail"
    config["NOTIFICATION_TO_OVERWRITE"] = overwrite_mail
    from os_credits import notifications

    # necessary since the module imports config and does not see the changes
    reload(notifications)
    from os_credits.notifications import EmailNotificationBase, EmailRecipient

    class NotificationClass(EmailNotificationBase):
        body_template = "$credits_granted - $project"
        subject_template = "Test: $credits_used"
        to = {"test3@local", EmailRecipient.PROJECT_MAINTAINERS}
        cc = {EmailRecipient.CLOUD_GOVERNANCE}
        bcc = {"test2@local"}

        def __init__(self, group):
            super().__init__(group, "")

    notification = NotificationClass(notification_group)
    msg = notification.construct_message()
    assert (
        msg["Cc"] == msg["Bcc"] == None
    ), "Cc and Bcc not empty despite NOTIFICATION_TO_OVERWRITE"
    assert (
        msg["To"] == overwrite_mail
    ), "NOTIFICATION_TO_OVERWRITE not applied correctly"
    del config["NOTIFICATION_TO_OVERWRITE"]


def test_message_construction(NotificationClass, notification_group):
    """Require smtpserver fixture to ensure that the value of
    config['CLOUD_GOVERNANCE_MAIL'] is set"""

    from os_credits.settings import config

    notification = NotificationClass(notification_group)
    msg = notification.construct_message()
    # using sets to test independent of order
    assert set(msg["To"].split(",")) == set(
        ("test3@local", "admin@project")
    ), "Wrong To in header of constructed message"
    assert (
        msg["Cc"] == config["CLOUD_GOVERNANCE_MAIL"]
    ), "Wrong Cc in header of constructed message"
    assert (
        msg["Bcc"] == "test2@local"
    ), "Wrong Bcc in header of construct_message message"
    assert (
        msg["Subject"] == f"Test: {notification_group.credits_used.value}"
    ), "Bad substitution of Subject"
    assert (
        msg._payload == f"{notification_group.credits_granted.value} - TestGroup"
    ), "Bad substitution of Body"


async def test_sending(smtpserver, loop, NotificationClass, notification_group):
    from os_credits.notifications import EmailNotificationBase, send_notification

    notification = NotificationClass(notification_group)

    with pytest.raises(EmailNotificationBase):
        raise notification
    assert len(smtpserver.outbox) == 0

    await wait({loop.create_task(send_notification(notification))})
    assert len(smtpserver.outbox) == 1


def test_construction_with_missing_placeholder(NotificationClass, notification_group):
    """Test whether a notification with an unresolvable placeholder in a template
    constructs a message with the placeholder unresolved. Requires the smtpserver
    fixture to ensure that the value of config['CLOUD_GOVERNANCE_MAIL'] is set"""

    class NotificationWithUnresolvableTemplate(NotificationClass):
        subject_template = "$unresolvable"

        def __init__(self, group):
            super().__init__(group)

    notification = NotificationWithUnresolvableTemplate(notification_group)
    msg = notification.construct_message()
    assert msg["Subject"] == NotificationWithUnresolvableTemplate.subject_template


def test_placeholder_overwrite_default(NotificationClass, notification_group):
    class NotificationWithCustomPlaceholder(NotificationClass):
        subject_template = "$credits_used"
        custom_placeholders = {"credits_used": "MyPlaceholder"}

        def __init__(self, group):
            super().__init__(group)

    notification = NotificationWithCustomPlaceholder(notification_group)
    msg = notification.construct_message()
    assert msg["Subject"] == "MyPlaceholder"
