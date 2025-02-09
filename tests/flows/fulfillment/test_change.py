from datetime import UTC, datetime, timedelta
from operator import itemgetter

from adobe_vipm.adobe.constants import (
    ORDER_TYPE_NEW,
    ORDER_TYPE_PREVIEW,
    ORDER_TYPE_RETURN,
    STATUS_PENDING,
    STATUS_PROCESSED,
)
from adobe_vipm.adobe.errors import AdobeError
from adobe_vipm.flows.constants import (
    CANCELLATION_WINDOW_DAYS,
    MPT_ORDER_STATUS_COMPLETED,
    MPT_ORDER_STATUS_PROCESSING,
    TEMPLATE_NAME_CHANGE,
)
from adobe_vipm.flows.fulfillment import fulfill_order


def test_upsizing(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    items_factory,
    pricelist_items_factory,
):
    """
    Tests a change order in case of upsizing.
    Tests also that right templates are for processing and completed.
    """
    mocked_get_template = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        side_effect=[{"id": "TPL-0000"}, {"id": "TPL-1111"}],
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(subscription_id="a-sub-id"),
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    subscriptions = subscriptions_factory(lines=lines_factory(quantity=10))
    processing_change_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        subscriptions=subscriptions,
        order_parameters=[],
    )

    updated_change_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_change_order,
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=[],
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=pricelist_items_factory(),
    )
    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )

    mocked_process_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.set_processing_template",
    )

    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )
    fulfill_order(mocked_mpt_client, processing_change_order)

    authorization_id = processing_change_order["authorization"]["id"]

    mocked_process_order.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {"id": "TPL-0000"},
    )

    mocked_adobe_client.create_preview_order.assert_called_once_with(
        authorization_id,
        "a-client-id",
        processing_change_order["id"],
        processing_change_order["lines"],
    )

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )
    assert mocked_update_order.mock_calls[0].kwargs == {
        "externalIds": {
            "vendor": adobe_order["orderId"],
        },
    }
    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )
    assert mocked_update_order.mock_calls[1].kwargs == {
        "lines": [
            {
                "id": updated_change_order["lines"][0]["id"],
                "price": {
                    "unitPP": 1234.55,
                },
            }
        ],
    }
    assert mocked_update_order.mock_calls[2].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )
    assert mocked_update_order.mock_calls[2].kwargs == {
        "parameters": {
            "fulfillment": fulfillment_parameters_factory(
                customer_id="a-client-id",
                retry_count="0",
            ),
            "ordering": [],
        },
    }
    mocked_update_subscription.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        subscriptions[0]["id"],
        parameters={
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_order["lineItems"][0]["offerId"],
                },
            ],
        },
    )
    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {"id": "TPL-1111"},
    )

    assert mocked_get_template.mock_calls[0].args == (
        mocked_mpt_client,
        processing_change_order["agreement"]["product"]["id"],
        MPT_ORDER_STATUS_PROCESSING,
        TEMPLATE_NAME_CHANGE,
    )

    assert mocked_get_template.mock_calls[1].args == (
        mocked_mpt_client,
        processing_change_order["agreement"]["product"]["id"],
        MPT_ORDER_STATUS_COMPLETED,
        TEMPLATE_NAME_CHANGE,
    )


def test_upsizing_order_already_created_adobe_order_not_ready(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    adobe_order_factory,
):
    """
    Tests the processing of an change order (upsizing) that has been placed in the previous
    attemp and still pending.
    """
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    adobe_order = adobe_order_factory(ORDER_TYPE_NEW, status=STATUS_PENDING)

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )
    fulfill_order(mocked_mpt_client, order)

    mocked_adobe_client.get_subscription.assert_not_called()
    mocked_update_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        parameters={
            "fulfillment": fulfillment_parameters_factory(
                retry_count="1",
                customer_id="a-client-id",
            ),
            "ordering": [],
        },
    )
    mocked_complete_order.assert_not_called()


