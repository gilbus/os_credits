from asyncio import wait
from importlib import reload

import pytest

from os_credits.exceptions import (
    BrokenTemplateError,
    MissingTemplateError,
    MissingToError,
)
from os_credits.notifications import (
    EmailNotificationBase,
    EmailRecipient,
    send_notification,
)
from os_credits.perun.attributes import DenbiCreditsGranted, DenbiCreditsUsed, ToEmail
from os_credits.perun.groupsManager import Group

from .conftest import TEST_INITIAL_CREDITS_GRANTED

test_group = Group("TestGroup")
test_group.email = ToEmail(value=["admin@project"])
test_group.credits_used = DenbiCreditsUsed(value=str(TEST_INITIAL_CREDITS_GRANTED))
test_group.credits_granted = DenbiCreditsGranted(
    value=str(TEST_INITIAL_CREDITS_GRANTED)
)


def test_detect_invalid_notifications():

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

        BrokenTemplate(test_group).construct_message()


class NotificationTest1(EmailNotificationBase):
    body_template = "$credits_granted - $project"
    subject_template = "Test: $credits_used"
    to = {"test3@local", EmailRecipient.PROJECT_MAINTAINERS}
    cc = {EmailRecipient.CLOUD_GOVERNANCE}
    bcc = {"test2@local"}

    def __init__(self, group):
        super().__init__(group, "")


def test_notification_to_overwrite(smtpserver, monkeypatch):
    from os_credits import settings

    overwrite_mail = "overwrite@mail"
    monkeypatch.setenv("NOTIFICATION_TO_OVERWRITE", overwrite_mail)
    reload(settings)
    notification = NotificationTest1(test_group)
    msg = notification.construct_message()
    assert (
        msg["Cc"] == msg["Bcc"] == None
    ), "Cc and Bcc not empty despite NOTIFICATION_TO_OVERWRITE"
    assert (
        msg["To"] == overwrite_mail
    ), "NOTIFICATION_TO_OVERWRITE not applied correctly"


def test_message_construction(smtpserver):
    """Require smtpserver fixture to ensure that the value of
    config['CLOUD_GOVERNANCE_MAIL'] is set"""

    from os_credits.settings import config

    notification = NotificationTest1(test_group)
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
        msg["Subject"] == f"Test: {test_group.credits_used.value}"
    ), "Bad substitution of Subject"
    assert (
        msg._payload == f"{test_group.credits_granted.value} - TestGroup"
    ), "Bad substitution of Body"


async def test_sending(smtpserver, loop):
    notification = NotificationTest1(test_group)

    with pytest.raises(EmailNotificationBase):
        raise notification
    assert len(smtpserver.outbox) == 0

    await wait({loop.create_task(send_notification(notification))})
    assert len(smtpserver.outbox) == 1
