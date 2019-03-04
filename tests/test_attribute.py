from typing import List, Optional

import pytest

from os_credits.perun.attributes import (
    DenbiCreditTimestamps,
    _ContainerPerunAttribute,
    _ScalarPerunAttribute,
)


class TestAttributes:
    class ScalarTestAttribute(
        _ScalarPerunAttribute[Optional[str]],
        perun_id=0000,
        perun_friendly_name="myTestAttr",
        perun_type="test",
        perun_namespace="test",
    ):
        def __init__(self, **kwargs: str) -> None:
            super().__init__(**kwargs)

    class ContainerTestAttribute(
        _ContainerPerunAttribute[List[str]],
        perun_id=0000,
        perun_friendly_name="myTestAttr",
        perun_type="test",
        perun_namespace="test",
    ):
        def __init__(self, **kwargs: str) -> None:
            super().__init__(**kwargs)

    def test_scalar_attribute_fixed_type(self):
        my_attr = self.ScalarTestAttribute(value="test_str", displayName="test")
        assert not my_attr.has_changed
        my_attr.value = "1234"
        assert (
            my_attr.value == "1234"
        ), "Changing value without changing type is allowed"
        with pytest.raises(TypeError):
            my_attr.value = 1234
        assert my_attr.has_changed

    def test_container_attribute_read_only(self):
        """Only the contents of container attributes are allowed to change"""
        my_attr = self.ContainerTestAttribute(
            value=["lala", "1234"], displayName="test"
        )
        assert not my_attr.has_changed
        my_attr.value.append("test2")
        with pytest.raises(AttributeError):
            my_attr.value = 1234
        assert my_attr.has_changed

    def test_container_attribute_not_none_value(self):
        """In case of value=None a container attribute must initialize `value` with an
        empty container (List/Set/Tuple) since only its contents can be changed
        """
        with pytest.raises(AttributeError):
            self.ContainerTestAttribute(value=None, displayName="test")

    def test_changed_indicator(self):
        my_attr = DenbiCreditTimestamps(value=None, displayName="test")
        assert not my_attr.has_changed
        my_attr.value.update({"test": "test"})
        assert my_attr.has_changed
        my_attr.has_changed = False
        assert not my_attr.has_changed
        with pytest.raises(ValueError):
            my_attr.has_changed = True
