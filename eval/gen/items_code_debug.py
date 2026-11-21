"""Code-debugging items: each is (name, intended behaviour, FIXED code, (find, replace) planting ONE bug,
hidden tests, difficulty, bug type). The buggy version is produced from the fixed one by the single
textual patch, so the planted bug is exactly that patch. build_code_tasks.py checks that tests pass on the
fixed code and FAIL on the buggy code (mutation check).
"""

E, H = "easy", "hard"

ITEMS = [
    # ------------------------------------------------------------------ easy
    ("count_vowels", "count the vowels (a, e, i, o, u, case-insensitive) in a string",
     "def count_vowels(s):\n    return sum(1 for c in s.lower() if c in \"aeiou\")\n",
     ('"aeiou"', '"aeio"'),
     """assert count_vowels("hello") == 2
assert count_vowels("SKY") == 0
assert count_vowels("education") == 5
assert count_vowels("") == 0
assert count_vowels("Umbrella") == 3
assert count_vowels("rhythm") == 0""", E, "missing element in literal"),
    ("is_even", "return True if an integer is even, else False (including negative numbers and zero)",
     "def is_even(n):\n    return n % 2 == 0\n",
     ("n % 2 == 0", "n % 2 == 1"),
     """assert is_even(4) is True
assert is_even(7) is False
assert is_even(0) is True
assert is_even(-2) is True
assert is_even(-3) is False""", E, "wrong comparison"),
    ("max_of_three", "return the largest of three numbers",
     "def max_of_three(a, b, c):\n    if a >= b and a >= c:\n        return a\n    if b >= c:\n        return b\n    return c\n",
     ("if b >= c:", "if b >= a:"),
     """assert max_of_three(1, 2, 3) == 3
assert max_of_three(9, 2, 3) == 9
assert max_of_three(1, 5, 9) == 9
assert max_of_three(1, 9, 5) == 9
assert max_of_three(-1, -5, -3) == -1
assert max_of_three(4, 4, 4) == 4""", E, "wrong variable in comparison"),
    ("factorial", "return n! for an integer n >= 0 (0! is 1)",
     "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n",
     ("        return 1\n", "        return 0\n"),
     """assert factorial(0) == 1
assert factorial(1) == 1
assert factorial(5) == 120
assert factorial(7) == 5040""", E, "wrong base case"),
    ("sum_to_n", "return the sum of the integers from 1 to n inclusive (0 when n is 0)",
     "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n",
     ("range(1, n + 1)", "range(1, n)"),
     """assert sum_to_n(1) == 1
assert sum_to_n(4) == 10
assert sum_to_n(100) == 5050
assert sum_to_n(0) == 0""", E, "off-by-one range"),
    ("reverse_string", "return the string reversed, building the result with a loop",
     "def reverse_string(s):\n    result = \"\"\n    for ch in s:\n        result = ch + result\n    return result\n",
     ("result = ch + result", "result = result + ch"),
     """assert reverse_string("abc") == "cba"
assert reverse_string("") == ""
assert reverse_string("a") == "a"
assert reverse_string("hello world") == "dlrow olleh\"""", E, "wrong concatenation order"),
    ("c_to_f", "convert degrees Celsius to degrees Fahrenheit",
     "def c_to_f(c):\n    return c * 9 / 5 + 32\n",
     ("c * 9 / 5", "c * 5 / 9"),
     """assert c_to_f(0) == 32
assert c_to_f(100) == 212
assert c_to_f(-40) == -40
assert abs(c_to_f(37) - 98.6) < 1e-9""", E, "inverted formula"),
    ("first_n_squares", "return a list of the squares of 1..n (empty list when n is 0)",
     "def first_n_squares(n):\n    return [i * i for i in range(1, n + 1)]\n",
     ("range(1, n + 1)", "range(n)"),
     """assert first_n_squares(3) == [1, 4, 9]
assert first_n_squares(0) == []
assert first_n_squares(1) == [1]
assert first_n_squares(5) == [1, 4, 9, 16, 25]""", E, "off-by-one range"),
    ("is_palindrome", "return True if a string reads the same forwards and backwards, ignoring case and non-alphanumeric characters",
     "def is_palindrome(s):\n    cleaned = \"\".join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]\n",
     ("c.lower() for c in s", "c for c in s"),
     """assert is_palindrome("Racecar") is True
assert is_palindrome("A man, a plan, a canal: Panama") is True
assert is_palindrome("hello") is False
assert is_palindrome("") is True
assert is_palindrome("No lemon, no melon") is True""", E, "missing normalisation"),
    ("count_words", "count the words in a text, where words are separated by any amount of whitespace",
     "def count_words(text):\n    return len(text.split())\n",
     ("text.split()", "text.split(\" \")"),
     """assert count_words("one two three") == 3
assert count_words("  spaced   out  words ") == 3
assert count_words("") == 0
assert count_words("tabs\\tand\\nnewlines") == 3
assert count_words("single") == 1""", E, "wrong split"),
    ("clamp", "restrict x to the range [lo, hi]",
     "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n",
     ("max(lo, min(x, hi))", "min(lo, max(x, hi))"),
     """assert clamp(5, 0, 10) == 5
assert clamp(-3, 0, 10) == 0
assert clamp(15, 0, 10) == 10
assert clamp(0, 0, 10) == 0
assert clamp(10, 0, 10) == 10""", E, "swapped min/max"),
    ("last_element", "return the last element of a list, or None if the list is empty",
     "def last_element(xs):\n    return xs[-1] if xs else None\n",
     ("xs[-1]", "xs[len(xs)]"),
     """assert last_element([1, 2, 3]) == 3
assert last_element([]) is None
assert last_element(["a"]) == "a\"""", E, "index out of range"),
    ("percentage", "return part as a percentage of whole, rounded to 1 decimal place",
     "def percentage(part, whole):\n    return round(part / whole * 100, 1)\n",
     ("part / whole", "whole / part"),
     """assert percentage(1, 4) == 25.0
assert percentage(1, 3) == 33.3
assert percentage(50, 200) == 25.0
assert percentage(0, 10) == 0.0
assert percentage(3, 2) == 150.0""", E, "swapped operands"),
    ("remove_duplicates", "remove duplicates from a list while keeping the first occurrence of each element in its original order",
     "def remove_duplicates(xs):\n    seen = set()\n    out = []\n    for x in xs:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out\n",
     ("    seen = set()\n    out = []\n    for x in xs:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out\n",
      "    return list(set(xs))\n"),
     """assert remove_duplicates([3, 1, 3, 2, 1]) == [3, 1, 2]
assert remove_duplicates([]) == []
assert remove_duplicates(["b", "a", "b"]) == ["b", "a"]
assert remove_duplicates([5, 4, 3, 2, 1, 1]) == [5, 4, 3, 2, 1]""", E, "order not preserved"),
    ("count_occurrences", "count how many times target appears in a list",
     "def count_occurrences(xs, target):\n    count = 0\n    for x in xs:\n        if x == target:\n            count += 1\n    return count\n",
     ("x == target", "x != target"),
     """assert count_occurrences([1, 2, 1, 3, 1], 1) == 3
assert count_occurrences([], 5) == 0
assert count_occurrences(["a", "b"], "c") == 0
assert count_occurrences([2, 2], 2) == 2""", E, "inverted condition"),
    ("min_in_list", "return the smallest element of a non-empty list of numbers",
     "def min_in_list(xs):\n    m = xs[0]\n    for x in xs:\n        if x < m:\n            m = x\n    return m\n",
     ("m = xs[0]", "m = 0"),
     """assert min_in_list([3, 1, 2]) == 1
assert min_in_list([5, 9, 7]) == 5
assert min_in_list([-4, -9]) == -9
assert min_in_list([8]) == 8""", E, "bad initial value"),
    ("capitalize_words", "capitalise the first letter of each word and lowercase the rest, words separated by single spaces",
     "def capitalize_words(s):\n    return \" \".join(w.capitalize() for w in s.split())\n",
     ("w.capitalize()", "w.upper()"),
     """assert capitalize_words("hello world") == "Hello World"
assert capitalize_words("PYTHON is fun") == "Python Is Fun"
assert capitalize_words("") == ""
assert capitalize_words("a") == "A\"""", E, "wrong string method"),
    ("fizzbuzz", "return \"FizzBuzz\" if n is divisible by both 3 and 5, \"Fizz\" if by 3, \"Buzz\" if by 5, otherwise str(n)",
     "def fizzbuzz(n):\n    if n % 15 == 0:\n        return \"FizzBuzz\"\n    if n % 3 == 0:\n        return \"Fizz\"\n    if n % 5 == 0:\n        return \"Buzz\"\n    return str(n)\n",
     ("    if n % 15 == 0:\n        return \"FizzBuzz\"\n    if n % 3 == 0:\n        return \"Fizz\"\n",
      "    if n % 3 == 0:\n        return \"Fizz\"\n    if n % 15 == 0:\n        return \"FizzBuzz\"\n"),
     """assert fizzbuzz(15) == "FizzBuzz"
assert fizzbuzz(30) == "FizzBuzz"
assert fizzbuzz(9) == "Fizz"
assert fizzbuzz(10) == "Buzz"
assert fizzbuzz(7) == "7\"""", E, "check order"),
    ("is_leap_year", "return True if a year is a leap year in the Gregorian calendar",
     "def is_leap_year(y):\n    return (y % 4 == 0 and y % 100 != 0) or y % 400 == 0\n",
     ("y % 400 == 0", "y % 100 == 0"),
     """assert is_leap_year(2024) is True
assert is_leap_year(2023) is False
assert is_leap_year(1900) is False
assert is_leap_year(2000) is True
assert is_leap_year(2100) is False""", E, "wrong divisor"),
    ("power", "compute base ** exp by repeated multiplication, for integer exp >= 0",
     "def power(base, exp):\n    result = 1\n    for _ in range(exp):\n        result *= base\n    return result\n",
     ("result = 1", "result = 0"),
     """assert power(2, 10) == 1024
assert power(5, 0) == 1
assert power(3, 3) == 27
assert power(-2, 3) == -8
assert power(1, 50) == 1""", E, "bad initial value"),
    ("digit_sum", "return the sum of the decimal digits of a non-negative integer",
     "def digit_sum(n):\n    total = 0\n    while n > 0:\n        total += n % 10\n        n //= 10\n    return total\n",
     ("n //= 10", "n //= 100"),
     """assert digit_sum(0) == 0
assert digit_sum(5) == 5
assert digit_sum(123) == 6
assert digit_sum(9999) == 36
assert digit_sum(1001) == 2""", E, "wrong step size"),
    ("get_initials", "return the uppercase initials of a full name, e.g. \"john ronald smith\" -> \"JRS\"",
     "def get_initials(name):\n    return \"\".join(w[0].upper() for w in name.split())\n",
     ("w[0]", "w[-1]"),
     """assert get_initials("john smith") == "JS"
assert get_initials("a b c") == "ABC"
assert get_initials("madonna") == "M"
assert get_initials("grace brewster murray hopper") == "GBMH\"""", E, "wrong index"),
    ("square_all", "return a NEW list with each element squared, without modifying the input list",
     "def square_all(xs):\n    return [x * x for x in xs]\n",
     ("    return [x * x for x in xs]\n", "    for i in range(len(xs)):\n        xs[i] = xs[i] * xs[i]\n    return xs\n"),
     """data = [1, 2, 3]
assert square_all(data) == [1, 4, 9]
assert data == [1, 2, 3]
assert square_all([]) == []
assert square_all([-2]) == [4]""", E, "mutates input"),
    ("to_binary", "return the binary representation of a non-negative integer as a string without any prefix",
     "def to_binary(n):\n    return bin(n)[2:]\n",
     ("bin(n)[2:]", "bin(n)"),
     """assert to_binary(5) == "101"
assert to_binary(0) == "0"
assert to_binary(8) == "1000"
assert to_binary(255) == "11111111\"""", E, "unstripped prefix"),
    ("join_with_commas", "join a list of strings with a comma and a space between items, with nothing after the last item",
     "def join_with_commas(items):\n    return \", \".join(items)\n",
     ("    return \", \".join(items)\n", "    out = \"\"\n    for it in items:\n        out += it + \", \"\n    return out\n"),
     """assert join_with_commas(["a", "b", "c"]) == "a, b, c"
assert join_with_commas(["x"]) == "x"
assert join_with_commas([]) == ""
assert join_with_commas(["one", "two"]) == "one, two\"""", E, "trailing separator"),

    # ------------------------------------------------------------------ hard
    ("binary_search", "return the index of target in a sorted list of distinct integers, or -1 if absent",
     "def binary_search(xs, target):\n    lo, hi = 0, len(xs) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if xs[mid] == target:\n            return mid\n        if xs[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n",
     ("lo = mid + 1", "lo = mid"),
     """assert binary_search([1, 3, 5, 7, 9], 7) == 3
assert binary_search([1, 3, 5, 7, 9], 1) == 0
assert binary_search([1, 3, 5, 7, 9], 9) == 4
assert binary_search([1, 3, 5, 7, 9], 4) == -1
assert binary_search([], 3) == -1
assert binary_search([2], 2) == 0
assert binary_search([1, 3, 5, 7, 9], 10) == -1""", H, "infinite loop / pointer not advanced"),
    ("flatten", "flatten arbitrarily nested lists of values into one flat list, preserving order",
     "def flatten(nested):\n    result = []\n    for item in nested:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n",
     ("result.extend(flatten(item))", "result.append(flatten(item))"),
     """assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
assert flatten([]) == []
assert flatten([[], [[]]]) == []
assert flatten([1, 2]) == [1, 2]
assert flatten([[1], [2, [3]], [[4]]]) == [1, 2, 3, 4]""", H, "extend vs append in recursion"),
    ("add_item", "return a list containing item appended to the given list; if no list is given, start from a fresh empty list each call",
     "def add_item(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items\n",
     ("def add_item(item, items=None):\n    if items is None:\n        items = []\n", "def add_item(item, items=[]):\n"),
     """assert add_item(1) == [1]
assert add_item(2) == [2]
assert add_item(3, [9]) == [9, 3]
assert add_item(4) == [4]
base = []
add_item(5, base)
assert base == [5]""", H, "mutable default argument"),
    ("merge_sorted", "merge two already-sorted lists into one sorted list",
     "def merge_sorted(a, b):\n    i = j = 0\n    result = []\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i])\n            i += 1\n        else:\n            result.append(b[j])\n            j += 1\n    result.extend(a[i:])\n    result.extend(b[j:])\n    return result\n",
     ("    result.extend(b[j:])\n", ""),
     """assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
assert merge_sorted([], [1, 2]) == [1, 2]
assert merge_sorted([1, 2], []) == [1, 2]
assert merge_sorted([1, 2, 3], [7, 8]) == [1, 2, 3, 7, 8]
assert merge_sorted([5, 6], [1, 2]) == [1, 2, 5, 6]
assert merge_sorted([1, 1], [1]) == [1, 1, 1]""", H, "leftover elements dropped"),
    ("rotate_left", "rotate a list left by k positions (k may exceed the list length) and return the new list; an empty list returns an empty list",
     "def rotate_left(xs, k):\n    if not xs:\n        return []\n    k %= len(xs)\n    return xs[k:] + xs[:k]\n",
     ("    k %= len(xs)\n", ""),
     """assert rotate_left([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]
assert rotate_left([1, 2, 3], 0) == [1, 2, 3]
assert rotate_left([1, 2, 3], 3) == [1, 2, 3]
assert rotate_left([1, 2, 3], 4) == [2, 3, 1]
assert rotate_left([], 5) == []
assert rotate_left([1, 2, 3, 4], 9) == [2, 3, 4, 1]""", H, "missing modulo"),
    ("chunk", "split a list into consecutive chunks of size n; the last chunk may be shorter",
     "def chunk(xs, n):\n    return [xs[i:i + n] for i in range(0, len(xs), n)]\n",
     ("range(0, len(xs), n)", "range(0, len(xs) - n, n)"),
     """assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
assert chunk([], 3) == []
assert chunk([1, 2], 5) == [[1, 2]]
assert chunk([1, 2, 3], 1) == [[1], [2], [3]]""", H, "last chunk dropped"),
    ("running_max", "return a list where element i is the maximum of the input's first i+1 elements",
     "def running_max(xs):\n    out = []\n    current = None\n    for x in xs:\n        if current is None or x > current:\n            current = x\n        out.append(current)\n    return out\n",
     ("current = None\n    for x in xs:\n        if current is None or x > current:", "current = 0\n    for x in xs:\n        if x > current:"),
     """assert running_max([1, 3, 2, 5, 4]) == [1, 3, 3, 5, 5]
assert running_max([]) == []
assert running_max([-5, -3, -4]) == [-5, -3, -3]
assert running_max([7]) == [7]
assert running_max([2, 2, 2]) == [2, 2, 2]""", H, "bad initial value for negatives"),
    ("group_by_length", "group words by length: return a dict mapping each length to the list of words with that length, in input order",
     "def group_by_length(words):\n    groups = {}\n    for w in words:\n        groups.setdefault(len(w), []).append(w)\n    return groups\n",
     ("groups.setdefault(len(w), []).append(w)", "groups[len(w)] = [w]"),
     """assert group_by_length(["a", "bb", "c", "dd", "eee"]) == {1: ["a", "c"], 2: ["bb", "dd"], 3: ["eee"]}
assert group_by_length([]) == {}
assert group_by_length(["x"]) == {1: ["x"]}
assert group_by_length(["hi", "yo", "hey"]) == {2: ["hi", "yo"], 3: ["hey"]}""", H, "overwrites accumulated list"),
    ("kth_largest_distinct", "return the k-th largest DISTINCT value of a list (k starts at 1), or None if there are fewer than k distinct values",
     "def kth_largest_distinct(xs, k):\n    vals = sorted(set(xs), reverse=True)\n    return vals[k - 1] if 1 <= k <= len(vals) else None\n",
     ("sorted(set(xs), reverse=True)", "sorted(xs, reverse=True)"),
     """assert kth_largest_distinct([4, 4, 3, 1], 2) == 3
assert kth_largest_distinct([5, 5, 5], 2) is None
assert kth_largest_distinct([1, 2, 3], 1) == 3
assert kth_largest_distinct([9, 7, 7, 5], 3) == 5
assert kth_largest_distinct([], 1) is None
assert kth_largest_distinct([1, 2], 3) is None""", H, "duplicates not removed"),
    ("is_balanced", "return True if every (, [ and { in a string is closed by the matching bracket in the right order",
     "def is_balanced(s):\n    pairs = {\")\": \"(\", \"]\": \"[\", \"}\": \"{\"}\n    stack = []\n    for ch in s:\n        if ch in \"([{\":\n            stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop() != pairs[ch]:\n                return False\n    return not stack\n",
     ("    return not stack\n", "    return True\n"),
     """assert is_balanced("([]{})") is True
assert is_balanced("(((") is False
assert is_balanced("(]") is False
assert is_balanced("") is True
assert is_balanced("())") is False
assert is_balanced("{[()]}x") is True
assert is_balanced("([)]") is False""", H, "unclosed openers ignored"),
    ("moving_average", "return the list of averages of every window of k consecutive elements (empty if k exceeds the length)",
     "def moving_average(xs, k):\n    return [sum(xs[i:i + k]) / k for i in range(len(xs) - k + 1)]\n",
     ("range(len(xs) - k + 1)", "range(len(xs) - k)"),
     """assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
assert moving_average([1, 2, 3], 3) == [2.0]
assert moving_average([1, 2], 3) == []
assert moving_average([4, 4, 4, 4], 1) == [4.0, 4.0, 4.0, 4.0]
assert moving_average([], 2) == []""", H, "last window dropped"),
    ("dedupe_ignore_case", "remove words that repeat an earlier word ignoring case, keeping the first occurrence with its original casing",
     "def dedupe_ignore_case(words):\n    seen = set()\n    out = []\n    for w in words:\n        if w.lower() not in seen:\n            seen.add(w.lower())\n            out.append(w)\n    return out\n",
     ("if w.lower() not in seen:", "if w not in seen:"),
     """assert dedupe_ignore_case(["Apple", "apple", "Banana"]) == ["Apple", "Banana"]
assert dedupe_ignore_case([]) == []
assert dedupe_ignore_case(["a", "A", "a"]) == ["a"]
assert dedupe_ignore_case(["x", "y"]) == ["x", "y"]
assert dedupe_ignore_case(["Dog", "cat", "DOG", "Cat"]) == ["Dog", "cat"]""", H, "comparison not normalised"),
    ("transpose", "transpose a non-empty rectangular matrix given as a list of rows (rows and columns may differ in count)",
     "def transpose(matrix):\n    return [[row[j] for row in matrix] for j in range(len(matrix[0]))]\n",
     ("range(len(matrix[0]))", "range(len(matrix))"),
     """assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]
assert transpose([[1, 2, 3]]) == [[1], [2], [3]]
assert transpose([[1], [2], [3]]) == [[1, 2, 3]]
assert transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]""", H, "square-matrix assumption"),
    ("word_frequencies", "return a dict of how many times each word appears in a list of words",
     "def word_frequencies(words):\n    d = {}\n    for w in words:\n        d[w] = d.get(w, 0) + 1\n    return d\n",
     ("d.get(w, 0)", "d.get(w, 1)"),
     """assert word_frequencies(["a", "b", "a"]) == {"a": 2, "b": 1}
assert word_frequencies([]) == {}
assert word_frequencies(["x"]) == {"x": 1}
assert word_frequencies(["z", "z", "z"]) == {"z": 3}""", H, "wrong default in counter"),
    ("pairs_with_sum", "count the pairs of elements at different positions i < j whose sum equals target",
     "def pairs_with_sum(xs, target):\n    count = 0\n    for i in range(len(xs)):\n        for j in range(i + 1, len(xs)):\n            if xs[i] + xs[j] == target:\n                count += 1\n    return count\n",
     ("range(i + 1, len(xs))", "range(i, len(xs))"),
     """assert pairs_with_sum([1, 2, 3, 4], 5) == 2
assert pairs_with_sum([2, 2, 2], 4) == 3
assert pairs_with_sum([5], 10) == 0
assert pairs_with_sum([], 3) == 0
assert pairs_with_sum([1, 1], 2) == 1
assert pairs_with_sum([3, 3, 4], 6) == 1""", H, "element paired with itself"),
    ("insert_sorted", "return a NEW sorted list with value inserted into an already-sorted list; do not modify the input list",
     "def insert_sorted(xs, v):\n    out = list(xs)\n    i = 0\n    while i < len(out) and out[i] < v:\n        i += 1\n    out.insert(i, v)\n    return out\n",
     ("out = list(xs)", "out = xs"),
     """base = [1, 3, 5]
assert insert_sorted(base, 4) == [1, 3, 4, 5]
assert base == [1, 3, 5]
assert insert_sorted([], 2) == [2]
assert insert_sorted([1, 2], 0) == [0, 1, 2]
assert insert_sorted([1, 2], 9) == [1, 2, 9]
assert insert_sorted([2, 2], 2) == [2, 2, 2]""", H, "aliasing / mutates input"),
    ("longest_run", "return the length of the longest streak of equal consecutive elements (0 for an empty list)",
     "def longest_run(xs):\n    best = cur = 0\n    prev = object()\n    for x in xs:\n        if x == prev:\n            cur += 1\n        else:\n            cur = 1\n            prev = x\n        best = max(best, cur)\n    return best\n",
     ("            cur = 1\n", "            cur = 0\n"),
     """assert longest_run([1, 1, 2, 2, 2, 3]) == 3
assert longest_run([]) == 0
assert longest_run([7]) == 1
assert longest_run([1, 2, 3]) == 1
assert longest_run([4, 4, 4, 4]) == 4
assert longest_run([1, 1, 2, 1, 1]) == 2""", H, "reset to wrong value"),
    ("compress", "run-length encode a string: \"aaabcc\" -> \"a3b1c2\" (empty string -> empty string)",
     "def compress(s):\n    if not s:\n        return \"\"\n    out = []\n    count = 1\n    for i in range(1, len(s)):\n        if s[i] == s[i - 1]:\n            count += 1\n        else:\n            out.append(s[i - 1] + str(count))\n            count = 1\n    out.append(s[-1] + str(count))\n    return \"\".join(out)\n",
     ("    out.append(s[-1] + str(count))\n", ""),
     """assert compress("aaabcc") == "a3b1c2"
assert compress("") == ""
assert compress("a") == "a1"
assert compress("abc") == "a1b1c1"
assert compress("zzzz") == "z4"
assert compress("aabbaa") == "a2b2a2\"""", H, "final group not flushed"),
    ("fib", "return the n-th Fibonacci number with fib(0) = 0 and fib(1) = 1, iteratively",
     "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n",
     ("range(n)", "range(n - 1)"),
     """assert fib(0) == 0
assert fib(1) == 1
assert fib(2) == 1
assert fib(10) == 55
assert fib(20) == 6765""", H, "off-by-one iteration count"),
    ("days_in_month", "return the number of days in a given month (1-12) of a given year, handling leap years",
     "def days_in_month(year, month):\n    if month == 2:\n        leap = (year % 4 == 0 and year % 100 != 0) or year % 400 == 0\n        return 29 if leap else 28\n    return 30 if month in (4, 6, 9, 11) else 31\n",
     ("        return 29 if leap else 28\n", "        return 28\n"),
     """assert days_in_month(2023, 1) == 31
assert days_in_month(2023, 4) == 30
assert days_in_month(2023, 2) == 28
assert days_in_month(2024, 2) == 29
assert days_in_month(1900, 2) == 28
assert days_in_month(2000, 2) == 29
assert days_in_month(2023, 12) == 31""", H, "special case ignored"),
    ("is_prime", "return True if n is a prime number, else False (n may be 0, 1 or negative)",
     "def is_prime(n):\n    if n < 2:\n        return False\n    for d in range(2, int(n ** 0.5) + 1):\n        if n % d == 0:\n            return False\n    return True\n",
     ("int(n ** 0.5) + 1", "int(n ** 0.5)"),
     """assert is_prime(2) is True
assert is_prime(3) is True
assert is_prime(9) is False
assert is_prime(25) is False
assert is_prime(29) is True
assert is_prime(1) is False
assert is_prime(0) is False
assert is_prime(-7) is False
assert is_prime(49) is False""", H, "range excludes the square root"),
    ("diagonal_sum", "return the sum of both diagonals of a square matrix, counting the centre element only once for odd sizes",
     "def diagonal_sum(m):\n    n = len(m)\n    total = sum(m[i][i] + m[i][n - 1 - i] for i in range(n))\n    if n % 2:\n        total -= m[n // 2][n // 2]\n    return total\n",
     ("    if n % 2:\n        total -= m[n // 2][n // 2]\n", ""),
     """assert diagonal_sum([[1, 2], [3, 4]]) == 10
assert diagonal_sum([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == 25
assert diagonal_sum([[5]]) == 5
assert diagonal_sum([[1, 0, 1], [0, 1, 0], [1, 0, 1]]) == 5""", H, "centre element double-counted"),
    ("top_k_frequent", "return the k most frequent values; ties are broken by the smaller value first",
     "def top_k_frequent(xs, k):\n    counts = {}\n    for x in xs:\n        counts[x] = counts.get(x, 0) + 1\n    return sorted(counts, key=lambda x: (-counts[x], x))[:k]\n",
     ("key=lambda x: (-counts[x], x)", "key=lambda x: -counts[x]"),
     """assert top_k_frequent([1, 1, 2, 2, 3], 2) == [1, 2]
assert top_k_frequent([3, 3, 2, 2, 1], 2) == [2, 3]
assert top_k_frequent([5, 4, 4, 5, 9], 1) == [4]
assert top_k_frequent([9, 7, 8], 3) == [7, 8, 9]
assert top_k_frequent([], 2) == []""", H, "tie-break ignored"),
    ("remove_all", "return a new list with every occurrence of val removed (the input list should be left unchanged)",
     "def remove_all(lst, val):\n    return [x for x in lst if x != val]\n",
     ("    return [x for x in lst if x != val]\n", "    for x in lst:\n        if x == val:\n            lst.remove(x)\n    return lst\n"),
     """data = [1, 2, 2, 3, 2]
assert remove_all(data, 2) == [1, 3]
assert data == [1, 2, 2, 3, 2]
assert remove_all([2, 2, 2], 2) == []
assert remove_all([], 1) == []
assert remove_all([1, 3], 2) == [1, 3]""", H, "mutation while iterating"),
    ("copy_grid", "return an independent deep copy of a list of lists, so that changing the copy never changes the original",
     "def copy_grid(grid):\n    return [row[:] for row in grid]\n",
     ("[row[:] for row in grid]", "[row for row in grid]"),
     """g = [[1, 2], [3, 4]]
c = copy_grid(g)
assert c == g
c[0][0] = 99
assert g == [[1, 2], [3, 4]]
assert c is not g
assert copy_grid([]) == []""", H, "shallow copy"),
]
