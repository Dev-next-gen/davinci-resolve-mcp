"""strict mode has to switch on however the client spells the flag.

`docs/SKILL.md` tells callers to "pass strict=true on any destructive op to opt
in", and strict mode is the rule that refuses a destructive call when the
pre-mutation archive could not be created. `is_strict_required()` tested the
parameter with `is True`, so only a literal JSON boolean counted: the same MCP
clients that send `ripple="false"` and `overwrite="false"` as strings get
`strict="true"` read as "not strict", and the destructive op runs with no
recoverable version behind it.
"""
import unittest

from src.utils import destructive_hook


# A registered destructive action that is NOT in STRICT_DEFAULT_ACTIONS, so the
# only thing that can turn strict mode on here is the caller's own flag.
ROUTINE = ("timeline", "add_track")


class StrictFlagSpelling(unittest.TestCase):
    def test_true_spellings_opt_in(self) -> None:
        for value in (True, "true", "True", " true ", "1", 1, "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(destructive_hook.is_strict_required(
                    *ROUTINE, {"strict": value},
                ))

    def test_false_spellings_stay_out(self) -> None:
        for value in (False, "false", "False", "0", 0, "no", "off"):
            with self.subTest(value=value):
                self.assertFalse(destructive_hook.is_strict_required(
                    *ROUTINE, {"strict": value},
                ))

    def test_absent_flag_stays_out(self) -> None:
        self.assertFalse(destructive_hook.is_strict_required(*ROUTINE, {"clip_id": "x"}))
        self.assertFalse(destructive_hook.is_strict_required(*ROUTINE, None))


class StrictStringOptInReachesTheWrapper(unittest.TestCase):
    """End-to-end: the opt-in has to stop the handler, not just flip a bool."""

    def setUp(self) -> None:
        self.saved_provider = destructive_hook._PROVIDER

    def tearDown(self) -> None:
        destructive_hook._PROVIDER = self.saved_provider

    def test_string_opt_in_refuses_when_the_archive_context_is_missing(self) -> None:
        destructive_hook.register_project_root_provider(lambda: None)

        calls: list[str] = []

        @destructive_hook.destructive_op("timeline")
        def fake_timeline(action: str, params=None):
            calls.append(action)
            return {"success": True, "called_through": True}

        result = fake_timeline("add_track", {"track_type": "video", "strict": "true"})
        self.assertFalse(result["success"])
        error = result["error"]
        message = error.get("message", "") if isinstance(error, dict) else error
        self.assertIn("strict mode", message)
        self.assertEqual(calls, [], msg="the handler must not run once the caller opted into strict mode")


if __name__ == "__main__":
    unittest.main()
