from math import sqrt


def moe_of_sum(*moes):
    """Combine margin of error of two or more independent distributions
    using sum of squares. Works for sums or differences.
    """
    return sqrt(sum(moe ** 2 for moe in moes))


def moe_of_subpop_ratio(subpop_est, subpop_moe, pop_est, pop_moe):
    """Approximate margin of error for the ratio of a subpopulation size
    to the population size, assuming these estimates were made from
    different sources (as happens in ACS data).

    We assume:
    - size of the population is at least 1
    - size of the subpopulation between 0 and the size of the population
    """
    assert subpop_moe >= 0
    assert pop_moe >= 0

    ratio_est = subpop_ratio(subpop_est, pop_est)
    ratio_min = subpop_ratio(subpop_est - subpop_moe, pop_est + pop_moe)
    ratio_max = subpop_ratio(subpop_est + subpop_moe, pop_est - pop_moe)
    
    return max(ratio_est - ratio_min, ratio_max - ratio_est)


def subpop_ratio(subpop_est, pop_est):
    """Basically subpop_est divided by pop_est, but with some reasonable
    assumptions that constrain the final answer:

    - actual value of pop is at least 1
    - actual value of subpop is at least 0
    - actual value of their ratio (what we return) is between 0 and 1
    """
    pop_est = max(pop_est, 1)
    subpop_est = max(min(subpop_est, pop_est), 0)

    return min(subpop_est / pop_est, 1)