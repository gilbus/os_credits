import pytest

from os_credits.perun.attributes import DenbiCreditsUsed


def test_perun_attr_setattr(perun_test_group):
    credits_used = DenbiCreditsUsed(value=200)
    perun_test_group.credits_used = credits_used
    with pytest.raises(AttributeError):
        perun_test_group.credits_used = 5
