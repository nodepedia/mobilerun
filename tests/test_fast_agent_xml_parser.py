import unittest

from mobilerun.agent.fast_agent.xml_parser import (
    extract_add_memory,
    format_tool_calls,
    parse_tool_calls,
)


class FastAgentXmlParserTest(unittest.TestCase):
    def test_drops_adjacent_exact_duplicate_tool_calls(self):
        text = """
I will tap the target.
<function_calls>
<invoke name="click_at">
<parameter name="x">128</parameter>
<parameter name="y">1560</parameter>
</invoke>
</function_calls>
<function_calls>
<invoke name="click_at">
<parameter name="x">128</parameter>
<parameter name="y">1560</parameter>
</invoke>
</function_calls>
"""

        thought, calls, err = parse_tool_calls(text, {"x": "number", "y": "number"})

        self.assertIn("I will tap", thought)
        self.assertIsNone(err)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "click_at")
        self.assertEqual(calls[0].parameters, {"x": 128, "y": 1560})

    def test_keeps_non_identical_sequential_calls(self):
        text = """
I will tap two different targets.
<function_calls>
<invoke name="click_at">
<parameter name="x">128</parameter>
<parameter name="y">1560</parameter>
</invoke>
<invoke name="click_at">
<parameter name="x">200</parameter>
<parameter name="y">1560</parameter>
</invoke>
</function_calls>
"""

        _, calls, err = parse_tool_calls(text, {"x": "number", "y": "number"})

        self.assertIsNone(err)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].parameters, {"x": 128, "y": 1560})
        self.assertEqual(calls[1].parameters, {"x": 200, "y": 1560})

    def test_keeps_identical_invokes_inside_one_block(self):
        text = """
I will press back twice.
<function_calls>
<invoke name="system_button">
<parameter name="button">back</parameter>
</invoke>
<invoke name="system_button">
<parameter name="button">back</parameter>
</invoke>
</function_calls>
"""

        _, calls, err = parse_tool_calls(text)

        self.assertIsNone(err)
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            [call.name for call in calls], ["system_button", "system_button"]
        )
        self.assertEqual(calls[0].parameters, {"button": "back"})
        self.assertEqual(calls[1].parameters, {"button": "back"})

    def test_keeps_intentional_mixed_batch(self):
        text = """
I will focus the field and type.
<function_calls>
<invoke name="click_at">
<parameter name="x">261</parameter>
<parameter name="y">1888</parameter>
</invoke>
<invoke name="type_text">
<parameter name="text">Android version</parameter>
<parameter name="clear">true</parameter>
</invoke>
</function_calls>
"""

        _, calls, err = parse_tool_calls(
            text,
            {"x": "number", "y": "number", "clear": "boolean"},
        )

        self.assertIsNone(err)
        self.assertEqual([call.name for call in calls], ["click_at", "type_text"])
        self.assertEqual(calls[0].parameters, {"x": 261, "y": 1888})
        self.assertEqual(
            calls[1].parameters,
            {"text": "Android version", "clear": True},
        )

    def test_duplicate_complete_blocks_execute_once(self):
        text = """
The task is done.
<function_calls>
<invoke name="complete">
<parameter name="success">true</parameter>
<parameter name="message">Done</parameter>
</invoke>
</function_calls>
<function_calls>
<invoke name="complete">
<parameter name="success">true</parameter>
<parameter name="message">Done</parameter>
</invoke>
</function_calls>
"""

        _, calls, err = parse_tool_calls(text, {"success": "boolean"})

        self.assertIsNone(err)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "complete")
        self.assertEqual(calls[0].parameters, {"success": True, "message": "Done"})

    def test_formatted_tool_calls_use_deduped_calls(self):
        text = """
Tap once.
<function_calls>
<invoke name="click_at">
<parameter name="x">128</parameter>
<parameter name="y">1560</parameter>
</invoke>
</function_calls>
<function_calls>
<invoke name="click_at">
<parameter name="x">128</parameter>
<parameter name="y">1560</parameter>
</invoke>
</function_calls>
"""

        _, calls, err = parse_tool_calls(text, {"x": "number", "y": "number"})
        formatted = format_tool_calls(calls)

        self.assertIsNone(err)
        self.assertEqual(formatted.count('<invoke name="click_at">'), 1)
        self.assertIn('<parameter name="x">128</parameter>', formatted)
        self.assertIn('<parameter name="y">1560</parameter>', formatted)

    def test_extract_add_memory_basic(self):
        text = "I see the email.\n<add_memory>Meeting at 3pm Thursday Room 204</add_memory>\nNow I'll click reply."
        result = extract_add_memory(text)
        self.assertEqual(result, "Meeting at 3pm Thursday Room 204")

    def test_extract_add_memory_empty(self):
        text = "Just a thought with no memory tag."
        result = extract_add_memory(text)
        self.assertEqual(result, "")

    def test_extract_add_memory_whitespace(self):
        text = "<add_memory>  spaced content  </add_memory>"
        result = extract_add_memory(text)
        self.assertEqual(result, "spaced content")

    def test_extract_add_memory_multiline(self):
        text = """Some thought here.
<add_memory>
Line 1: Meeting at 3pm
Line 2: Room 204
</add_memory>
Tool calls follow."""
        result = extract_add_memory(text)
        self.assertIn("Meeting at 3pm", result)
        self.assertIn("Room 204", result)

    def test_extract_add_memory_with_tool_calls(self):
        text = """I see the password field.
<add_memory>Username is admin@test.com</add_memory>
<function_calls>
<invoke name="click"><parameter name="index">5</parameter></invoke>
</function_calls>"""
        thought, calls, err = parse_tool_calls(text, {"index": "number"})
        memory = extract_add_memory(thought)
        self.assertIsNone(err)
        self.assertEqual(memory, "Username is admin@test.com")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "click")

    def test_extract_add_memory_multiple_blocks(self):
        text = """I found two important things on this screen.
<add_memory>User email is a@example.com</add_memory>
<add_memory>Verification code is 123456</add_memory>"""
        result = extract_add_memory(text)
        self.assertIn("User email is a@example.com", result)
        self.assertIn("Verification code is 123456", result)

    # -- parse_error / regex fallback tests -----------------------------------

    def test_no_function_calls_returns_none_error(self):
        text = "Just a thought, no tool calls."
        _, calls, err = parse_tool_calls(text)
        self.assertEqual(calls, [])
        self.assertIsNone(err)

    def test_malformed_xml_returns_parse_error(self):
        """Completely broken XML with <function_calls> tags but no salvageable invokes."""
        text = """I'll do something.
<function_calls>
<<broken<<< nonsense >>>
</function_calls>"""
        _, calls, err = parse_tool_calls(text)
        self.assertEqual(calls, [])
        self.assertIsNotNone(err)
        self.assertIn("could not be parsed", err)

    def test_corrupted_parameter_tag_recovered_by_fallback(self):
        """Broken tag names inside <invoke> are recovered by regex fallback.

        Simulates the DSML-token-leak corruption observed in production logs:
        <parameter ...> becomes <DSML ...> for some parameters.
        """
        text = """I'll swipe up.
<function_calls>
<invoke name="swipe">
<parameter name="coordinate">[360, 1200]</parameter>
<DSML name="coordinate2">[360, 400]</DSML>
<parameter name="duration">1.0</parameter>
</invoke>
</function_calls>"""
        _, calls, err = parse_tool_calls(text)

        # Fallback recovers the tool call and the two well-formed params
        # (the corrupted <DSML> tag is lost, but parsing does not fail)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "swipe")
        self.assertIn("coordinate", calls[0].parameters)
        self.assertIn("duration", calls[0].parameters)

    def test_missing_close_tag_uses_fallback(self):
        """Missing </invoke> should still be recovered by the fallback."""
        text = """Click it.
<function_calls>
<invoke name="click">
<parameter name="index">5</parameter>
</function_calls>"""
        _, calls, err = parse_tool_calls(text, {"index": "number"})

        # Should recover the call via fallback even though </invoke> is missing
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "click")
        self.assertEqual(calls[0].parameters, {"index": 5})

    def test_completely_garbled_returns_error(self):
        """Completely garbled content inside <function_calls> yields parse_error."""
        text = """Doing things.
<function_calls>
this is not xml at all, just random text with < and > symbols everywhere
</function_calls>"""
        _, calls, err = parse_tool_calls(text)
        self.assertEqual(calls, [])
        self.assertIsNotNone(err)

    def test_partial_corruption_recovers_valid_invokes(self):
        """When one invoke is corrupted but another is valid, recover the valid one."""
        text = """Two actions.
<function_calls>
<invoke name="click">
<parameter name="index">3</parameter>
</invoke>
<invoke name="broken<<<
<DSML name="x">bad</DSML>
</invoke>
</function_calls>"""
        _, calls, err = parse_tool_calls(text, {"index": "number"})

        # At least the first valid invoke should be recovered
        self.assertGreaterEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "click")
        self.assertEqual(calls[0].parameters, {"index": 3})


if __name__ == "__main__":
    unittest.main()