def test_upsizing_create_adobe_preview_order_error(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    adobe_api_error_factory,
):
    """
    Tests the processing of a change order (upsizing) when the Adobe preview order
    creation fails. The change order will be failed.
    """
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_error = AdobeError(
        adobe_api_error_factory("9999", "Error while creating a preview order")
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.side_effect = adobe_error
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    mocked_fail_order = mocker.patch("adobe_vipm.flows.fulfillment.shared.fail_order")

    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
    )
    fulfill_order(mocked_mpt_client, order)

    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        str(adobe_error),
    )


def test_downsizing(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    items_factory,
    pricelist_items_factory,
):
    """
    Tests the processing of a change order (downsizing) including:
        * search adobe orders by sku that must be referenced in return orders
        * adobe return orders creation
        * adobe preview order creation
        * adobe new order creation
        * order completion
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        return_value={"id": "TPL-1111"},
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    order_to_return = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        order_id="P0000000",
    )
    adobe_return_order = adobe_order_factory(
        ORDER_TYPE_RETURN,
        status=STATUS_PROCESSED,
    )
    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(subscription_id="a-sub-id"),
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.return_value = [
        (order_to_return, order_to_return["lineItems"][0], None),
    ]
    mocked_adobe_client.create_return_order.return_value = adobe_return_order
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    subscriptions = subscriptions_factory(lines=lines_factory(quantity=20))

    updated_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    processing_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
    )

    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_order,
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=[],
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=pricelist_items_factory(),
    )
    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )

    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )
    fulfill_order(mocked_mpt_client, processing_order)

    authorization_id = processing_order["authorization"]["id"]

    mocked_adobe_client.create_return_order.assert_called_once_with(
        authorization_id,
        "a-client-id",
        order_to_return,
        order_to_return["lineItems"][0],
    )

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[0].kwargs == {
        "parameters": processing_order["parameters"],
    }

    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[1].kwargs == {
        "externalIds": {
            "vendor": adobe_order["orderId"],
        },
    }

    assert mocked_update_order.mock_calls[2].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[2].kwargs == {
        "lines": [
            {
                "id": updated_order["lines"][0]["id"],
                "price": {
                    "unitPP": 1234.55,
                },
            }
        ],
    }

    mocked_update_subscription.assert_called_once_with(
        mocked_mpt_client,
        processing_order["id"],
        subscriptions[0]["id"],
        parameters={
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_order["lineItems"][0]["offerId"],
                },
            ],
        },
    )

    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_order["id"],
        {"id": "TPL-1111"},
    )
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.assert_called_once_with(
        authorization_id,
        "a-client-id",
        processing_order["lines"][0]["item"]["externalIds"]["vendor"],
        processing_order["lines"][0]["id"],
    )


def test_downsizing_return_order_exists(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    items_factory,
    pricelist_items_factory,
):
    """
    Tests the processing of a change order (downsizing) when the return order
    has already been created in Adobe.
    The return order will not be placed again.
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        return_value={"id": "TPL-1111"},
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    order_to_return = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        order_id="P0000000",
    )
    adobe_return_order = adobe_order_factory(
        ORDER_TYPE_RETURN,
        status=STATUS_PROCESSED,
    )
    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(subscription_id="a-sub-id"),
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.return_value = [
        (order_to_return, order_to_return["lineItems"][0], adobe_return_order),
    ]
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order

    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    subscriptions = subscriptions_factory(lines=lines_factory(quantity=20))

    processing_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
    )

    updated_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_order,
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=[],
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=pricelist_items_factory(),
    )
    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    fulfill_order(mocked_mpt_client, processing_order)

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[0].kwargs == {
        "parameters": processing_order["parameters"],
    }

    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[1].kwargs == {
        "externalIds": {
            "vendor": adobe_order["orderId"],
        },
    }
    assert mocked_update_order.mock_calls[2].args == (
        mocked_mpt_client,
        processing_order["id"],
    )
    assert mocked_update_order.mock_calls[2].kwargs == {
        "lines": [
            {
                "id": updated_order["lines"][0]["id"],
                "price": {
                    "unitPP": 1234.55,
                },
            }
        ]
    }
    mocked_update_subscription.assert_called_once_with(
        mocked_mpt_client,
        processing_order["id"],
        subscriptions[0]["id"],
        parameters={
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_order["lineItems"][0]["offerId"],
                },
            ],
        },
    )

    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_order["id"],
        {"id": "TPL-1111"},
    )
    mocked_adobe_client.create_return_order.assert_not_called()


