"""
calculations.py
---------------
The calculation engine for the Customer Experience Platform.

Owner: Member 1.
Members 3 (Dashboard) and 4 (Reports) should IMPORT from this file
instead of rewriting the same math:

    from calculations import calculate_csat, calculate_change, calculate_gap

The CSAT / CES / NPS formulas each use a fixed answer scale, described
in the docstring of every function. Agree on those scales with the team
before the survey questions are written.

There is no Streamlit and no database code here on purpose.
"""

import pandas as pd


def _clean(responses):
    """
    Accept either a plain Python list or a pandas Series, and return a
    Series with the blank answers removed.
    """
    return pd.Series(list(responses)).dropna()


# ----------------------------------------------------------------------
# 1) Survey-based indicators: CSAT, CES, NPS
# ----------------------------------------------------------------------

def calculate_csat(responses):
    """
    CSAT = Customer Satisfaction Score.

    Input : answers on a 1-5 scale.
    Rule  : answers of 4 or 5 count as satisfied.
    Output: percentage of satisfied customers, 0..100. Higher is better.
    """
    answers = _clean(responses)
    if len(answers) == 0:
        return None

    satisfied = answers.isin([4, 5]).sum()
    return round(satisfied / len(answers) * 100, 2)


def calculate_ces(responses):
    """
    CES = Customer Effort Score, as a NET score (not an average).

    Input : answers on a 1-5 scale (5 = very easy, 1 = very difficult).
    Rule  : CES = % who found it easy (4-5) minus % who found it hard (1-2).
    Output: a score from -100 to +100. HIGHER is better (easier service).
    """
    answers = _clean(responses)
    if len(answers) == 0:
        return None

    easy = answers.isin([4, 5]).sum() / len(answers) * 100
    hard = answers.isin([1, 2]).sum() / len(answers) * 100
    return round(easy - hard, 2)


def calculate_nps(responses):
    """
    NPS = Net Promoter Score.

    Input : answers on a 0-10 scale.
    Rule  : 9-10 = promoter, 7-8 = passive, 0-6 = detractor.
            NPS = %promoters - %detractors.
    Output: a score from -100 to +100. Higher is better.
    """
    answers = _clean(responses)
    if len(answers) == 0:
        return None

    promoters = answers.isin([9, 10]).sum() / len(answers) * 100
    detractors = (answers <= 6).sum() / len(answers) * 100
    return round(promoters - detractors, 2)


# ----------------------------------------------------------------------
# 2) Comparison indicators: change over time, gap vs. target
# ----------------------------------------------------------------------

def calculate_change(previous_value, current_value):
    """
    Compare the current period against the previous one.

    Returns a dictionary:
        change          -> current - previous (absolute difference)
        change_percent  -> the difference as a % of the previous value
                           (None if the previous value is 0, to avoid
                           dividing by zero)
        direction       -> "increase" / "decrease" / "no change"
    """
    previous_value = float(previous_value)
    current_value = float(current_value)

    change = round(current_value - previous_value, 2)

    if previous_value == 0:
        change_percent = None          # cannot divide by zero
    else:
        change_percent = round(change / abs(previous_value) * 100, 1)

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


def calculate_gap(current_value, target_value,
                  higher_is_better=True, close_threshold=5.0):
    """
    Compare the current value against the target value.

    higher_is_better : True for CSAT / CES / NPS (all three are scores
                       where higher = better), False for indicators like
                       response time where lower = better.
    close_threshold  : how far below the target (in %) still counts as
                       "Close" instead of "Below Target". Default 5%.

    Returns a dictionary:
        gap          -> current - target
        gap_percent  -> the gap as a % of the target (None if target is 0)
        status       -> "Met" / "Close" / "Below Target"
    """
    current_value = float(current_value)
    target_value = float(target_value)

    gap = round(current_value - target_value, 2)

    if target_value == 0:
        gap_percent = None
    else:
        gap_percent = round(gap / abs(target_value) * 100, 1)

    # "Performance" = how much better than target we are.
    # For lower-is-better indicators the sign is flipped.
    performance = gap if higher_is_better else -gap

    if performance >= 0:
        status = "Met"
    elif gap_percent is not None and abs(gap_percent) <= close_threshold:
        status = "Close"
    elif gap_percent is None and abs(gap) <= close_threshold:
        status = "Close"
    else:
        status = "Below Target"

    return {
        "gap": gap,
        "gap_percent": gap_percent,
        "status": status,
    }


def summarize_indicator(previous_value, current_value, target_value,
                        higher_is_better=True):
    """
    Convenience function: runs calculate_change + calculate_gap together
    and returns one flat dictionary. This is what the Dashboard and the
    Reports pages will normally call.
    """
    change = calculate_change(previous_value, current_value)
    gap = calculate_gap(current_value, target_value, higher_is_better)

    result = {}
    result.update(change)
    result.update(gap)
    return result


# ----------------------------------------------------------------------
# Quick self-test: run "python calculations.py" to check the math.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("CSAT:", calculate_csat([5, 4, 3, 5, 2, 4]))   # 66.67 %
    print("CES :", calculate_ces([5, 4, 3, 1, 2]))       # 40.0 - 40.0 = 0.0
    print("NPS :", calculate_nps([10, 9, 8, 7, 6, 3]))   # 33.33 - 33.33 = 0.0
    print("Empty:", calculate_csat([]))                  # None
    print("Change:", calculate_change(41, 55))
    print("Gap   :", calculate_gap(55, 60))