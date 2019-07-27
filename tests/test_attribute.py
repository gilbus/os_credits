from typing import List
from typing import Optional

import pytest

from os_credits.perun.attributes import ContainerPerunAttribute
from os_credits.perun.attributes import DenbiCreditsGranted
from os_credits.perun.attributes import DenbiCreditTimestamps
from os_credits.perun.attributes import ScalarPerunAttribute
from os_credits.perun.base_attributes import PerunAttribute


@pytest.fixture(name="ContainerTestAttribute")
def fixtureContainerTestAttribute():
    class ContainerTestAttribute(
        ContainerPerunAttribute[List[str]],
        perun_id=0000,
        perun_friendly_name="myContainerTestAttr",
        perun_type="test",
        perun_namespace="test",
    ):
        def __init__(self, **kwargs: str) -> None:
            super().__init__(**kwargs)

    return ContainerTestAttribute


@pytest.fixture(name="ScalarTestAttribute")
def fixtureScalarTestAttribute():
    class ScalarTestAttribute(
        ScalarPerunAttribute[Optional[str]],
        perun_id=0000,
        perun_friendly_name="myScalarTestAttr",
        perun_type="test",
        perun_namespace="test",
    ):
        def __init__(self, **kwargs: str) -> None:
            super().__init__(**kwargs)

    return ScalarTestAttribute


def test_scalar_attribute_fixed_type(ScalarTestAttribute):
    my_attr = ScalarTestAttribute(value="test_str", displayName="test")
    assert not my_attr.has_changed
    my_attr.value = "1234"
    assert (
        my_attr.value == "1234"
    ), "Changing value without changing type is wrongly forbidden"
    assert my_attr.has_changed
    with pytest.raises(TypeError):
        my_attr.value = 1234


def test_container_attribute_read_only(ContainerTestAttribute):
    """Only the contents of container attributes are allowed to change"""
    my_attr = ContainerTestAttribute(value=["lala", "1234"], displayName="test")
    assert not my_attr.has_changed
    my_attr.value.append("test2")
    with pytest.raises(AttributeError):
        my_attr.value = 1234
    assert my_attr.has_changed


def test_container_attribute_not_none_value(ContainerTestAttribute):
    """In case of value=None a container attribute must initialize `value` with an
    empty container (List/Set/Tuple) since only its contents can be changed
    """
    with pytest.raises(AttributeError):
        ContainerTestAttribute(value=None, displayName="test")


def test_container_none_value_false():
    for attr_class in PerunAttribute.registered_attributes.values():
        try:
            attr = attr_class(value=None)
        except Exception:
            # in case of attributes which do not allow empty values
            continue
        print("Testing falseness of empty", attr_class)
        assert not bool(
            attr
        ), f"No provided value must evaluate to False, error for attribute {attr_class}"


def test_changed_indicator():
    my_attr = DenbiCreditTimestamps(value=None, displayName="test")
    assert not my_attr.has_changed
    my_attr.value.update({"test": "test"})
    assert my_attr.has_changed
    my_attr.has_changed = False
    assert not my_attr.has_changed
    with pytest.raises(ValueError):
        my_attr.has_changed = True


def test_credits_granted_read_only():
    credits_granted = DenbiCreditsGranted(value="100")
    with pytest.raises(AttributeError):
        credits_granted.value = 200