def test_downsizing_return_order_pending(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
):
    """
    Tests the processing of a change order (downsizing) when the return order
    has already been created in Adobe but it is still pending.
    The return order will not be placed again.
    The new order will not be placed yet.
    """
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    order_to_return = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        order_id="P0000000",
    )
    adobe_return_order = adobe_order_factory(
        ORDER_TYPE_RETURN,
        status=STATUS_PENDING,
    )
    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.return_value = [
        (order_to_return, order_to_return["lineItems"][0], adobe_return_order),
    ]

    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions_factory(lines=lines_factory(quantity=20)),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
    )
    fulfill_order(mocked_mpt_client, order)

    mocked_update_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        parameters={
            "fulfillment": fulfillment_parameters_factory(
                retry_count="1",
                customer_id="a-client-id",
            ),
            "ordering": [],
        },
    )
    mocked_complete_order.assert_not_called()
    mocked_adobe_client.create_return_order.assert_not_called()


def test_downsizing_new_order_pending(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    adobe_order_factory,
):
    """
    Tests the processing of a change order (downsizing) when the return order
    has already been created and processed by Adobe and the new order has been
    placed but is still pending.
    The return order will not be placed again.
    The RetryCount parameter will be set to 1.
    """
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PENDING,
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=order,
    )

    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )
    fulfill_order(mocked_mpt_client, order)

    mocked_adobe_client.create_return_order.assert_not_called()
    mocked_complete_order.assert_not_called()
    mocked_update_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        parameters={
            "fulfillment": fulfillment_parameters_factory(
                retry_count="1",
                customer_id="a-client-id",
            ),
            "ordering": [],
        },
    )


def test_downsizing_create_new_order_error(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_api_error_factory,
):
    """
    Tests the processing of a change order (downsizing) when the create new order
    returns an error.

    """
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    order_to_return = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        order_id="P0000000",
    )
    adobe_return_order = adobe_order_factory(
        ORDER_TYPE_RETURN,
        status=STATUS_PROCESSED,
    )
    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_error = AdobeError(adobe_api_error_factory(code=400, message="an error"))

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.return_value = [
        (order_to_return, order_to_return["lineItems"][0], None),
    ]
    mocked_adobe_client.create_return_order.return_value = adobe_return_order
    mocked_adobe_client.create_new_order.side_effect = adobe_error

    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )
    mocked_mpt_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=20,
            quantity=10,
        ),
        subscriptions=subscriptions_factory(lines=lines_factory(quantity=20)),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
    )

    mocked_fail_order = mocker.patch("adobe_vipm.flows.fulfillment.shared.fail_order")

    mocked_mpt_client = mocker.MagicMock()

    fulfill_order(mocked_mpt_client, order)

    mocked_fail_order.assert_called_once_with(
        mocked_mpt_client,
        order["id"],
        str(adobe_error),
    )


