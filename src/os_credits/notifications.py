from __future__ import annotations

from asyncio import AbstractEventLoop, get_event_loop
from email.mime.text import MIMEText
from enum import Enum, auto
from string import Template
from typing import ClassVar, Dict, Optional, Set, Union

from aiosmtplib import SMTP

from os_credits.exceptions import BrokenTemplateError, MissingTemplateError
from os_credits.log import internal_logger
from os_credits.perun.groupsManager import Group
from os_credits.settings import config


class EmailRecipient(Enum):
    CLOUD_GOVERNANCE = auto()
    PROJECT_MAINTAINERS = auto()


EmailRecipientType = Union[str, EmailRecipient]


class EmailNotificationBase(Exception):
    """Base class of all exceptions whose cause should not only be logged but also send
    to the Cloud Governance and/or the Group maintainers."""

    to: ClassVar[Set[EmailRecipientType]]
    cc: ClassVar[Set[EmailRecipientType]] = set()
    bcc: ClassVar[Set[EmailRecipientType]] = set()

    """:class:`string.Template` object created on class instantiation from the content
    of :attr:`subject_template`."""
    subject: ClassVar[Template]
    """Contains the template for the subject of mail in string form. Must be defined by
    any subclass."""
    subject_template: ClassVar[str]
    """:class:`string.Template` object created on class instantiation from the content
    of :attr:`body_template`."""
    body: ClassVar[Template]
    """Contains the template for the body of mail in string form. Must be defined by any
    subclass."""
    body_template: ClassVar[str]
    """Mapping between placeholders and values which can used inside subject and body
    templates. See :func:`construct_message` for default mappings provided by the base
    class. Feel free to overwrite/extend the function or add custom mappings to this
    attribute inside the constructor of your subclass.
    """
    placeholders: Dict[str, str] = {}

    def __init_subclass__(cls) -> None:
        """Automatically constructs a template from the body provided by the subclass.

        Before construction whitespace at beginning and end of the body is removed.

        :raises ValueError: In case any template construction fails or the class defines
        no `To`.
        """
        if not "body_template" in dir(cls) or not cls.body_template.strip():
            raise MissingTemplateError(
                f"Body template of {cls.__name__} is not defined or empty."
            )
        if not "subject_template" in dir(cls) or not cls.subject_template.strip():
            raise MissingTemplateError(
                f"Subject template of {cls.__name__} is not defined or empty."
            )
        cls.body = Template(cls.body_template.strip())
        cls.subject = Template(cls.subject_template.strip())

    def __init__(self, group: Group, message: str) -> None:
        self.group = group
        self.message = message

    def construct_message(self) -> MIMEText:
        placeholder = {
            "project": self.group.name,
            "credits_current": str(self.group.credits_current.value),
            "credits_granted": str(self.group.credits_granted.value),
            **self.placeholders,
        }
        try:
            rendered_subject = self.subject.substitute(placeholder)
        except KeyError as e:
            internal_logger.error(
                "Subject of Notification %s contains unknown placeholder %s. Sending "
                "partially unformatted mail.",
                type(self).__name__,
                e,
            )
            rendered_subject = self.subject.safe_substitute(placeholder)
        except ValueError as e:
            internal_logger.error(
                "Subject of Notification %s contains invalid placeholder %s.",
                type(self).__name__,
                e,
            )
            raise BrokenTemplateError(f"Subject of Notification {type(self).__name__}")
        try:
            rendered_body = self.body.substitute(placeholder)
        except KeyError as e:
            internal_logger.error(
                "Body of Notification %s contains unknown placeholder %s. Sending "
                "partially unformatted mail.",
                type(self).__name__,
                e,
            )
            rendered_body = self.body.safe_substitute(placeholder)
        except ValueError as e:
            internal_logger.error(
                "Body of Notification %s contains invalid placeholder %s.",
                type(self).__name__,
                e,
            )
            raise BrokenTemplateError(f"Body of Notification {type(self).__name__}")
        message = MIMEText(rendered_body)
        message["Subject"] = rendered_subject
        message["From"] = config["MAIL_FROM"]
        if config["NOTIFICATION_TO_OVERWRITE"].strip():
            internal_logger.info(
                "Applying `NOTIFICATION_TO_OVERWRITE` setting to notification `%s`",
                self,
            )
            message["To"] = config["NOTIFICATION_TO_OVERWRITE"]
        else:
            message["To"] = self.resolve_recipient_placeholders(self.to)
            message["Cc"] = self.resolve_recipient_placeholders(self.cc)
            message["Bcc"] = self.resolve_recipient_placeholders(self.bcc)
        internal_logger.debug(
            "Recipients of notification `%s`: To=%s, Cc=%s, Bcc=%s",
            self,
            message["To"],
            message["Cc"],
            message["Bcc"],
        )

        return message

    def resolve_recipient_placeholders(
        self, recipient_placeholders: Set[EmailRecipientType]
    ) -> str:
        recipients = set()
        for r in recipient_placeholders:
            if r is EmailRecipient.CLOUD_GOVERNANCE:
                recipients.add(config["CLOUD_GOVERNANCE_MAIL"])
            elif r is EmailRecipient.PROJECT_MAINTAINERS:
                for mail in self.group.email.value:
                    recipients.add(mail)
            elif isinstance(r, str):
                recipients.add(r)
        return ",".join(recipients)


class HalfOfCreditsLeft(EmailNotificationBase):
    subject_template = "50% Credits left for Project ${project}"
    to = {EmailRecipient.PROJECT_MAINTAINERS}
    cc = {EmailRecipient.CLOUD_GOVERNANCE}
    body_template = """
Dear Project Maintainer,

Your OpenStack Project ${project} in the de.NBI Cloud has less than 50% of its credits
left. To view a history of your credits please login at the Cloud Portal under
https://cloud.denbi.de/portal.

Have a nice day,
Your de.NBI Cloud Governance

----
This is an automatically generated message, please do not respond to it directly.
Use contact@denbi.de instead.
"""

    def __init__(self, group: Group) -> None:
        super().__init__(
            group,
            message=f"Group {group.name} has only 50% of their credits left. Sending "
            "notification.",
        )
        self.group = group


async def send_notification(
    notification: EmailNotificationBase, loop: Optional[AbstractEventLoop] = None
) -> None:
    loop = loop or get_event_loop()
    async with SMTP(
        hostname=config["MAIL_SMTP_SERVER"], port=config["MAIL_SMTP_PORT"], loop=loop
    ) as smtp:
        if not config["MAIL_NOT_STARTTLS"]:
            internal_logger.debug("Not connecting via STARTTLS as requested")
            await smtp.starttls()
        if config["MAIL_SMTP_USER"] and config["MAIL_SMTP_PASSWORD"]:
            internal_logger.debug("Authenticating against smtp server")
            await smtp.login(config["MAIL_SMTP_USER"], config["MAIL_SMTP_PASSWORD"])
        else:
            internal_logger.debug(
                "Not authenticating against smtp server since neither user and/nor "
                "password are specified."
            )
        await smtp.send_message(notification.construct_message())
