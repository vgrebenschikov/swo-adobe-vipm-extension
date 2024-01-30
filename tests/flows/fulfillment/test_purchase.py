import pytest

from adobe_vipm.adobe.constants import (
    ORDER_STATUS_DESCRIPTION,
    ORDER_TYPE_NEW,
    ORDER_TYPE_PREVIEW,
    STATUS_PENDING,
    STATUS_PROCESSED,
    UNRECOVERABLE_ORDER_STATUSES,
)
from adobe_vipm.adobe.errors import AdobeError
from adobe_vipm.flows.fulfillment import fulfill_order


def test_no_customer(
    mocker,
    settings,
    agreement,
    buyer,
    seller,
    order_factory,
    order_parameters_factory,
    fulfillment_parameters_factory,
    adobe_order_factory,
    adobe_items_factory,
    adobe_subscription_factory,
):
    """
    Tests the processing of a purchase order including:
        * customer creation
        * order creation
        * subscription creation
        * order completion
    """

    settings.EXTENSION_CONFIG["COMPLETED_TEMPLATE_ID"] = "TPL-1111"

    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocker.patch("adobe_vipm.flows.fulfillment.get_buyer", return_value=buyer)
    mocked_get_seller = mocker.patch("adobe_vipm.flows.fulfillment.get_seller", return_value=seller)
    mocked_create_customer_account = mocker.patch(
        "adobe_vipm.flows.fulfillment.create_customer_account",
        return_value=order_factory(
            fulfillment_parameters=fulfillment_parameters_factory(customer_id="a-client-id"),
        ),
    )

    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(subscription_id="a-sub-id"),
    )
    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)

    adobe_subscription = adobe_subscription_factory()

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocked_adobe_client.get_subscription.return_value = adobe_subscription
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.update_order",
        side_effect=[
            order_factory(
                fulfillment_parameters=fulfillment_parameters_factory(
                    customer_id="a-client-id",
                    retry_count="1",
                ),
                external_ids={"vendor": adobe_order["orderId"]},
            ),
            order_factory(
                fulfillment_parameters=fulfillment_parameters_factory(
                    customer_id="a-client-id",
                    retry_count="0",
                ),
                external_ids={"vendor": adobe_order["orderId"]},
            ),
        ],
    )
    mocked_create_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.create_subscription",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.complete_order",
    )

    order = order_factory()

    fulfill_order(mocked_mpt_client, order)

    seller_country = seller["address"]["country"]

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_create_customer_account.assert_called_once_with(
        mocked_mpt_client,
        seller_country,
        buyer,
        order,
    )
    mocked_adobe_client.create_preview_order.assert_called_once_with(
        seller_country,
        "a-client-id",
        order_factory(
            fulfillment_parameters=fulfillment_parameters_factory(customer_id="a-client-id")
        ),
    )

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        order["id"],
        {
            "externalIDs": {
                "vendor": adobe_order["orderId"],
            },
        },
    )
    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        order["id"],
        {
            "parameters": {
                "fulfillment": fulfillment_parameters_factory(
                    customer_id="a-client-id",
                    retry_count="0",
                ),
                "order": order_parameters_factory(),
            },
        },
    )
    mocked_create_subscription.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        {
            "name": "Subscription for Awesome product",
            "parameters": {
                "fulfillment": [
                    {
                        "name": "SubscriptionId",
                        "value": adobe_subscription["subscriptionId"],
                    },
                ],
            },
            "items": [
                {
                    "lineNumber": 1,
                },
            ],
            "startDate": adobe_subscription["creationDate"],
        },
    )
    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        "TPL-1111",
    )
    mocked_adobe_client.get_order.assert_called_once_with(
        seller_country, "a-client-id", adobe_order["orderId"]
    )
    mocked_adobe_client.get_subscription.assert_called_once_with(
        seller_country,
        "a-client-id",
        adobe_subscription["subscriptionId"],
    )


def test_customer_already_created(
    mocker,
    agreement,
    seller,
    order_factory,
    order_parameters_factory,
    fulfillment_parameters_factory,
    adobe_order_factory,
):
    """
    Tests the processing of a purchase order with the customer already created.
    Adobe returns that the order is still processing.
    """
    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocked_get_seller = mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_create_customer_account = mocker.patch(
        "adobe_vipm.flows.fulfillment.create_customer_account",
    )

    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_order = adobe_order_factory(ORDER_TYPE_NEW, status=STATUS_PENDING)

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.update_order",
        return_value=order_factory(
            fulfillment_parameters=fulfillment_parameters_factory(
                customer_id="a-client-id",
            ),
            external_ids={"vendor": adobe_order["orderId"]},
        ),
    )

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(customer_id="a-client-id")
    )

    fulfill_order(mocked_mpt_client, order)

    seller_country = seller["address"]["country"]

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_create_customer_account.assert_not_called()
    mocked_adobe_client.create_preview_order.assert_called_once_with(
        seller_country,
        "a-client-id",
        order_factory(
            fulfillment_parameters=fulfillment_parameters_factory(customer_id="a-client-id")
        ),
    )

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        order["id"],
        {
            "externalIDs": {
                "vendor": adobe_order["orderId"],
            },
        },
    )
    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        order["id"],
        {
            "parameters": {
                "fulfillment": fulfillment_parameters_factory(
                    customer_id="a-client-id",
                    retry_count="1",
                ),
                "order": order_parameters_factory(),
            },
        },
    )


