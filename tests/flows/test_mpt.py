from urllib.parse import urljoin

import pytest
from responses import matchers

from adobe_vipm.flows.errors import MPTError
from adobe_vipm.flows.mpt import (
    complete_order,
    create_subscription,
    fail_order,
    get_buyer,
    get_seller,
    querying_order,
    update_order,
)


def test_fail_order(mpt_client, requests_mocker):
    """Test the call to switch an order to Failed."""
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/fail"),
        json={"failed": "order"},
        match=[
            matchers.json_params_matcher(
                {
                    "reason": "a-reason",
                },
            ),
        ],
    )

    failed_order = fail_order(mpt_client, "ORD-0000", "a-reason")
    assert failed_order == {"failed": "order"}


def test_fail_order_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to switch an order to Failed when it fails.
    """
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/fail"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Order not found"),
    )

    with pytest.raises(MPTError) as cv:
        fail_order(mpt_client, "ORD-0000", "a-reason")

    assert cv.value.status == 404


def test_get_buyer(mpt_client, requests_mocker):
    """Test the call to retrieve a buyer."""
    requests_mocker.get(
        urljoin(mpt_client.base_url, "buyers/BUY-0000"),
        json={"a": "buyer"},
    )

    buyer = get_buyer(mpt_client, "BUY-0000")
    assert buyer == {"a": "buyer"}


def test_get_buyer_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to to retrieve a buyer when it fails.
    """
    requests_mocker.get(
        urljoin(mpt_client.base_url, "buyers/BUY-0000"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Buyer not found"),
    )

    with pytest.raises(MPTError) as cv:
        get_buyer(mpt_client, "BUY-0000")

    assert cv.value.status == 404


def test_get_seller(mpt_client, requests_mocker):
    """Test the call to retrieve a seller."""
    requests_mocker.get(
        urljoin(mpt_client.base_url, "sellers/SEL-0000"),
        json={"a": "seller"},
    )

    seller = get_seller(mpt_client, "SEL-0000")
    assert seller == {"a": "seller"}


def test_get_seller_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to to retrieve a seller when it fails.
    """
    requests_mocker.get(
        urljoin(mpt_client.base_url, "sellers/SEL-0000"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Buyer not found"),
    )

    with pytest.raises(MPTError) as cv:
        get_seller(mpt_client, "SEL-0000")

    assert cv.value.status == 404


def test_querying_order(mpt_client, requests_mocker):
    """Test the call to switch an order to Query."""
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/query"),
        json={"querying": "order"},
        match=[
            matchers.json_params_matcher(
                {
                    "parameters": [{"name": "a-param", "value": "a-value"}],
                },
            ),
        ],
    )

    query_order = querying_order(
        mpt_client,
        "ORD-0000",
        {
            "parameters": [
                {"name": "a-param", "value": "a-value"},
            ],
        },
    )
    assert query_order == {"querying": "order"}


def test_querying_order_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to switch an order to Query when it fails.
    """
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/query"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Order not found"),
    )

    with pytest.raises(MPTError) as cv:
        querying_order(mpt_client, "ORD-0000", {})

    assert cv.value.status == 404


def test_update_order(mpt_client, requests_mocker):
    """Test the call to update an order."""
    requests_mocker.put(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000"),
        json={"updated": "order"},
        match=[
            matchers.json_params_matcher(
                {
                    "parameters": [{"name": "a-param", "value": "a-value"}],
                },
            ),
        ],
    )

    updated_order = update_order(
        mpt_client,
        "ORD-0000",
        {
            "parameters": [
                {"name": "a-param", "value": "a-value"},
            ],
        },
    )
    assert updated_order == {"updated": "order"}


def test_update_order_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to update an order when it fails.
    """
    requests_mocker.put(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Order not found"),
    )

    with pytest.raises(MPTError) as cv:
        update_order(mpt_client, "ORD-0000", {})

    assert cv.value.status == 404


def test_complete_order(mpt_client, requests_mocker):
    """Test the call to switch an order to Completed."""
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/complete"),
        json={"completed": "order"},
        match=[
            matchers.json_params_matcher(
                {
                    "template": {"id": "template_id"},
                },
            ),
        ],
    )

    completed_order = complete_order(
        mpt_client,
        "ORD-0000",
        "template_id",
    )
    assert completed_order == {"completed": "order"}


def test_complete_order_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to switch an order to Completed when it fails.
    """
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/complete"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Order not found"),
    )

    with pytest.raises(MPTError) as cv:
        complete_order(mpt_client, "ORD-0000", {})

    assert cv.value.status == 404


def test_create_subscription(mpt_client, requests_mocker):
    """Test the call to create a subscription."""
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/subscriptions"),
        json={"a": "subscription"},
        status=201,
        match=[
            matchers.json_params_matcher({"subscription": "payload"}),
        ],
    )

    subscription = create_subscription(
        mpt_client,
        "ORD-0000",
        {"subscription": "payload"},
    )
    assert subscription == {"a": "subscription"}


def test_create_subscription_error(mpt_client, requests_mocker, mpt_error_factory):
    """
    Test the call to create a subscription when it fails.
    """
    requests_mocker.post(
        urljoin(mpt_client.base_url, "commerce/orders/ORD-0000/subscriptions"),
        status=404,
        json=mpt_error_factory(404, "Not Found", "Order not found"),
    )

    with pytest.raises(MPTError) as cv:
        create_subscription(mpt_client, "ORD-0000", {})

    assert cv.value.status == 404