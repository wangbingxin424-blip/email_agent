import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_agent.accounts import add_mail_account, read_env_values


class AccountTests(unittest.TestCase):
    def test_add_account_migrates_legacy_qq(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env.local").write_text(
                "\n".join(
                    [
                        "QQ_EMAIL_ADDRESS=me@qq.com",
                        "QQ_EMAIL_AUTH_CODE=legacy-code",
                        "QQ_IMAP_HOST=imap.qq.com",
                    ]
                ),
                encoding="utf-8",
            )
            payload = {
                "provider": "163",
                "address": "client@163.com",
                "auth_code": "client-code",
                "label": "Client",
            }
            with patch.dict(os.environ, {}, clear=True):
                result = add_mail_account(payload, root=root)

            values = read_env_values(root / ".env.local")
            self.assertEqual(result["host"], "imap.163.com")
            self.assertEqual(values["EMAIL_ACCOUNT_1_ADDRESS"], "me@qq.com")
            self.assertEqual(values["EMAIL_ACCOUNT_2_ADDRESS"], "client@163.com")
            self.assertEqual(values["EMAIL_ACCOUNT_2_PROVIDER"], "163")

    def test_add_account_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env.local").write_text(
                "EMAIL_ACCOUNT_1_ADDRESS=client@126.com\nEMAIL_ACCOUNT_1_AUTH_CODE=old-code\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    add_mail_account(
                        {"provider": "126", "address": "client@126.com", "auth_code": "new-code"},
                        root=root,
                    )


if __name__ == "__main__":
    unittest.main()
