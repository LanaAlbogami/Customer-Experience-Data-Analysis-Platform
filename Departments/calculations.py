import pandas as pd


# ==================================================
# Data cleaning
# ==================================================

def _clean(responses, minimum, maximum):
    """
    Clean survey responses and keep only valid answers
    within the allowed scale.

    Examples:
    - CSAT / CES: valid answers are 1 to 5
    - NPS: valid answers are 0 to 10

    NaN, blanks, 99 (Not Applicable), and any value
    outside the allowed range are excluded completely.
    """

    answers = pd.to_numeric(
        pd.Series(list(responses)),
        errors="coerce",
    ).dropna()

    return answers[
        answers.between(
            minimum,
            maximum,
        )
    ]


# ==================================================
# Survey-based indicators
# ==================================================

def calculate_csat(responses):
    """
    CSAT = Customer Satisfaction Score.

    Input:
        Answers on a 1-5 scale.

    Valid answers:
        1, 2, 3, 4, 5

    Classification:
        4-5 = Satisfied
        3   = Neutral
        1-2 = Dissatisfied

    Formula:
        CSAT =
        Number of satisfied responses (4 or 5)
        --------------------------------------
        Number of valid responses (1 to 5)
        * 100

    Output:
        Percentage from 0 to 100.

    Important:
        99, NaN, blanks, and values outside 1-5
        are excluded from both numerator and denominator.
    """

    answers = _clean(
        responses,
        minimum=1,
        maximum=5,
    )

    if len(answers) == 0:
        return None

    satisfied = answers.isin(
        [4, 5]
    ).sum()

    return round(
        satisfied
        / len(answers)
        * 100,
        2,
    )


def calculate_ces(responses):
    """
    CES = Customer Effort Score as a NET score.

    Input:
        Answers on a 1-5 scale.

    Valid answers:
        1, 2, 3, 4, 5

    Classification:
        4-5 = Easy
        3   = Neutral
        1-2 = Difficult

    Formula:
        CES =
        % Easy
        -
        % Difficult

    Where:
        % Easy =
        Number of responses 4 or 5
        --------------------------
        Number of valid responses
        * 100

        % Difficult =
        Number of responses 1 or 2
        --------------------------
        Number of valid responses
        * 100

    Output:
        Score from -100 to +100.

    Important:
        99, NaN, blanks, and values outside 1-5
        are excluded from the denominator.
    """

    answers = _clean(
        responses,
        minimum=1,
        maximum=5,
    )

    if len(answers) == 0:
        return None

    easy = (
        answers.isin(
            [4, 5]
        ).sum()
        / len(answers)
        * 100
    )

    hard = (
        answers.isin(
            [1, 2]
        ).sum()
        / len(answers)
        * 100
    )

    return round(
        easy - hard,
        2,
    )


def calculate_nps(responses):
    """
    NPS = Net Promoter Score.

    Input:
        Answers on a 0-10 scale.

    Valid answers:
        0 through 10

    Classification:
        9-10 = Promoters
        7-8  = Passives
        0-6  = Detractors

    Formula:
        NPS =
        % Promoters
        -
        % Detractors

    Where:
        % Promoters =
        Number of responses 9 or 10
        ---------------------------
        Number of valid responses
        * 100

        % Detractors =
        Number of responses 0 to 6
        --------------------------
        Number of valid responses
        * 100

    Output:
        Score from -100 to +100.

    Important:
        Passives (7-8) are included in the denominator
        but not in either side of the subtraction.

        99, NaN, blanks, and values outside 0-10
        are excluded completely.
    """

    answers = _clean(
        responses,
        minimum=0,
        maximum=10,
    )

    if len(answers) == 0:
        return None

    promoters = (
        answers.isin(
            [9, 10]
        ).sum()
        / len(answers)
        * 100
    )

    detractors = (
        answers.between(
            0,
            6,
        ).sum()
        / len(answers)
        * 100
    )

    return round(
        promoters - detractors,
        2,
    )


# ==================================================
# Comparison indicators
# ==================================================

