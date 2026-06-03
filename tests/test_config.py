import os
import unittest
from unittest.mock import patch

from email_agent.config import MailConfig, OpenAIConfig, guess_imap_host, is_placeholder


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

    def test_multi_account_config_is_preferred(self):
        env = {
            "QQ_EMAIL_ADDRESS": "legacy@qq.com",
            "QQ_EMAIL_AUTH_CODE": "legacy-code",
            "EMAIL_ACCOUNT_1_ADDRESS": "first@example.com",
            "EMAIL_ACCOUNT_1_AUTH_CODE": "first-code",
            "EMAIL_ACCOUNT_1_IMAP_HOST": "imap.example.com",
            "EMAIL_ACCOUNT_2_ADDRESS": "second@qq.com",
            "EMAIL_ACCOUNT_2_AUTH_CODE": "second-code",
        }
        with patch.dict(os.environ, env, clear=True):
            accounts = MailConfig.all_from_env()
        self.assertEqual([account.address for account in accounts], ["first@example.com", "second@qq.com"])
        self.assertEqual(accounts[0].host, "imap.example.com")
        self.assertEqual(accounts[1].host, "imap.qq.com")

    def test_guess_imap_host_for_common_domains(self):
        self.assertEqual(guess_imap_host("person@163.com"), "imap.163.com")
        self.assertEqual(guess_imap_host("person@example.com"), "imap.example.com")


if __name__ == "__main__":
    unittest.main()
