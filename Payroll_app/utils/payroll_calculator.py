def calculate_tax(salary):
    # The progressive tax rate calculation is realized based on the HMRC tax rate table
    brackets = [
        (12570, 0),
        (50270, 0.2),
        (150000, 0.4),
        (float('inf'), 0.45)
    ]
    tax = 0
    remaining = salary
    for i, (threshold, rate) in enumerate(brackets):
        if i == 0:
            remaining -= threshold
            continue
        prev_threshold = brackets[i-1][0]
        bracket_amount = min(remaining, threshold - prev_threshold)
        tax += bracket_amount * rate
        remaining -= bracket_amount
        if remaining <= 0:
            break
    return tax

def calculate_ni(salary):
    # The calculation logic of national insurance
    weekly_earnings = salary / 52
    if weekly_earnings > 242:
        return (weekly_earnings - 242) * 0.02 * 52
    return 0