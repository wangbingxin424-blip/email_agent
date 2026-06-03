import os
import unittest
from unittest.mock import patch

from email_agent.config import MailConfig, OpenAIConfig, is_placeholder


class ConfigTests(unittest.TestCase):
    def test_placeholder_detection(self):
        self.assertTrue(is_placeholder("replace_with_your_aliyun_dashscope_key"))
        self.assertFalse(is_placeholder("real-looking-value"))

    def test_openai_config_rejects_placeholder_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "your_api_key_here"}, clear=True):
            with self.assertRaises(RuntimeError):
                OpenAIConfig.from_env()

    def test_mail_config_rejects_placeholder_auth_code(self):
        env = {
            "QQ_EMAIL_ADDRESS": "3243715276@qq.com",
            "QQ_EMAIL_AUTH_CODE": "replace_with_your_qq_mail_imap_authorization_code",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError):
                MailConfig.qq_from_env()


if __name__ == "__main__":
    unittest.main()