def test_mixed(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    adobe_subscription_factory,
    items_factory,
    pricelist_items_factory,
):
    """
    Tests a change order in case of upsizing + downsizing + new item + downsizing out of window.
    It includes:
        * return order creation for downsized item
        * Adobe subscription update for downsizing out of window
        * order creation for the three items
        * subscription creation for new item
        * subscription actual sku update for existing upsized items
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        return_value={"id": "TPL-1111"},
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_preview_order_items = (
        adobe_items_factory(
            line_number=1,
            offer_id="sku-downsized",
            quantity=8,
        )
        + adobe_items_factory(
            line_number=2,
            offer_id="sku-upsized",
            quantity=12,
        )
        + adobe_items_factory(
            line_number=3,
            offer_id="sku-new",
            quantity=5,
        )
    )

    adobe_order_items = (
        adobe_items_factory(
            line_number=1,
            offer_id="sku-downsized",
            quantity=8,
            subscription_id="sub-1",
        )
        + adobe_items_factory(
            line_number=2,
            offer_id="sku-upsized",
            quantity=12,
            subscription_id="sub-2",
        )
        + adobe_items_factory(
            line_number=3,
            offer_id="sku-new",
            quantity=5,
            subscription_id="sub-3",
        )
    )

    adobe_return_order_items = adobe_items_factory(
        line_number=1,
        offer_id="sku-downsized",
        quantity=10,
    )

    order_to_return = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        order_id="P0000000",
    )
    adobe_return_order = adobe_order_factory(
        ORDER_TYPE_RETURN,
        status=STATUS_PROCESSED,
        items=adobe_return_order_items,
    )

    adobe_preview_order = adobe_order_factory(
        ORDER_TYPE_PREVIEW,
        items=adobe_preview_order_items,
    )
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_order_items,
    )

    adobe_sub_downsized_to_update = adobe_subscription_factory(
        subscription_id="sub-1",
        offer_id="sku-downsized",
    )

    adobe_sub_upsized_to_update = adobe_subscription_factory(
        subscription_id="sub-2",
        offer_id="sku-upsized",
    )

    adobe_new_sub = adobe_subscription_factory(
        subscription_id="sub-3",
        offer_id="sku-new",
    )

    adobe_sub_to_update = adobe_subscription_factory(
        subscription_id="sub-4",
        offer_id="sku-downsize-out",
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.search_new_and_returned_orders_by_sku_line_number.return_value = [
        (order_to_return, order_to_return["lineItems"][0], None),
    ]
    mocked_adobe_client.create_return_order.return_value = adobe_return_order
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocked_adobe_client.create_preview_renewal.return_value = {
        "lineItems": [
            {
                "subscriptionId": "sub-4",
                "offerId": "sku-downsize-out-full-sku",
            },
        ],
    }
    mocked_adobe_client.get_subscription.side_effect = [
        adobe_sub_to_update,
        adobe_sub_downsized_to_update,
        adobe_sub_upsized_to_update,
        adobe_new_sub,
    ]
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    downsizing_items = lines_factory(
        line_id=1,
        item_id=1,
        old_quantity=10,
        quantity=8,
        external_vendor_id="sku-downsized",
    )
    upsizing_items = lines_factory(
        line_id=2,
        item_id=2,
        old_quantity=10,
        quantity=12,
        external_vendor_id="sku-upsized",
    )
    new_items = lines_factory(
        line_id=3,
        item_id=3,
        name="New cool product",
        old_quantity=0,
        quantity=5,
        external_vendor_id="sku-new",
    )

    downsizing_items_out_of_window = lines_factory(
        line_id=4,
        item_id=4,
        old_quantity=10,
        quantity=8,
        external_vendor_id="sku-downsize-out",
    )

    order_items = (
        upsizing_items + new_items + downsizing_items + downsizing_items_out_of_window
    )

    preview_order_items = upsizing_items + new_items + downsizing_items

    order_subscriptions = (
        subscriptions_factory(
            subscription_id="SUB-001",
            adobe_subscription_id="sub-1",
            lines=lines_factory(
                line_id=1,
                item_id=1,
                quantity=10,
                external_vendor_id="sku-downsized",
            ),
        )
        + subscriptions_factory(
            subscription_id="SUB-002",
            adobe_subscription_id="sub-2",
            lines=lines_factory(
                line_id=2,
                item_id=2,
                quantity=10,
                external_vendor_id="sku-upsized",
            ),
        )
        + subscriptions_factory(
            subscription_id="SUB-004",
            adobe_subscription_id="sub-4",
            lines=lines_factory(
                line_id=4,
                item_id=4,
                quantity=10,
                external_vendor_id="sku-downsize-out",
            ),
            start_date=datetime.now(UTC) - timedelta(days=CANCELLATION_WINDOW_DAYS + 1),
        )
    )

    processing_change_order = order_factory(
        order_type="Change",
        lines=order_items,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        subscriptions=order_subscriptions,
    )

    updated_change_order = order_factory(
        order_type="Change",
        lines=order_items,
        subscriptions=order_subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_mpt_client = mocker.MagicMock()
    mocked_update_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_change_order,
    )

    mocked_create_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.create_subscription",
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=[],
    )
    price_items = pricelist_items_factory(1, "sku-downsized", 1234.55)
    price_items.extend(pricelist_items_factory(2, "sku-upsized", 4321.55))
    price_items.extend(pricelist_items_factory(3, "sku-new", 9876.54))
    price_items.extend(pricelist_items_factory(4, "sku-downsize-out", 6789.55))
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=price_items,
    )

    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )

    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    fulfill_order(mocked_mpt_client, processing_change_order)

    authorization_id = processing_change_order["authorization"]["id"]

    mocked_adobe_client.create_preview_order.assert_called_once_with(
        authorization_id,
        "a-client-id",
        processing_change_order["id"],
        preview_order_items,
    )
    mocked_adobe_client.update_subscription.assert_called_once_with(
        authorization_id,
        "a-client-id",
        "sub-4",
        quantity=8,
    )

    assert mocked_update_order.mock_calls[0].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )
    expected_lines = []
    for line in sorted(order_items, key=itemgetter("id")):
        if line["id"] == downsizing_items_out_of_window[0]["id"]:
            unit_pp = 6789.55
        else:
            unit_pp = line["price"]["unitPP"]

        expected_lines.append(
            {
                "id": line["id"],
                "price": {
                    "unitPP": unit_pp,
                },
            }
        )

    assert mocked_update_order.mock_calls[0].kwargs == {"lines": expected_lines}

    assert mocked_update_order.mock_calls[1].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )
    assert mocked_update_order.mock_calls[1].kwargs == {
        "parameters": processing_change_order["parameters"],
    }

    assert mocked_update_order.mock_calls[2].args == (
        mocked_mpt_client,
        processing_change_order["id"],
    )

    assert mocked_update_order.mock_calls[2].kwargs == {
        "externalIds": {
            "vendor": adobe_order["orderId"],
        },
    }

    mocked_create_subscription.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {
            "name": "Subscription for New cool product",
            "parameters": {
                "fulfillment": [
                    {
                        "externalId": "adobeSKU",
                        "value": adobe_new_sub["offerId"],
                    },
                ],
            },
            "externalIds": {"vendor": adobe_new_sub["subscriptionId"]},
            "lines": [
                {
                    "id": processing_change_order["lines"][1]["id"],
                },
            ],
            "startDate": adobe_new_sub["creationDate"],
            "commitmentDate": adobe_new_sub["renewalDate"],
        },
    )

    assert mocked_update_subscription.mock_calls[0].args == (
        mocked_mpt_client,
        processing_change_order["id"],
        order_subscriptions[2]["id"],
    )
    assert mocked_update_subscription.mock_calls[0].kwargs == {
        "parameters": {
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": "sku-downsize-out-full-sku",
                },
            ],
        },
    }

    assert mocked_update_subscription.mock_calls[1].args == (
        mocked_mpt_client,
        processing_change_order["id"],
        order_subscriptions[0]["id"],
    )
    assert mocked_update_subscription.mock_calls[1].kwargs == {
        "parameters": {
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_sub_downsized_to_update["offerId"],
                },
            ],
        },
    }

    assert mocked_update_subscription.mock_calls[2].args == (
        mocked_mpt_client,
        processing_change_order["id"],
        order_subscriptions[1]["id"],
    )
    assert mocked_update_subscription.mock_calls[2].kwargs == {
        "parameters": {
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_sub_upsized_to_update["offerId"],
                },
            ],
        },
    }

    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {"id": "TPL-1111"},
    )


def test_upsize_of_previously_downsized_out_of_win_without_new_order(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_subscription_factory,
):
    """
    Tests a change order in case of an upsizing after a previous downsizing change
    order fulfilled outside the cancellation window.
    Only the renewal quantity of the subscription should be updated.
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        return_value={"id": "TPL-1111"},
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_sub_to_update = adobe_subscription_factory(
        subscription_id="sub-4",
        current_quantity=18,
        renewal_quantity=10,
    )

    mocked_adobe_client = mocker.MagicMock()

    mocked_adobe_client.get_subscription.return_value = adobe_sub_to_update
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    upsizing_items_out_of_window = lines_factory(
        line_id=4,
        old_quantity=10,
        quantity=18,
    )

    order_subscriptions = subscriptions_factory(
        subscription_id="SUB-004",
        adobe_subscription_id="sub-4",
        lines=lines_factory(
            line_id=4,
            quantity=10,
        ),
        start_date=datetime.now(UTC) - timedelta(days=CANCELLATION_WINDOW_DAYS + 1),
    )

    processing_change_order = order_factory(
        order_type="Change",
        lines=upsizing_items_out_of_window,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        subscriptions=order_subscriptions,
    )

    mocked_mpt_client = mocker.MagicMock()

    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    fulfill_order(mocked_mpt_client, processing_change_order)

    authorization_id = processing_change_order["authorization"]["id"]

    mocked_adobe_client.update_subscription.assert_called_once_with(
        authorization_id,
        "a-client-id",
        "sub-4",
        quantity=18,
    )

    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {"id": "TPL-1111"},
    )


