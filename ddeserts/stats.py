from math import sqrt


def moe_of_sum(*moes):
    """Combine margin of error of two or more independent distributions
    using sum of squares"""
    return sqrt(sum(moe ** 2 for moe in moes))


def moe_of_ratio(a_est, a_moe, b_est, b_moe):
    """Approximate margin of error for a/b."""
    # this only makes sense for positive divisors
    if not (b_est > b_moe >= 0):
        raise ValueError

    # find highest and lowest values within margin of error
    min_a = a_est - a_moe
    max_a = a_est + a_moe
    min_b = b_est - b_moe
    max_b = b_est + b_moe
    
    # compare highest and lowest ratios to our estimate
    ratio = a_est / b_est
    min_ratio = min_a / max_b
    max_ratio = max_a / min_b
    
    return max(ratio - min_ratio, max_ratio - ratio)