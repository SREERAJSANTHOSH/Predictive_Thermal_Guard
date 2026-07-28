"""C <-> Python parity, wired into the normal test run.

The embedded core is the thing that actually ships on hardware. If it drifts
from the reference the tests would keep passing while the firmware quietly
misbehaved, so parity is enforced here rather than left to a manual script.
"""

import shutil

import pytest
from tools.parity import SCENARIOS, build_library, compare


@pytest.fixture(scope="module")
def lib():
    if shutil.which("cc") is None and shutil.which("gcc") is None:
        pytest.skip("no C compiler available")
    return build_library()


class TestParity:
    @pytest.mark.parametrize("name", list(SCENARIOS))
    def test_scenario_matches(self, lib, name):
        point_ids, sweeps = SCENARIOS[name]()
        divergences = compare(point_ids, sweeps, lib=lib)
        assert not divergences, "\n".join(str(d) for d in divergences[:20])

    def test_c_builds_without_warnings(self, lib):
        """build_library raises if the compiler emits anything on stderr."""
        assert lib is not None

    def test_verdict_enum_order_is_locked(self, lib):
        """A reordered C enum must fail loudly, not silently remap verdicts."""
        from tools.parity import C_VERDICTS

        for i, name in enumerate(C_VERDICTS):
            assert lib.tsg_verdict_name(i).decode() == name
