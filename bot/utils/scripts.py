def calculate_multiplier(spins, variables):
    for v in variables[::-1]:
        if spins >= v:
            return v
    return 1