def test_upsize_of_previously_downsized_out_of_win_with_new_order(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    adobe_subscription_factory,
    items_factory,
    pricelist_items_factory,
):
    """
    Tests a change order in case of an upsizing after a previous downsizing change
    order fulfilled outside the cancellation window and with a quantity that exceed
    the current.
    The renewal quantity of the subscription should not be updated because of the
    current quantity is equal to the auto renewal.
    """
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        return_value={"id": "TPL-1111"},
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_preview_order = adobe_order_factory(
        ORDER_TYPE_PREVIEW,
        items=adobe_items_factory(
            line_number=4,
            quantity=3,
        ),
    )
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(
            line_number=4,
            quantity=3,
            subscription_id="sub-4",
        ),
    )

    adobe_sub_to_update = adobe_subscription_factory(
        subscription_id="sub-4",
        current_quantity=18,
        renewal_quantity=18,
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocked_adobe_client.get_subscription.return_value = adobe_sub_to_update
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    upsizing_items_out_of_window = lines_factory(
        line_id=4,
        old_quantity=10,
        quantity=21,
    )

    order_subscriptions = subscriptions_factory(
        subscription_id="SUB-004",
        adobe_subscription_id="sub-4",
        lines=lines_factory(
            line_id=4,
            quantity=10,
        ),
        start_date=datetime.now(UTC) - timedelta(days=CANCELLATION_WINDOW_DAYS + 1),
    )

    processing_change_order = order_factory(
        order_type="Change",
        lines=upsizing_items_out_of_window,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        subscriptions=order_subscriptions,
    )

    updated_change_order = order_factory(
        order_type="Change",
        lines=upsizing_items_out_of_window,
        subscriptions=order_subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_mpt_client = mocker.MagicMock()

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_change_order,
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=[],
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=pricelist_items_factory(),
    )
    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )
    mocked_complete_order = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )

    fulfill_order(mocked_mpt_client, processing_change_order)

    authorization_id = processing_change_order["authorization"]["id"]

    mocked_adobe_client.create_preview_order.assert_called_once_with(
        authorization_id,
        "a-client-id",
        processing_change_order["id"],
        lines_factory(
            line_id=4,
            old_quantity=18,
            quantity=21,
        ),
    )

    mocked_adobe_client.update_subscription.assert_not_called()

    mocked_update_subscription.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        order_subscriptions[0]["id"],
        parameters={
            "fulfillment": [
                {
                    "externalId": "adobeSKU",
                    "value": adobe_order["lineItems"][0]["offerId"],
                },
            ],
        },
    )

    mocked_complete_order.assert_called_once_with(
        mocked_mpt_client,
        processing_change_order["id"],
        {"id": "TPL-1111"},
    )


