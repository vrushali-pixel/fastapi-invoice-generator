# ─────────────────────────────────────────────
# CONCEPT: Unit Testing with pytest
#
# Unit tests test ONE thing in isolation.
# We test the SERVICE layer — business logic.
# We don't test the database or HTTP layer.
#
# CONCEPT: Mocking
# Our service calls repository functions (DB queries).
# In tests we don't want to hit a real database.
# We use unittest.mock to FAKE the DB responses.
# mock.patch replaces a real function with a fake one
# that returns whatever we tell it to return.
#
# This means tests:
# - Run instantly (no DB connection needed)
# - Work anywhere (no PostgreSQL required)
# - Test ONLY the business logic
# ─────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock
from service import (
    create_invoice_service,
    ProductNotFoundError,
    InsufficientStockError,
)


# ── Helpers ──────────────────────────────────

def make_product(id=1, name="Laptop", price=75000.0, stock=10):
    """Create a fake product dict — mimics what DB returns."""
    return {
        "id": id,
        "name": name,
        "current_price": price,
        "stock_quantity": stock,
    }


def make_invoice_request(product_id=1, quantity=1, customer="Test Customer"):
    """Create a fake invoice request object."""
    item = MagicMock()
    item.product_id = product_id
    item.quantity = quantity

    invoice = MagicMock()
    invoice.customer_name = customer
    invoice.items = [item]

    return invoice


# ── Tests ─────────────────────────────────────

class TestCreateInvoiceService:

    # CONCEPT: @patch decorator
    # Replaces the real function with a Mock during this test.
    # "repository.get_product_by_id" is replaced with mock_get_product.
    # We control what it returns using mock_get_product.return_value.
    @patch("service.insert_invoice_item")
    @patch("service.reduce_product_stock")
    @patch("service.insert_invoice")
    @patch("service.get_product_by_id")
    def test_successful_invoice_creation(
        self, mock_get_product, mock_insert_invoice,
        mock_reduce_stock, mock_insert_item
    ):
        """
        WHAT: create_invoice_service returns correct invoice data
        WHEN: product exists and has sufficient stock
        """
        # Arrange — set up fake data
        mock_get_product.return_value = make_product(price=75000.0, stock=10)
        mock_insert_invoice.return_value = 1  # fake invoice_id
        cursor = MagicMock()
        invoice = make_invoice_request(quantity=2)

        # Act — call the function we're testing
        invoice_id, invoice_number, total = create_invoice_service(cursor, invoice)

        # Assert — check the results
        assert invoice_id == 1
        assert invoice_number.startswith("INV-")
        # 2 laptops × 75000 = 150000 + 18% tax = 177000
        assert total == 177000.0


    @patch("service.get_product_by_id")
    def test_raises_error_when_product_not_found(self, mock_get_product):
        """
        WHAT: ProductNotFoundError is raised
        WHEN: product_id doesn't exist in DB
        """
        # Arrange — DB returns None (product not found)
        mock_get_product.return_value = None
        cursor = MagicMock()
        invoice = make_invoice_request(product_id=999)

        # Act + Assert — expect this specific exception
        with pytest.raises(ProductNotFoundError) as exc_info:
            create_invoice_service(cursor, invoice)

        assert "999" in str(exc_info.value)


    @patch("service.get_product_by_id")
    def test_raises_error_when_insufficient_stock(self, mock_get_product):
        """
        WHAT: InsufficientStockError is raised
        WHEN: requested quantity exceeds available stock
        """
        # Arrange — product exists but only 2 in stock
        mock_get_product.return_value = make_product(stock=2)
        cursor = MagicMock()
        # Request 5 but only 2 available
        invoice = make_invoice_request(quantity=5)

        # Act + Assert
        with pytest.raises(InsufficientStockError) as exc_info:
            create_invoice_service(cursor, invoice)

        assert "Insufficient stock" in str(exc_info.value)


    @patch("service.insert_invoice_item")
    @patch("service.reduce_product_stock")
    @patch("service.insert_invoice")
    @patch("service.get_product_by_id")
    def test_tax_calculation_is_correct(
        self, mock_get_product, mock_insert_invoice,
        mock_reduce_stock, mock_insert_item
    ):
        """
        WHAT: Tax is calculated at exactly 18%
        WHEN: invoice is created successfully
        """
        mock_get_product.return_value = make_product(price=1000.0, stock=10)
        mock_insert_invoice.return_value = 1
        cursor = MagicMock()
        invoice = make_invoice_request(quantity=1)

        invoice_id, invoice_number, total = create_invoice_service(cursor, invoice)

        # 1000 + 18% = 1180
        assert total == 1180.0


    @patch("service.insert_invoice_item")
    @patch("service.reduce_product_stock")
    @patch("service.insert_invoice")
    @patch("service.get_product_by_id")
    def test_invoice_number_format(
        self, mock_get_product, mock_insert_invoice,
        mock_reduce_stock, mock_insert_item
    ):
        """
        WHAT: Invoice number starts with INV-
        WHEN: invoice is created successfully
        """
        mock_get_product.return_value = make_product(stock=10)
        mock_insert_invoice.return_value = 1
        cursor = MagicMock()
        invoice = make_invoice_request()

        _, invoice_number, _ = create_invoice_service(cursor, invoice)

        assert invoice_number.startswith("INV-")
        # INV- followed by timestamp digits
        assert len(invoice_number) > 5


    @patch("service.insert_invoice_item")
    @patch("service.reduce_product_stock")
    @patch("service.insert_invoice")
    @patch("service.get_product_by_id")
    def test_stock_is_reduced_after_invoice(
        self, mock_get_product, mock_insert_invoice,
        mock_reduce_stock, mock_insert_item
    ):
        """
        WHAT: reduce_product_stock is called for each item
        WHEN: invoice is created successfully
        """
        mock_get_product.return_value = make_product(stock=10)
        mock_insert_invoice.return_value = 1
        cursor = MagicMock()
        invoice = make_invoice_request(quantity=3)

        create_invoice_service(cursor, invoice)

        # Verify stock reduction was called with correct args
        mock_reduce_stock.assert_called_once_with(cursor, 1, 3)


# ── Auth Utils Tests ──────────────────────────

class TestAuthUtils:

    def test_password_hash_is_not_plain_text(self):
        """
        WHAT: hashed password is different from plain password
        WHEN: hash_password is called
        """
        from auth_utils import hash_password
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert len(hashed) > 20

    def test_password_verification_correct(self):
        """
        WHAT: verify_password returns True
        WHEN: correct password is checked against its hash
        """
        from auth_utils import hash_password, verify_password
        plain = "mypassword123"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_password_verification_wrong(self):
        """
        WHAT: verify_password returns False
        WHEN: wrong password is checked against hash
        """
        from auth_utils import hash_password, verify_password
        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_access_token_contains_user_data(self):
        """
        WHAT: decoded token contains user email
        WHEN: access token is created
        """
        from auth_utils import create_access_token, decode_token
        token = create_access_token({"sub": "test@example.com"})
        payload = decode_token(token)
        assert payload["sub"] == "test@example.com"
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        """
        WHAT: refresh token has type 'refresh'
        WHEN: refresh token is created
        """
        from auth_utils import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "test@example.com"})
        payload = decode_token(token)
        assert payload["type"] == "refresh"