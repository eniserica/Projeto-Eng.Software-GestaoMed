import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as app_module


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app_module.app.test_client()

    @patch("app.register_user")
    def test_registration_saves_password_hash(self, register_user):
        response = self.client.post(
            "/cadastro",
            data={
                "tipo": "paciente",
                "nome": "Ana Silva",
                "email": "ana@example.com",
                "senha": "senha-segura-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        register_user.assert_called_once()
        args = register_user.call_args.args
        self.assertEqual(args[:2], ("Ana Silva", "ana@example.com"))
        self.assertNotEqual(args[2], "senha-segura-123")

    @patch("app.register_user")
    def test_public_registration_cannot_create_administrator(self, register_user):
        response = self.client.post(
            "/cadastro",
            data={
                "tipo": "administrador",
                "nome": "Ana Silva",
                "email": "ana@example.com",
                "senha": "senha-segura-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"create_admin.py", response.data)
        register_user.assert_not_called()

    @patch("app.authenticate_user")
    def test_valid_login_starts_session_and_redirects(self, authenticate_user):
        authenticate_user.return_value = {
            "id": 7,
            "nome": "Ana Silva",
            "tipo": "paciente",
            "senha_hash": generate_password_hash("senha-segura-123"),
            "ativo": True,
        }

        response = self.client.post(
            "/login",
            data={
                "tipo": "paciente",
                "email": "ana@example.com",
                "senha": "senha-segura-123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/paciente")
        with self.client.session_transaction() as user_session:
            self.assertEqual(user_session["usuario_id"], 7)
            self.assertEqual(user_session["tipo"], "paciente")

    def test_private_area_requires_login(self):
        response = self.client.get("/paciente")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_patient_cannot_access_doctor_area(self):
        with self.client.session_transaction() as user_session:
            user_session["usuario_id"] = 7
            user_session["tipo"] = "paciente"

        response = self.client.get("/medico")

        self.assertEqual(response.status_code, 403)

    def test_admin_dashboard_renders_for_admin(self):
        with self.client.session_transaction() as user_session:
            user_session["usuario_id"] = 1
            user_session["tipo"] = "administrador"
            user_session["nome"] = "Admin"

        response = self.client.get("/administrador")

        self.assertEqual(response.status_code, 200)

    def test_logout_clears_session(self):
        with self.client.session_transaction() as user_session:
            user_session["usuario_id"] = 7
            user_session["tipo"] = "paciente"

        response = self.client.get("/logout")

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as user_session:
            self.assertNotIn("usuario_id", user_session)


if __name__ == "__main__":
    unittest.main()
