def parse_company_id(value: str) -> int:
    """
    Convert CLI args from strings -> hex.

    e.g.
        "1234"
        "0x1234"
    """

    # Obtain value + convert
    value = value.lower().replace("0x", "")

    # Parse in base 16
    company_id = int(value, 16)

    # Boundary checking
    if not 0 <= company_id <= 0xFFFF:
        raise ValueError(
            "Company ID must fit in 16 bits"
        )

    return company_id
