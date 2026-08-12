from decimal import Decimal

from database.crud.indicator_results import (
    create_indicator_result,
)

# This script is for testing the creation of an indicator result in the database.
try:
    result = create_indicator_result(
        record_id=1,
        indicator_id=1,
        prev_value=Decimal("75"),
        current_value=Decimal("82"),
        target_value=Decimal("90"),
    )

    print("Indicator result created successfully.")
    print("Result ID:", result.result_id)
    print("Record ID:", result.record_id)
    print("Indicator ID:", result.indicator_id)
    print("Previous value:", result.prev_value)
    print("Current value:", result.current_value)
    print("Target value:", result.target_value)

except ValueError as error:
    print(error)