def test_create_customer_fails(
    mocker,
    seller,
    order_factory,
):
    """
    Tests the processing of a purchase order. It fails on customer creation no
    order will be placed.
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_create_customer_account = mocker.patch(
        "adobe_vipm.flows.fulfillment.create_customer_account",
        return_value=None,
    )
    mocked_adobe_client = mocker.MagicMock()
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory()

    fulfill_order(mocked_mpt_client, order)

    mocked_create_customer_account.assert_called_once()
    mocked_adobe_client.create_preview_order.assert_not_called()
    mocked_adobe_client.create_new_order.assert_not_called()


def test_create_adobe_preview_order_error(
    mocker,
    seller,
    order_factory,
    fulfillment_parameters_factory,
    adobe_api_error_factory,
):
    """
    Tests the processing of a purchase order. It fails on adobe preview
    order creation. The purchase order will be failed.
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.create_customer_account",
        return_value=None,
    )

    adobe_error = AdobeError(
        adobe_api_error_factory("9999", "Error while creating a preview order")
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.side_effect = adobe_error
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    mocked_fail_order = mocker.patch("adobe_vipm.flows.fulfillment.fail_order")

    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(customer_id="a-client-id")
    )

    fulfill_order(mocked_mpt_client, order)

    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        str(adobe_error),
    )


def test_customer_and_order_already_created_adobe_order_not_ready(
    mocker,
    agreement,
    seller,
    order_factory,
    order_parameters_factory,
    fulfillment_parameters_factory,
):
    """
    Tests the continuation of processing a purchase order since in the
    previous attemp the order has been created but not still processed
    on Adobe side. The RetryCount fullfilment paramter must be incremented.
    The purchase order will not be completed and the processing will be stopped.
    """
    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocked_get_seller = mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.update_order",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.complete_order",
    )
    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = {"status": "1002"}
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        external_ids={"vendor": "an-order-id"},
    )

    fulfill_order(mocked_mpt_client, order)

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_adobe_client.get_subscription.assert_not_called()
    mocked_update_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        {
            "parameters": {
                "order": order_parameters_factory(),
                "fulfillment": fulfillment_parameters_factory(
                    customer_id="a-client-id",
                    retry_count="1",
                ),
            }
        },
    )
    mocked_complete_order.assert_not_called()


def test_customer_already_created_order_already_created_max_retries_reached(
    mocker,
    agreement,
    seller,
    order_factory,
    fulfillment_parameters_factory,
):
    """
    Tests the processing of a purchase order when the allowed maximum number of
    attemps has been reached.
    The order will be failed with a message saying that this maximum has been reached.
    """
    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocked_get_seller = mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_fail_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.fail_order",
    )
    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = {"status": "1002"}
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
            retry_count=10,
        ),
        external_ids={"vendor": "an-order-id"},
    )

    fulfill_order(mocked_mpt_client, order)

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_adobe_client.get_subscription.assert_not_called()
    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        "Max processing attemps reached (10).",
    )


@pytest.mark.parametrize(
    "order_status",
    UNRECOVERABLE_ORDER_STATUSES,
)
def test_customer_already_created_order_already_created_unrecoverable_status(
    mocker,
    agreement,
    seller,
    order_factory,
    fulfillment_parameters_factory,
    order_status,
):
    """
    Tests the processing of a purchase order when the Adobe order has been processed unsuccessfully.
    The purchase order will be failed and with a message that describe the error returned by Adobe.
    """
    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocked_get_seller = mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_fail_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.fail_order",
    )
    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = {"status": order_status}
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
            retry_count=10,
        ),
        external_ids={"vendor": "an-order-id"},
    )

    fulfill_order(mocked_mpt_client, order)

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_adobe_client.get_subscription.assert_not_called()
    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        ORDER_STATUS_DESCRIPTION[order_status],
    )


def test_customer_already_created_order_already_created_unexpected_status(
    mocker,
    agreement,
    seller,
    order_factory,
    fulfillment_parameters_factory,
):
    """
    Tests the processing of a purchase order when the Adobe order has been processed unsuccessfully
    and the status of the order returned by Adobe is not documented.
    The purchase order will be failed and with a message that explain that Adobe returned an
    unexpected error.
    """
    mocker.patch("adobe_vipm.flows.fulfillment.get_agreement", return_value=agreement)
    mocked_get_seller = mocker.patch(
        "adobe_vipm.flows.fulfillment.get_seller",
        return_value=seller,
    )
    mocked_fail_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.fail_order",
    )
    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = {"status": "9999"}
    mocker.patch(
        "adobe_vipm.flows.fulfillment.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
            retry_count=10,
        ),
        external_ids={"vendor": "an-order-id"},
    )

    fulfill_order(mocked_mpt_client, order)

    mocked_get_seller.assert_called_once_with(mocked_mpt_client, seller["id"])
    mocked_adobe_client.get_subscription.assert_not_called()
    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        "Unexpected status (9999) received from Adobe.",
    )