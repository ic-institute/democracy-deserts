from math import sqrt


def moe_of_sum(*moes):
    """Combine margin of error of two or more independent distributions
    using sum of squares"""
    return sqrt(sum(moe ** 2 for moe in moes))


def moe_of_subpop_ratio(subpop_est, subpop_moe, pop_est, pop_moe):
    """Approximate margin of error for the ratio of a subpopulation size
    to the population size, assuming these estimates were made from
    different sources (as happens in ACS data).

    We assume:
    - size of the population is at least 1
    - size of the subpopulation between 0 and the size of the population
    """
    assert subpop_est >= 0
    assert subpop_moe >= 0
    assert pop_est >= 0
    assert pop_moe >= 0

    def _ratio(subpop, pop):
        pop = max(pop, 1)
        subpop = max(min(subpop, pop), 0)

        return subpop / pop

    ratio_est = _ratio(subpop_est, pop_est)
    ratio_min = _ratio(subpop_est - subpop_moe, pop_est + pop_moe)
    ratio_max = _ratio(subpop_est + subpop_moe, pop_est - pop_moe)
    
    return max(ratio_est - ratio_min, ratio_max - ratio_est)

