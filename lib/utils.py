import re

def laterOrEqualVersionStringCompare(numberString1, numberString2):
    numbers1 = [int(n) for n in re.findall(r'\d+', numberString1)]
    numbers2 = [int(n) for n in re.findall(r'\d+', numberString2)]
    if len(numbers1) > len(numbers2):
        numbers2 = numbers2 + [0]*(len(numbers1) - len(numbers2))
    elif len(numbers1) < len(numbers2):
        numbers1 = numbers1 + [0]*(len(numbers2) - len(numbers1))
    compare = False
    for number1, number2 in zip(numbers1, numbers2):
        if numbers1 > numbers2:
            return True
        compare = True if numbers1 == numbers2 else False
    return compare
