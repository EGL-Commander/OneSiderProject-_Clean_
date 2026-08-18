from unittest.mock import patch
import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from projects.models import Project
from purchases.models import Purchase

from .views import _confirm_purchase

from django.core import mail


class ConfirmPurchaseIdempotencyTests(TestCase):
    """
    Regression tests for the bug the payment flow used to have: calling
    the success path twice (e.g. buyer refreshes payment_success, or the
    webhook and the browser callback both arrive) must NOT mark the
    purchase successful twice or double-count purchases_count.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", password="pass1234"
        )

        self.project = Project.objects.create(
            title="Sample Project",
            short_description="A test project",
            description="Full description",
            project_type="web",
            price=499,
            cloud_storage_type="gdrive",
            cloud_file_id="fake-id",
        )

        self.purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            status="pending",
            razorpay_payment_link_id="plink_test123",
        )

    def test_first_confirmation_marks_success_and_increments_count(self):
        _confirm_purchase(self.purchase.id, "pay_test123")

        self.purchase.refresh_from_db()
        self.project.refresh_from_db()

        self.assertEqual(self.purchase.status, "success")
        self.assertEqual(self.purchase.razorpay_payment_id, "pay_test123")
        self.assertEqual(self.project.purchases_count, 1)

    def test_second_confirmation_is_a_no_op(self):
        # Simulates the webhook and the browser callback both firing for
        # the same payment - this must not double the purchase count.
        _confirm_purchase(self.purchase.id, "pay_test123")
        _confirm_purchase(self.purchase.id, "pay_test123")

        self.purchase.refresh_from_db()
        self.project.refresh_from_db()

        self.assertEqual(self.purchase.status, "success")
        self.assertEqual(self.project.purchases_count, 1)


@override_settings(RAZORPAY_WEBHOOK_SECRET="test-secret")
class RazorpayWebhookTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer2", password="pass1234"
        )

        self.project = Project.objects.create(
            title="Another Project",
            short_description="A test project",
            description="Full description",
            project_type="web",
            price=499,
            cloud_storage_type="gdrive",
            cloud_file_id="fake-id-2",
        )

        self.purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            status="pending",
            razorpay_payment_link_id="plink_webhook123",
        )

    def _payload(self):
        return {
            "event": "payment_link.paid",
            "payload": {
                "payment": {"entity": {"id": "pay_webhook123"}},
                "payment_link": {"entity": {"id": "plink_webhook123"}},
            },
        }

    @patch("payments.views.client")
    def test_valid_webhook_confirms_purchase(self, mock_client):
        # verify_webhook_signature raises on failure and returns None on
        # success, so we just need it to not raise.
        mock_client.utility.verify_webhook_signature.return_value = None

        response = self.client.post(
            "/payments/webhook/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="fake-signature",
        )

        self.assertEqual(response.status_code, 200)

        self.purchase.refresh_from_db()
        self.project.refresh_from_db()

        self.assertEqual(self.purchase.status, "success")
        self.assertEqual(self.project.purchases_count, 1)

    @patch("payments.views.client")
    def test_invalid_signature_is_rejected(self, mock_client):
        import razorpay
        mock_client.utility.verify_webhook_signature.side_effect = (
            razorpay.errors.SignatureVerificationError("bad signature")
        )

        response = self.client.post(
            "/payments/webhook/",
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_RAZORPAY_SIGNATURE="wrong-signature",
        )

        self.assertEqual(response.status_code, 400)

        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, "pending")

@override_settings(DEFAULT_FROM_EMAIL="noreply@onesider.in")
class PurchaseReceiptTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="receiptbuyer",
            email="receiptbuyer@example.com",
            password="pass1234",
        )

        self.project = Project.objects.create(
            title="Receipt Project",
            short_description="A test project",
            description="Full description",
            project_type="web",
            price=799,
            cloud_storage_type="gdrive",
            cloud_file_id="fake-receipt-id",
        )

        self.purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            status="pending",
            razorpay_payment_link_id="plink_receipt123",
        )

    def test_receipt_sent_after_successful_purchase(self):
        with self.captureOnCommitCallbacks(execute=True):
            _confirm_purchase(
                self.purchase.id,
                "pay_receipt123",
            )

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        self.assertEqual(
            email.to,
            ["receiptbuyer@example.com"],
        )

        self.assertIn(
            "Receipt Project",
            email.subject,
        )

        self.assertIn(
            str(self.purchase.id),
            email.body,
        )

    def test_receipt_not_sent_twice(self):
        with self.captureOnCommitCallbacks(execute=True):
            _confirm_purchase(
                self.purchase.id,
                "pay_receipt123",
            )

        with self.captureOnCommitCallbacks(execute=True):
            _confirm_purchase(
                self.purchase.id,
                "pay_receipt123",
            )

        self.assertEqual(len(mail.outbox), 1)

    def test_missing_customer_email_does_not_break_purchase(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        with self.captureOnCommitCallbacks(execute=True):
            _confirm_purchase(
                self.purchase.id,
                "pay_receipt123",
            )

        self.purchase.refresh_from_db()

        self.assertEqual(
            self.purchase.status,
            "success",
        )

        self.assertEqual(len(mail.outbox), 0)

class PurchaseStatusTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="statusbuyer",
            password="pass1234",
        )

        self.project = Project.objects.create(
            title="Status Project",
            short_description="A test project",
            description="Full description",
            project_type="web",
            price=299,
            cloud_storage_type="gdrive",
            cloud_file_id="fake-status-id",
        )

    def test_purchase_is_stored_as_pending(self):
        purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            razorpay_payment_link_id="plink_status123",
        )

        purchase.refresh_from_db()

        self.assertEqual(purchase.status, "pending")

    def test_purchase_can_be_stored_as_failed(self):
        purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            status="failed",
            razorpay_payment_link_id="plink_failed123",
        )

        purchase.refresh_from_db()

        self.assertEqual(purchase.status, "failed")

    def test_purchase_can_be_stored_as_success(self):
        purchase = Purchase.objects.create(
            user=self.user,
            project=self.project,
            status="success",
            razorpay_payment_link_id="plink_success123",
            razorpay_payment_id="pay_success123",
        )

        purchase.refresh_from_db()

        self.assertEqual(purchase.status, "success")
        self.assertEqual(
            purchase.razorpay_payment_id,
            "pay_success123",
        )