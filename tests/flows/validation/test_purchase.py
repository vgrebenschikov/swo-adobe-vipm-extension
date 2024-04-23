import pytest

from adobe_vipm.flows.constants import (
    ERR_ADDRESS,
    ERR_ADDRESS_LINE_1_LENGTH,
    ERR_ADDRESS_LINE_2_LENGTH,
    ERR_CITY_LENGTH,
    ERR_COMPANY_NAME_CHARS,
    ERR_COMPANY_NAME_LENGTH,
    ERR_CONTACT,
    ERR_COUNTRY_CODE,
    ERR_EMAIL_FORMAT,
    ERR_FIRST_NAME_FORMAT,
    ERR_LAST_NAME_FORMAT,
    ERR_PHONE_NUMBER_LENGTH,
    ERR_POSTAL_CODE_FORMAT,
    ERR_POSTAL_CODE_LENGTH,
    ERR_PREFERRED_LANGUAGE,
    ERR_STATE_OR_PROVINCE,
    PARAM_ADDRESS,
    PARAM_COMPANY_NAME,
    PARAM_CONTACT,
    PARAM_PREFERRED_LANGUAGE,
)
from adobe_vipm.flows.utils import get_customer_data, get_ordering_parameter
from adobe_vipm.flows.validation.purchase import (
    validate_address,
    validate_company_name,
    validate_contact,
    validate_customer_data,
    validate_preferred_language,
)

pytestmark = pytest.mark.usefixtures("mock_adobe_config")