def test_duplicate_items(mocker, order_factory, lines_factory):
    mocked_fail = mocker.patch(
        "adobe_vipm.flows.fulfillment.change.switch_order_to_failed",
    )
    mocked_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory() + lines_factory(),
    )

    fulfill_order(mocked_client, order)

    mocked_fail.assert_called_once_with(
        mocked_client,
        order,
        "The order cannot contain multiple lines for the same item: ITM-1234-1234-1234-0001.",
    )


def test_existing_items(mocker, order_factory, lines_factory):
    mocked_fail = mocker.patch(
        "adobe_vipm.flows.fulfillment.change.switch_order_to_failed",
    )
    mocked_client = mocker.MagicMock()

    order = order_factory(
        order_type="Change",
        lines=lines_factory(line_id=2, item_id=10),
    )

    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=order["agreement"])

    fulfill_order(mocked_client, order)

    mocked_fail.assert_called_once_with(
        mocked_client,
        order,
        "The order cannot contain new lines for an existing item: ITM-1234-1234-1234-0010.",
    )



def test_one_time_items(
    mocker,
    agreement,
    order_factory,
    lines_factory,
    fulfillment_parameters_factory,
    subscriptions_factory,
    adobe_order_factory,
    adobe_items_factory,
    items_factory,
    pricelist_items_factory,
):
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_template_or_default",
        side_effect=[{"id": "TPL-0000"}, {"id": "TPL-1111"}],
    )
    mocker.patch("adobe_vipm.flows.helpers.get_agreement", return_value=agreement)

    adobe_preview_order = adobe_order_factory(ORDER_TYPE_PREVIEW)
    adobe_order = adobe_order_factory(
        ORDER_TYPE_NEW,
        status=STATUS_PROCESSED,
        items=adobe_items_factory(subscription_id="a-sub-id"),
    )

    mocked_adobe_client = mocker.MagicMock()
    mocked_adobe_client.create_preview_order.return_value = adobe_preview_order
    mocked_adobe_client.create_new_order.return_value = adobe_order
    mocked_adobe_client.get_order.return_value = adobe_order
    mocker.patch(
        "adobe_vipm.flows.fulfillment.change.get_adobe_client",
        return_value=mocked_adobe_client,
    )

    subscriptions = subscriptions_factory(lines=lines_factory(quantity=10))
    processing_change_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        subscriptions=subscriptions,
        order_parameters=[],
    )

    updated_change_order = order_factory(
        order_type="Change",
        lines=lines_factory(
            old_quantity=10,
            quantity=20,
        ),
        subscriptions=subscriptions,
        fulfillment_parameters=fulfillment_parameters_factory(
            customer_id="a-client-id",
        ),
        order_parameters=[],
        external_ids={"vendor": adobe_order["orderId"]},
    )

    mocked_mpt_client = mocker.MagicMock()
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_order",
        return_value=updated_change_order,
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_items_by_skus",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_product_onetime_items_by_ids",
        return_value=items_factory(),
    )
    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.get_pricelist_items_by_product_items",
        return_value=pricelist_items_factory(),
    )
    mocked_update_subscription = mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.update_subscription",
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.set_processing_template",
    )

    mocker.patch(
        "adobe_vipm.flows.fulfillment.shared.complete_order",
    )
    fulfill_order(mocked_mpt_client, processing_change_order)


    mocked_update_subscription.assert_not_called()