def calculate_change(
    previous_value,
    current_value,
):
    """
    Compare the current period against the previous period.

    Returns:
        change
            Current value - previous value

        change_percent
            Change as a percentage of the previous value.
            Returns None if previous value is 0.

        direction
            increase / decrease / no change
    """

    previous_value = float(
        previous_value
    )

    current_value = float(
        current_value
    )

    change = round(
        current_value
        - previous_value,
        2,
    )

    if previous_value == 0:
        change_percent = None

    else:
        change_percent = round(
            change
            / abs(previous_value)
            * 100,
            1,
        )

    if change > 0:
        direction = "increase"

    elif change < 0:
        direction = "decrease"

    else:
        direction = "no change"

    return {
        "change": change,
        "change_percent": change_percent,
        "direction": direction,
    }


def calculate_gap(
    current_value,
    target_value,
    higher_is_better=True,
    close_threshold=5.0,
):
    """
    Compare the current value against the target value.

    higher_is_better:
        True for CSAT, CES, and NPS.

    close_threshold:
        Percentage difference from the target that still
        counts as "Close".

    Returns:
        gap
            Current value - target value

        gap_percent
            Gap as percentage of target.
            Returns None when target = 0.

        status
            Met / Close / Below Target
    """

    current_value = float(
        current_value
    )

    target_value = float(
        target_value
    )

    gap = round(
        current_value
        - target_value,
        2,
    )

    if target_value == 0:
        gap_percent = None

    else:
        gap_percent = round(
            gap
            / abs(target_value)
            * 100,
            1,
        )

    # Performance means how much better
    # the current result is than the target.
    performance = (
        gap
        if higher_is_better
        else -gap
    )

    if performance >= 0:
        status = "Met"

    elif (
        gap_percent is not None
        and abs(gap_percent)
        <= close_threshold
    ):
        status = "Close"

    elif (
        gap_percent is None
        and abs(gap)
        <= close_threshold
    ):
        status = "Close"

    else:
        status = "Below Target"

    return {
        "gap": gap,
        "gap_percent": gap_percent,
        "status": status,
    }


def summarize_indicator(
    previous_value,
    current_value,
    target_value,
    higher_is_better=True,
):
    """
    Run calculate_change and calculate_gap together
    and return one combined dictionary.
    """

    change = calculate_change(
        previous_value,
        current_value,
    )

    gap = calculate_gap(
        current_value,
        target_value,
        higher_is_better,
    )

    result = {}

    result.update(
        change
    )

    result.update(
        gap
    )

    return result


# ==================================================
# Quick self-test
# ==================================================

if __name__ == "__main__":

    print(
        "CSAT:",
        calculate_csat(
            [5, 4, 3, 5, 2, 4]
        ),
    )
    # 4 satisfied out of 6
    # = 66.67%

    print(
        "CSAT with 99:",
        calculate_csat(
            [5, 4, 3, 99, 99]
        ),
    )
    # Valid answers = 5, 4, 3
    # Satisfied = 5, 4
    # = 2 / 3 = 66.67%

    print(
        "CES:",
        calculate_ces(
            [5, 4, 3, 1, 2]
        ),
    )
    # Easy = 40%
    # Difficult = 40%
    # CES = 0

    print(
        "CES with 99:",
        calculate_ces(
            [5, 4, 3, 1, 99]
        ),
    )
    # Valid answers = 4
    # Easy = 50%
    # Difficult = 25%
    # CES = 25

    print(
        "NPS:",
        calculate_nps(
            [10, 9, 8, 7, 6, 3]
        ),
    )
    # Promoters = 33.33%
    # Detractors = 33.33%
    # NPS = 0

    print(
        "NPS with 99:",
        calculate_nps(
            [10, 9, 8, 7, 6, 99]
        ),
    )
    # 99 excluded

    print(
        "Empty:",
        calculate_csat([]),
    )
    # None

    print(
        "Change:",
        calculate_change(
            41,
            55,
        ),
    )

    print(
        "Gap:",
        calculate_gap(
            55,
            60,
        ),
    )