@pytest.mark.parametrize(
    "company_name",
    [
        "Hill, Patterson and Simpson, Tuc-Dixon & Garza, Phelps Inc",
        "Bart",
        "Schneider 1997",
        "ELA L・L GEMINADA SL",
        "(Paren_tesi S.p.A.)",
        'Herma\\nos "Preciosos" SAU',
        "Precios/os 'Hermanos' SAU",
    ],
)
def test_validate_company_name(order_factory, order_parameters_factory, company_name):
    """
    Tests the validation of the Company name when it is valid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(company_name=company_name)
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_company_name(order, customer_data)

    assert has_error is False

    param = get_ordering_parameter(order, PARAM_COMPANY_NAME)
    assert "error" not in param


@pytest.mark.parametrize(
    "company_name",
    [
        "Hill, Patterson and Simpson, Tuc-Dixon & Garza, Phelps & Maria Addolorata Inc",
        "Bar",
    ],
)
def test_validate_company_name_invalid_length(
    order_factory, order_parameters_factory, company_name
):
    """
    Tests the validation of the Company name when it is invalid due to length.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(company_name=company_name)
    )
    customer_data = get_customer_data(order)
    has_error, order = validate_company_name(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(order, PARAM_COMPANY_NAME)
    assert param["error"] == ERR_COMPANY_NAME_LENGTH.to_dict(title=param["name"])
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


@pytest.mark.parametrize(
    "company_name",
    [
        "Felici ☺ SRL",
        "Quasimodo $ 23",
        "Euro € Company",
        "Star * of the Sky",
    ],
)
def test_validate_company_name_invalid_chars(
    order_factory, order_parameters_factory, company_name
):
    """
    Tests the validation of the Company name when it is invalid due to chars.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(company_name=company_name)
    )
    customer_data = get_customer_data(order)
    has_error, order = validate_company_name(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(order, PARAM_COMPANY_NAME)
    assert param["error"] == ERR_COMPANY_NAME_CHARS.to_dict(title=param["name"])
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_preferred_language(order_factory, order_parameters_factory):
    """
    Tests the validation of the preferred language when it is valid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(preferred_language="en-US")
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_preferred_language(order, customer_data)

    assert has_error is False

    param = get_ordering_parameter(
        order,
        PARAM_PREFERRED_LANGUAGE,
    )
    assert "error" not in param


def test_validate_preferred_language_invalid(
    order_factory,
    order_parameters_factory,
):
    """
    Tests the validation of the preferred language when it is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(preferred_language="invalid")
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_preferred_language(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_PREFERRED_LANGUAGE,
    )
    assert param["error"] == ERR_PREFERRED_LANGUAGE.to_dict(
        title=param["name"],
        languages="en-US",
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_address(order_factory):
    """
    Tests the validation of a valid address.
    """
    order = order_factory()
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is False

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )
    assert "error" not in param


def test_validate_address_invalid_country(order_factory, order_parameters_factory):
    """
    Tests the validation of an address when the country is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            address={
                "country": "ES",
                "state": "B",
                "city": "Barcelona",
                "addressLine1": "Plaza Catalunya 1",
                "addressLine2": "1o 1a",
                "postalCode": "08001",
            },
        )
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )
    assert param["error"] == ERR_ADDRESS.to_dict(
        title=param["name"],
        errors=ERR_COUNTRY_CODE,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_address_invalid_state(order_factory, order_parameters_factory):
    """
    Tests the validation of an address when the state or province is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            address={
                "country": "US",
                "state": "ZZ",
                "city": "San Jose",
                "addressLine1": "3601 Lyon St",
                "addressLine2": "",
                "postalCode": "94123",
            },
        )
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )
    assert param["error"] == ERR_ADDRESS.to_dict(
        title=param["name"],
        errors=ERR_STATE_OR_PROVINCE,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_address_invalid_postal_code(order_factory, order_parameters_factory):
    """
    Tests the validation of an address when the postal code doesn't match
    the expected pattern.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            address={
                "country": "US",
                "state": "CA",
                "city": "San Jose",
                "addressLine1": "3601 Lyon St",
                "addressLine2": "",
                "postalCode": "9412312",
            },
        )
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )
    assert param["error"] == ERR_ADDRESS.to_dict(
        title=param["name"],
        errors=ERR_POSTAL_CODE_FORMAT,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_address_invalid_postal_code_length(
    order_factory, order_parameters_factory
):
    """
    Tests the validation of an address when the postal code doesn't match
    the expected length.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            address={
                "country": "VU",
                "state": "TOB",
                "city": "Lalala",
                "addressLine1": "Blah blah",
                "addressLine2": "",
                "postalCode": "9" * 41,
            },
        )
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )
    assert param["error"] == ERR_ADDRESS.to_dict(
        title=param["name"],
        errors=ERR_POSTAL_CODE_LENGTH,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_address_invalid_others(order_factory, order_parameters_factory):
    """
    Tests the validation of an address when address lines or city exceed the the
    maximum allowed length.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            address={
                "country": "VU",
                "state": "TOB",
                "city": "C" * 41,
                "addressLine1": "1" * 61,
                "addressLine2": "2" * 61,
                "postalCode": "",
            },
        )
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_address(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_ADDRESS,
    )

    assert param["error"] == ERR_ADDRESS.to_dict(
        title=param["name"],
        errors="; ".join(
            (
                ERR_ADDRESS_LINE_1_LENGTH,
                ERR_ADDRESS_LINE_2_LENGTH,
                ERR_CITY_LENGTH,
            ),
        ),
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_contact(order_factory):
    """
    Tests the validation of a valid contact.
    """
    order = order_factory()
    customer_data = get_customer_data(order)

    has_error, order = validate_contact(order, customer_data)

    assert has_error is False

    param = get_ordering_parameter(
        order,
        PARAM_CONTACT,
    )
    assert "error" not in param


def test_validate_contact_invalid_first_name(order_factory, order_parameters_factory):
    """
    Tests the validation of a contact when the first name is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            contact={
                "firstName": "First N@m€",
                "lastName": "Last Name",
                "email": "test@example.com",
            },
        ),
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_contact(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_CONTACT,
    )
    assert param["error"] == ERR_CONTACT.to_dict(
        title=param["name"],
        errors=ERR_FIRST_NAME_FORMAT,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_contact_invalid_last_name(order_factory, order_parameters_factory):
    """
    Tests the validation of a contact when the last name is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            contact={
                "firstName": "First Name",
                "lastName": "L@ast N@m€",
                "email": "test@example.com",
            },
        ),
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_contact(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_CONTACT,
    )
    assert param["error"] == ERR_CONTACT.to_dict(
        title=param["name"],
        errors=ERR_LAST_NAME_FORMAT,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_contact_invalid_email(order_factory, order_parameters_factory):
    """
    Tests the validation of a contact when the email is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            contact={
                "firstName": "First Name",
                "lastName": "Last Name",
                "email": "test_example.com",
            },
        ),
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_contact(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_CONTACT,
    )
    assert param["error"] == ERR_CONTACT.to_dict(
        title=param["name"],
        errors=ERR_EMAIL_FORMAT,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_contact_invalid_phone(order_factory, order_parameters_factory):
    """
    Tests the validation of a contact when the phone is invalid.
    """
    order = order_factory(
        order_parameters=order_parameters_factory(
            contact={
                "firstName": "First Name",
                "lastName": "Last Name",
                "email": "test@example.com",
                "phone": {
                    "prefix": "+1",
                    "number": "4082954078" * 5,
                },
            },
        ),
    )
    customer_data = get_customer_data(order)

    has_error, order = validate_contact(order, customer_data)

    assert has_error is True

    param = get_ordering_parameter(
        order,
        PARAM_CONTACT,
    )
    assert param["error"] == ERR_CONTACT.to_dict(
        title=param["name"],
        errors=ERR_PHONE_NUMBER_LENGTH,
    )
    assert param["constraints"]["hidden"] is False
    assert param["constraints"]["optional"] is False


def test_validate_customer_data(mocker):
    """
    Test that `validate_customer_data` calls the single validation
    function in the right order and that the has_errors will be False in case of
    no errors.
    """
    order_mocks = [
        mocker.MagicMock(),
    ]
    customer_data = mocker.MagicMock()
    fn_mocks = []
    for fnname in (
        "validate_company_name",
        "validate_preferred_language",
        "validate_address",
        "validate_contact",
    ):
        order_mock = mocker.MagicMock()
        order_mocks.append(order_mock)
        fn_mocks.append(
            mocker.patch(
                f"adobe_vipm.flows.validation.purchase.{fnname}",
                return_value=(False, order_mock),
            ),
        )

    has_errors, order = validate_customer_data(order_mocks[0], customer_data)

    assert has_errors is False
    assert order == order_mocks[-1]

    for mock_id, fn_mock in enumerate(fn_mocks):
        fn_mock.assert_called_once_with(order_mocks[mock_id], customer_data)


@pytest.mark.parametrize(
    "no_validating_fn",
    [
        "validate_company_name",
        "validate_preferred_language",
        "validate_address",
        "validate_contact",
    ],
)
def test_validate_customer_data_invalid(mocker, no_validating_fn):
    """
    Test that if one of the validation returns has_errors=True the
    `validate_customer_data` function returns has_errors=True
    """
    for fnname in (
        "validate_company_name",
        "validate_preferred_language",
        "validate_address",
        "validate_contact",
    ):
        mocker.patch(
            f"adobe_vipm.flows.validation.purchase.{fnname}",
            return_value=(fnname == no_validating_fn, mocker.MagicMock()),
        )

    has_errors, _ = validate_customer_data(mocker.MagicMock(), mocker.MagicMock())

    assert has_errors is True