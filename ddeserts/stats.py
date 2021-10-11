"""Statistics, mostly for calculating margin of error.

Derived from the ACS General Handbook (see
data/census/acs_general_handbook_2018_ch08.pdf)
"""
from math import sqrt


def moe_of_sum(*moes):
    """Combine margin of error of two or more independent distributions
    using sum of squares. Works for sums or differences.
    """
    return sqrt(sum(moe ** 2 for moe in moes))


def moe_of_prop(subpop_est, pop_est, subpop_moe, pop_moe):
    """Approximate margin of error for the ratio of a subpopulation size
    to the population size, assuming these estimates were made from
    different sources (as happens in ACS data).

    We assume:
    - pop is at least 1
    - subpop / pop is between 0 and 1
    """
    pop_est = max(pop_est, 1)
    prop = est_of_prop(subpop_est, pop_est)

    # this formula assumes pop. MoE is less than subpop. MoE
    pop_moe = min(pop_moe, subpop_moe)

    return 1 / pop_est * sqrt(
        subpop_moe ** 2 - (prop * pop_moe) ** 2
    )


def est_of_prop(subpop_est, pop_est):
    """Basically subpop_est divided by pop_est, but with some reasonable
    assumptions that constrain the final answer:

    - actual value of pop is at least 1
    - actual value of subpop is at least 0
    - actual value of pop/subpop (what we return) is between 0 and 1
    """
    pop_est = max(pop_est, 1)
    subpop_est = max(min(subpop_est, pop_est), 0)

    return min(subpop_est / pop_est, 1)