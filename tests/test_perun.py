from importlib import reload
from os import getenv
from random import randint

import pytest

from os_credits.perun.attributes import DenbiCreditsUsed, DenbiCreditTimestamps, ToEmail
from os_credits.perun.attributesManager import (
    get_attributes,
    get_resource_bound_attributes,
    set_attributes,
    set_resource_bound_attributes,
)
from os_credits.perun.exceptions import (
    BadCredentialsException,
    DenbiCreditsGrantedMissing,
    GroupNotExistsError,
    GroupResourceNotAssociatedError,
)
from os_credits.perun.group import Group
from os_credits.perun.groupsManager import get_group_by_name

pytestmark = pytest.mark.skipif(
    not getenv("TEST_ONLINE", False),
    reason="Skip all tests against Perun since $TEST_ONLINE is not set.",
)


async def test_bad_credentials(perun_test_group: Group, monkeypatch):
    from os_credits import settings

    monkeypatch.setenv("OS_CREDITS_PERUN_LOGIN", "bogus")
    monkeypatch.setenv("OS_CREDITS_PERUN_PASSWORD", "bogus")
    reload(settings)

    with pytest.raises(BadCredentialsException):
        await get_group_by_name(perun_test_group.name)


async def test_group_not_exists():

    with pytest.raises(GroupNotExistsError):
        await get_group_by_name("This Group Does Not Exist")


async def test_get_group_by_name(perun_test_group: Group):
    resp = await get_group_by_name(perun_test_group.name)
    assert resp["id"] == perun_test_group.id


async def test_get_attributes(perun_test_group: Group):
    # assert value which must not be changed inside Perun
    resp = await get_attributes(
        perun_test_group.id, attribute_full_names=[ToEmail.get_full_name()]
    )
    assert resp[0]["value"] == ["DO NOT CHANGE THIS VALUES"], "Unexpected response"


async def test_set_attributes(perun_test_group: Group, loop):
    random_value = randint(0, 200)

    credits_used = DenbiCreditsUsed(value=random_value)
    await set_attributes(perun_test_group.id, [credits_used])
    resp = await get_attributes(
        perun_test_group.id, attribute_full_names=[DenbiCreditsUsed.get_full_name()]
    )
    # value is stored as str inside Perun
    assert resp[0]["value"] == str(random_value)


async def test_credits_granted_missing(perun_test_group: Group):
    # name of Perun group without any value
    perun_test_group.name = f"{perun_test_group.name}_credits_granted"
    # attr should not be set
    with pytest.raises(DenbiCreditsGrantedMissing):
        await perun_test_group.connect()


async def test_group_resource_not_associated(perun_test_group: Group):
    # name of Perun group without association
    perun_test_group.name = f"{perun_test_group.name}_no_resource"
    # attr should not be set
    with pytest.raises(GroupResourceNotAssociatedError):
        await perun_test_group.connect()


async def test_not_associated_error(perun_test_group: Group):
    assert await perun_test_group.is_assigned_resource()
    # OPENSTACK_RESOURCE
    not_associated_but_existing_resource_id = 8675
    perun_test_group.resource_id = not_associated_but_existing_resource_id
    assert not await perun_test_group.is_assigned_resource()


async def test_set_resource_bound_attributes(perun_test_group: Group):
    random_value = {"test": "2019-01-01 00:00:00.000000"}

    timestamps = DenbiCreditTimestamps(value=random_value)
    await set_resource_bound_attributes(
        perun_test_group.id, perun_test_group.resource_id, [timestamps]
    )
    resp = await get_resource_bound_attributes(
        perun_test_group.id,
        perun_test_group.resource_id,
        attribute_full_names=[DenbiCreditTimestamps.get_full_name()],
    )
    # value is stored as str inside Perun
    assert resp[0]["value"] == random_value


async def test_group_repr(perun_test_group):
    await perun_test_group.connect()
    # make sure that __repr__ never fails
    repr(perun_test_group)
    assert True
