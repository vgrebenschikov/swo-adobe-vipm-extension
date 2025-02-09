import logging

from adobe_vipm.adobe.config import get_config
from adobe_vipm.adobe.errors import AdobeAPIError, AdobeHttpError
from adobe_vipm.flows.airtable import (
    STATUS_RUNNING,
    STATUS_SYNCHRONIZED,
    get_transfer_by_authorization_membership_or_customer,
)
from adobe_vipm.flows.constants import (
    ERR_ADOBE_MEMBERSHIP_ID,
    ERR_ADOBE_MEMBERSHIP_ID_ITEM,
    ERR_ADOBE_MEMBERSHIP_NOT_FOUND,
    ERR_ADOBE_UNEXPECTED_ERROR,
    PARAM_MEMBERSHIP_ID,
)
from adobe_vipm.flows.mpt import get_product_items_by_skus
from adobe_vipm.flows.utils import (
    get_adobe_membership_id,
    get_order_line_by_sku,
    get_ordering_parameter,
    get_partial_sku,
    get_transfer_item_sku_by_subscription,
    is_transferring_item_expired,
    set_ordering_parameter_error,
)

logger = logging.getLogger(__name__)


def add_lines_to_order(mpt_client, order, adobe_object, quantity_field):
    returned_skus = [
        get_partial_sku(item["offerId"])
        for item in adobe_object["items"]
        if not is_transferring_item_expired(item)
    ]

    items_map = {
        item["externalIds"]["vendor"]: item
        for item in get_product_items_by_skus(
            mpt_client, order["agreement"]["product"]["id"], returned_skus
        )
    }
    valid_adobe_lines = []
    for adobe_line in adobe_object["items"]:
        if is_transferring_item_expired(adobe_line):
            continue
        item = items_map.get(get_partial_sku(adobe_line["offerId"]))
        if not item:
            param = get_ordering_parameter(order, PARAM_MEMBERSHIP_ID)
            order = set_ordering_parameter_error(
                order,
                PARAM_MEMBERSHIP_ID,
                ERR_ADOBE_MEMBERSHIP_ID_ITEM.to_dict(
                    title=param["name"],
                    item_sku=get_partial_sku(adobe_line["offerId"]),
                ),
            )
            return True, order, adobe_object
        current_line = get_order_line_by_sku(
            order, get_partial_sku(adobe_line["offerId"])
        )
        if current_line:
            current_line["quantity"] = adobe_line[quantity_field]
        else:
            order["lines"].append(
                {
                    "item": item,
                    "quantity": adobe_line[quantity_field],
                    "oldQuantity": 0,
                },
            )

        valid_adobe_lines.append(adobe_line)

    lines = [
        line
        for line in order["lines"]
        if line["item"]["externalIds"]["vendor"] in returned_skus
    ]
    order["lines"] = lines

    return False, order, {"items": valid_adobe_lines}


def validate_transfer_not_migrated(mpt_client, adobe_client, order):
    authorization_id = order["authorization"]["id"]
    membership_id = get_adobe_membership_id(order)
    transfer_preview = None

    try:
        transfer_preview = adobe_client.preview_transfer(
            authorization_id,
            membership_id,
        )
    except AdobeAPIError as e:
        param = get_ordering_parameter(order, PARAM_MEMBERSHIP_ID)
        order = set_ordering_parameter_error(
            order,
            PARAM_MEMBERSHIP_ID,
            ERR_ADOBE_MEMBERSHIP_ID.to_dict(title=param["name"], details=str(e)),
        )
        return True, order, None
    except AdobeHttpError as he:
        err_msg = (
            ERR_ADOBE_MEMBERSHIP_NOT_FOUND
            if he.status_code == 404
            else ERR_ADOBE_UNEXPECTED_ERROR
        )
        param = get_ordering_parameter(order, PARAM_MEMBERSHIP_ID)
        order = set_ordering_parameter_error(
            order,
            PARAM_MEMBERSHIP_ID,
            ERR_ADOBE_MEMBERSHIP_ID.to_dict(title=param["name"], details=err_msg),
        )
        return True, order, None

    return add_lines_to_order(mpt_client, order, transfer_preview, "quantity")


def validate_transfer(mpt_client, adobe_client, order):
    config = get_config()
    authorization_id = order["authorization"]["id"]
    authorization = config.get_authorization(authorization_id)
    membership_id = get_adobe_membership_id(order)
    product_id = order["agreement"]["product"]["id"]

    transfer = get_transfer_by_authorization_membership_or_customer(
        product_id,
        authorization.authorization_id,
        membership_id,
    )

    if not transfer:
        return validate_transfer_not_migrated(mpt_client, adobe_client, order)

    if transfer.status == STATUS_RUNNING:
        param = get_ordering_parameter(order, PARAM_MEMBERSHIP_ID)
        order = set_ordering_parameter_error(
            order,
            PARAM_MEMBERSHIP_ID,
            ERR_ADOBE_MEMBERSHIP_ID.to_dict(
                title=param["name"], details="Migration in progress, retry later"
            ),
        )
        return True, order, None

    if transfer.status == STATUS_SYNCHRONIZED:
        param = get_ordering_parameter(order, PARAM_MEMBERSHIP_ID)
        order = set_ordering_parameter_error(
            order,
            PARAM_MEMBERSHIP_ID,
            ERR_ADOBE_MEMBERSHIP_ID.to_dict(
                title=param["name"], details="Membership has already been migrated"
            ),
        )
        return True, order, None

    subscriptions = adobe_client.get_subscriptions(
        authorization_id,
        transfer.customer_id,
    )
    adobe_transfer = adobe_client.get_transfer(
        authorization_id,
        transfer.membership_id,
        transfer.transfer_id,
    )
    for subscription in subscriptions["items"]:
        correct_sku = get_transfer_item_sku_by_subscription(
            adobe_transfer, subscription["subscriptionId"]
        )
        subscription["offerId"] = correct_sku or subscription["offerId"]

    return add_lines_to_order(mpt_client, order, subscriptions, "currentQuantity")
