"""Routes with stubbed transports: nothing here reaches a network or a model."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from nnpredict import routes


class StubStream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        if isinstance(self.msg, Exception):
            raise self.msg
        return self.msg


class StubAnthropic:
    def __init__(self, msgs):
        self.msgs = list(msgs)
        self.requests = []
        self.messages = SimpleNamespace(stream=self.stream)

    def stream(self, **req):
        self.requests.append({**req, "messages": [dict(m) for m in req["messages"]]})
        return StubStream(self.msgs.pop(0))


def msg(text, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0,
                              cache_creation_input_tokens=0),
    )


class APIStatus(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status_code = status


class TestAnthropic(unittest.TestCase):
    def test_request_and_conversation(self):
        cfg = {"route": "anthropic_api", "model": "claude-opus-5-5", "effort": "high", "max_tokens": 64000}
        client = StubAnthropic([APIStatus(529), msg("", stop="refusal"), msg('{"a": 1}'), msg('{"a": 2}')])
        conv = routes.AnthropicConversation(cfg, client=client)
        r1 = conv.send("the prompt")
        self.assertTrue(r1.failed)
        self.assertIn("529", r1.error)
        r2 = conv.send("the prompt")
        self.assertTrue(r2.refusal)
        r3 = conv.send("the prompt")
        self.assertEqual(r3.text, '{"a": 1}')
        self.assertEqual(r3.usage["output_tokens"], 5)
        conv.send("follow-up")
        req = client.requests[-1]
        self.assertEqual(req["model"], "claude-opus-5-5")
        self.assertEqual(req["thinking"], {"type": "adaptive"})
        self.assertEqual(req["output_config"], {"effort": "high"})
        self.assertEqual(req["max_tokens"], 64000)
        self.assertNotIn("temperature", req)
        # failed tries leave no trace in the history; the follow-up carries the whole conversation
        self.assertEqual([m["role"] for m in req["messages"]], ["user", "assistant", "user"])
        self.assertEqual(req["messages"][0]["content"], "the prompt")

    def test_bad_request_is_fatal(self):
        conv = routes.AnthropicConversation({"model": "claude-opus-5-5"}, client=StubAnthropic([APIStatus(400)]))
        with self.assertRaises(routes.FatalRouteError):
            conv.send("x")

    def test_no_key_is_fatal(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(routes.FatalRouteError):
                routes.anthropic_key()


class TestOpenRouter(unittest.TestCase):
    def test_placeholder_refused(self):
        with self.assertRaises(routes.FatalRouteError):
            routes.OpenRouterConversation({"model": "PLACEHOLDER-openrouter-model-id"})

    def test_request(self):
        calls = []

        def transport(url, headers, body, timeout):
            calls.append((url, headers, json.loads(json.dumps(body))))
            if len(calls) == 1:
                return 503, {"error": {"message": "busy"}}
            return 200, {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                         "usage": {"prompt_tokens": 3}}

        conv = routes.OpenRouterConversation({"model": "vendor/model", "reasoning": "high", "max_tokens": 100},
                                             transport=transport)
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-not-a-key"}):
            self.assertTrue(conv.send("p").failed)
            r = conv.send("p")
        self.assertEqual(r.text, "{}")
        url, headers, body = calls[-1]
        self.assertEqual(url, routes.OPENROUTER_URL)
        self.assertEqual(body["model"], "vendor/model")
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual(body["messages"], [{"role": "user", "content": "p"}])


class TestClaudeCli(unittest.TestCase):
    def test_command_stdin_env_and_resume(self):
        calls = []

        def runner(cmd, stdin_text, timeout, cwd, env):
            calls.append((cmd, stdin_text, timeout, env))
            return 0, json.dumps({"type": "result", "is_error": False, "result": "{}", "session_id": "abc",
                                  "usage": {"output_tokens": 2}}), ""

        conv = routes.ClaudeCliConversation({"model": "haiku", "effort": "low", "timeout": 60}, runner=runner)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-not-a-key"}):
            r = conv.send("the prompt")
            conv.send("follow-up")
        conv.close()
        self.assertEqual(r.text, "{}")
        cmd, stdin_text, timeout, env = calls[0]
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertEqual(cmd[cmd.index("--model") + 1], "haiku")
        self.assertEqual(cmd[cmd.index("--effort") + 1], "low")
        self.assertNotIn("--resume", cmd)
        for flag in ("--safe-mode", "--strict-mcp-config", "--disable-slash-commands"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--system-prompt") + 1], routes.CLI_SYSTEM_PROMPT)
        self.assertEqual(conv.record_extra["cli_flags"], cmd[1:])
        self.assertEqual(stdin_text, "the prompt")
        self.assertEqual(timeout, 60)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(calls[1][0][-2:], ["--resume", "abc"])

    def test_error_reply(self):
        conv = routes.ClaudeCliConversation({"model": "haiku"}, runner=lambda *a: (-9, "", "timed out after 1 s"))
        r = conv.send("x")
        conv.close()
        self.assertTrue(r.failed)
        self.assertIn("timed out", r.error)

    def test_runner_kills_on_timeout(self):
        rc, out, err = routes.subprocess_runner(["sleep", "5"], "", 0.5, None, dict(os.environ))
        self.assertEqual(rc, -9)
        self.assertIn("timed out", err)


if __name__ == "__main__":
    unittest.main()
