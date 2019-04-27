from asyncio import wait

import pytest

from os_credits.exceptions import BrokenTemplateError, MissingTemplateError
from os_credits.notifications import (
    EmailNotificationBase,
    EmailRecipient,
    SendNotificationsMails,
)
from os_credits.perun.attributes import (
    DenbiCreditsCurrent,
    DenbiCreditsGranted,
    ToEmail,
)
from os_credits.perun.groupsManager import Group

from .conftest import TEST_INITIAL_CREDITS_GRANTED

test_group = Group("TestGroup")
test_group.email = ToEmail(value=["admin@project"])
test_group.credits_current = DenbiCreditsCurrent(
    value=str(TEST_INITIAL_CREDITS_GRANTED)
)
test_group.credits_granted = DenbiCreditsGranted(
    value=str(TEST_INITIAL_CREDITS_GRANTED)
)


def test_broken_template_detection():

    with pytest.raises(MissingTemplateError):

        class EmptySubjectTemplate(EmailNotificationBase):
            body_template = "Hallo welt"
            subject_template = ""

    with pytest.raises(MissingTemplateError):

        class MissingSubjectTemplate(EmailNotificationBase):
            body_template = "Hallo welt"

    with pytest.raises(BrokenTemplateError):

        class BrokenTemplate(EmailNotificationBase):
            body_template = "Hallo $100 welt"
            subject_template = "Broken $ template"

            def __init__(self, group):
                super().__init__(group, "")

        BrokenTemplate(test_group).construct_message()


class NotificationTest1(EmailNotificationBase):
    body_template = "$credits_granted - $project"
    subject_template = "Test: $credits_current"
    to = {"test3@local", EmailRecipient.PROJECT_MAINTAINERS}
    cc = {EmailRecipient.CLOUD_GOVERNANCE}
    bcc = {"test2@local"}

    def __init__(self, group):
        super().__init__(group, "")


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
        msg["Subject"] == f"Test: {test_group.credits_current.value}"
    ), "Bad substitution of Subject"
    assert (
        msg._payload == f"{test_group.credits_granted.value} - TestGroup"
    ), "Bad substitution of Body"


async def test_sending(smtpserver, loop):
    notification = NotificationTest1(test_group)

    with pytest.raises(EmailNotificationBase):
        raise notification
    assert len(smtpserver.outbox) == 0

    async def coro():
        async with SendNotificationsMails(loop=loop):
            raise notification

    await wait({loop.create_task(coro())})
    assert len(smtpserver.outbox) == 1
