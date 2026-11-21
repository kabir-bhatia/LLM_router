"""Code-generation items: (name, signature, spec, REFERENCE solution, hidden tests, difficulty).
The reference must pass every test (checked in build_code_tasks.py)."""

E, H = "easy", "hard"

ITEMS = [
    # ------------------------------------------------------------------ easy
    ("sum_of_evens", "sum_of_evens(nums)", "returns the sum of the even integers in the list nums (0 for an empty list or if there are none)",
     "def sum_of_evens(nums):\n    return sum(n for n in nums if n % 2 == 0)\n",
     """assert sum_of_evens([1, 2, 3, 4]) == 6
assert sum_of_evens([]) == 0
assert sum_of_evens([1, 3, 5]) == 0
assert sum_of_evens([-2, -3, 4]) == 2
assert sum_of_evens([0]) == 0
assert sum_of_evens([10]) == 10""", E),
    ("count_char", "count_char(s, ch)", "counts how many times the single character ch occurs in the string s (case-sensitive)",
     "def count_char(s, ch):\n    return sum(1 for c in s if c == ch)\n",
     """assert count_char("banana", "a") == 3
assert count_char("Banana", "b") == 0
assert count_char("", "x") == 0
assert count_char("aaaa", "a") == 4
assert count_char("hello world", " ") == 1
assert count_char("abc", "z") == 0""", E),
    ("is_anagram", "is_anagram(a, b)", "returns True if the strings a and b are anagrams of each other, ignoring case and spaces",
     "def is_anagram(a, b):\n    norm = lambda s: sorted(s.replace(' ', '').lower())\n    return norm(a) == norm(b)\n",
     """assert is_anagram("listen", "silent") is True
assert is_anagram("Dormitory", "dirty room") is True
assert is_anagram("hello", "world") is False
assert is_anagram("", "") is True
assert is_anagram("aab", "abb") is False
assert is_anagram("a", "A") is True""", E),
    ("reverse_words", "reverse_words(s)", "returns the words of the string s in reverse order, joined by single spaces (extra whitespace in s is ignored)",
     "def reverse_words(s):\n    return ' '.join(reversed(s.split()))\n",
     """assert reverse_words("hello world") == "world hello"
assert reverse_words("  a  b   c ") == "c b a"
assert reverse_words("") == ""
assert reverse_words("single") == "single"
assert reverse_words("one two three four") == "four three two one\"""", E),
    ("find_max_index", "find_max_index(xs)", "returns the index of the FIRST occurrence of the largest value in the list xs, or None if xs is empty",
     "def find_max_index(xs):\n    if not xs:\n        return None\n    best = 0\n    for i, x in enumerate(xs):\n        if x > xs[best]:\n            best = i\n    return best\n",
     """assert find_max_index([1, 5, 3]) == 1
assert find_max_index([]) is None
assert find_max_index([4, 4, 4]) == 0
assert find_max_index([2, 9, 9, 1]) == 1
assert find_max_index([-5, -2, -9]) == 1
assert find_max_index([7]) == 0""", E),
    ("char_frequency", "char_frequency(s)", "returns a dict mapping each character of s to the number of times it appears",
     "def char_frequency(s):\n    d = {}\n    for c in s:\n        d[c] = d.get(c, 0) + 1\n    return d\n",
     """assert char_frequency("aab") == {"a": 2, "b": 1}
assert char_frequency("") == {}
assert char_frequency("a a") == {"a": 2, " ": 1}
assert char_frequency("Aa") == {"A": 1, "a": 1}
assert char_frequency("zzz") == {"z": 3}""", E),
    ("multiples", "multiples(n, k)", "returns a list of the first k positive multiples of n, in increasing order (empty list if k <= 0)",
     "def multiples(n, k):\n    return [n * i for i in range(1, k + 1)]\n",
     """assert multiples(3, 4) == [3, 6, 9, 12]
assert multiples(5, 1) == [5]
assert multiples(7, 0) == []
assert multiples(2, -3) == []
assert multiples(10, 3) == [10, 20, 30]""", E),
    ("is_sorted", "is_sorted(xs)", "returns True if the list xs is in non-decreasing order (an empty or one-element list counts as sorted)",
     "def is_sorted(xs):\n    return all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))\n",
     """assert is_sorted([1, 2, 3]) is True
assert is_sorted([1, 1, 2]) is True
assert is_sorted([3, 2, 1]) is False
assert is_sorted([]) is True
assert is_sorted([5]) is True
assert is_sorted([1, 3, 2, 4]) is False""", E),
    ("remove_vowels", "remove_vowels(s)", "returns s with all vowels (a, e, i, o, u in either case) removed",
     "def remove_vowels(s):\n    return ''.join(c for c in s if c.lower() not in 'aeiou')\n",
     """assert remove_vowels("hello") == "hll"
assert remove_vowels("AEIOU") == ""
assert remove_vowels("") == ""
assert remove_vowels("Python Programming") == "Pythn Prgrmmng"
assert remove_vowels("xyz") == "xyz\"""", E),
    ("middle_element", "middle_element(xs)", "returns the middle element of the list xs; for an even-length list return the first of the two middle elements; return None for an empty list",
     "def middle_element(xs):\n    if not xs:\n        return None\n    return xs[(len(xs) - 1) // 2]\n",
     """assert middle_element([1, 2, 3]) == 2
assert middle_element([1, 2, 3, 4]) == 2
assert middle_element([]) is None
assert middle_element([9]) == 9
assert middle_element([5, 6]) == 5
assert middle_element(["a", "b", "c", "d", "e"]) == "c\"""", E),
    ("product_of_list", "product_of_list(xs)", "returns the product of all numbers in the list xs (1 for an empty list)",
     "def product_of_list(xs):\n    p = 1\n    for x in xs:\n        p *= x\n    return p\n",
     """assert product_of_list([2, 3, 4]) == 24
assert product_of_list([]) == 1
assert product_of_list([5]) == 5
assert product_of_list([2, 0, 9]) == 0
assert product_of_list([-1, 3]) == -3
assert product_of_list([-2, -2]) == 4""", E),
    ("second_word", "second_word(s)", "returns the second whitespace-separated word of s, or the empty string if s has fewer than two words",
     "def second_word(s):\n    w = s.split()\n    return w[1] if len(w) > 1 else ''\n",
     """assert second_word("hello big world") == "big"
assert second_word("only") == ""
assert second_word("") == ""
assert second_word("  a   b  ") == "b"
assert second_word("x y") == "y\"""", E),
    ("count_positive", "count_positive(xs)", "returns how many numbers in xs are strictly greater than zero",
     "def count_positive(xs):\n    return sum(1 for x in xs if x > 0)\n",
     """assert count_positive([1, -2, 3]) == 2
assert count_positive([]) == 0
assert count_positive([0, 0]) == 0
assert count_positive([-1, -2]) == 0
assert count_positive([0.5, -0.5, 2]) == 2""", E),
    ("repeat_with_dash", "repeat_with_dash(s, n)", "returns the string s repeated n times, separated by single dashes (\"ab\", 3 -> \"ab-ab-ab\"); returns \"\" when n <= 0",
     "def repeat_with_dash(s, n):\n    return '-'.join([s] * n) if n > 0 else ''\n",
     """assert repeat_with_dash("ab", 3) == "ab-ab-ab"
assert repeat_with_dash("x", 1) == "x"
assert repeat_with_dash("x", 0) == ""
assert repeat_with_dash("x", -2) == ""
assert repeat_with_dash("", 3) == "--\"""", E),
    ("is_power_of_two", "is_power_of_two(n)", "returns True if the integer n is a positive power of two (1, 2, 4, 8, ...), else False",
     "def is_power_of_two(n):\n    return n > 0 and (n & (n - 1)) == 0\n",
     """assert is_power_of_two(1) is True
assert is_power_of_two(16) is True
assert is_power_of_two(18) is False
assert is_power_of_two(0) is False
assert is_power_of_two(-8) is False
assert is_power_of_two(1024) is True
assert is_power_of_two(1000) is False""", E),
    ("list_diff", "list_diff(a, b)", "returns the elements of list a that do not appear in list b, keeping their order and duplicates from a",
     "def list_diff(a, b):\n    bs = set(b)\n    return [x for x in a if x not in bs]\n",
     """assert list_diff([1, 2, 3, 4], [2, 4]) == [1, 3]
assert list_diff([1, 1, 2], [2]) == [1, 1]
assert list_diff([], [1]) == []
assert list_diff([1, 2], []) == [1, 2]
assert list_diff(["a", "b"], ["b", "c"]) == ["a"]""", E),
    ("to_camel_case", "to_camel_case(s)", "converts a snake_case string to camelCase: \"hello_big_world\" -> \"helloBigWorld\" (a string with no underscore is returned unchanged)",
     "def to_camel_case(s):\n    parts = s.split('_')\n    return parts[0] + ''.join(p.capitalize() for p in parts[1:])\n",
     """assert to_camel_case("hello_big_world") == "helloBigWorld"
assert to_camel_case("single") == "single"
assert to_camel_case("a_b") == "aB"
assert to_camel_case("") == ""
assert to_camel_case("x_y_z") == "xYZ\"""", E),
    ("count_even_digits", "count_even_digits(n)", "returns how many digits of the non-negative integer n are even (0 counts as even; count_even_digits(0) is 1)",
     "def count_even_digits(n):\n    return sum(1 for d in str(n) if int(d) % 2 == 0)\n",
     """assert count_even_digits(0) == 1
assert count_even_digits(1357) == 0
assert count_even_digits(2468) == 4
assert count_even_digits(1002) == 3
assert count_even_digits(7) == 0""", E),
    ("swap_pairs", "swap_pairs(xs)", "returns a new list in which each adjacent pair of elements is swapped, [1,2,3,4,5] -> [2,1,4,3,5]; a final unpaired element stays in place",
     "def swap_pairs(xs):\n    out = list(xs)\n    for i in range(0, len(out) - 1, 2):\n        out[i], out[i + 1] = out[i + 1], out[i]\n    return out\n",
     """assert swap_pairs([1, 2, 3, 4, 5]) == [2, 1, 4, 3, 5]
assert swap_pairs([1, 2]) == [2, 1]
assert swap_pairs([]) == []
assert swap_pairs([7]) == [7]
data = [1, 2, 3]
assert swap_pairs(data) == [2, 1, 3]
assert data == [1, 2, 3]""", E),
    ("longest_word", "longest_word(s)", "returns the longest whitespace-separated word in s (the first one if there is a tie), or the empty string if s has no words",
     "def longest_word(s):\n    best = ''\n    for w in s.split():\n        if len(w) > len(best):\n            best = w\n    return best\n",
     """assert longest_word("the quick brown fox") == "quick"
assert longest_word("") == ""
assert longest_word("aa bb cc") == "aa"
assert longest_word("a bbb cc dddd ee") == "dddd"
assert longest_word("   ") == ""
assert longest_word("word") == "word\"""", E),
    ("bmi_category", "bmi_category(weight_kg, height_m)", "computes BMI = weight_kg / height_m**2 and returns \"underweight\" if BMI < 18.5, \"normal\" if BMI < 25, \"overweight\" if BMI < 30, otherwise \"obese\"",
     "def bmi_category(weight_kg, height_m):\n    bmi = weight_kg / height_m ** 2\n    if bmi < 18.5:\n        return 'underweight'\n    if bmi < 25:\n        return 'normal'\n    if bmi < 30:\n        return 'overweight'\n    return 'obese'\n",
     """assert bmi_category(50, 1.8) == "underweight"
assert bmi_category(70, 1.75) == "normal"
assert bmi_category(85, 1.75) == "overweight"
assert bmi_category(110, 1.75) == "obese"
assert bmi_category(25, 1.0) == "overweight"
assert bmi_category(18.5, 1.0) == "normal"
assert bmi_category(30, 1.0) == "obese\"""", E),
    ("gcd", "gcd(a, b)", "returns the greatest common divisor of two non-negative integers (gcd(0, n) is n; gcd(0, 0) is 0)",
     "def gcd(a, b):\n    while b:\n        a, b = b, a % b\n    return a\n",
     """assert gcd(12, 18) == 6
assert gcd(17, 5) == 1
assert gcd(0, 7) == 7
assert gcd(9, 0) == 9
assert gcd(0, 0) == 0
assert gcd(100, 25) == 25
assert gcd(48, 36) == 12""", E),
    ("caesar_shift", "caesar_shift(s, k)", "shifts each letter of s forward by k positions in the alphabet (wrapping around z -> a), preserving case and leaving non-letters unchanged; k may be larger than 26",
     "def caesar_shift(s, k):\n    out = []\n    for c in s:\n        if c.isalpha() and c.isascii():\n            base = ord('A') if c.isupper() else ord('a')\n            out.append(chr((ord(c) - base + k) % 26 + base))\n        else:\n            out.append(c)\n    return ''.join(out)\n",
     """assert caesar_shift("abc", 1) == "bcd"
assert caesar_shift("xyz", 3) == "abc"
assert caesar_shift("Hello, World!", 5) == "Mjqqt, Btwqi!"
assert caesar_shift("abc", 0) == "abc"
assert caesar_shift("abc", 27) == "bcd"
assert caesar_shift("", 4) == ""
assert caesar_shift("ZzAa", 1) == "AaBb\"""", E),
    ("is_valid_password", "is_valid_password(p)", "returns True only if the string p has at least 8 characters and contains at least one uppercase letter, one lowercase letter and one digit",
     "def is_valid_password(p):\n    return (len(p) >= 8 and any(c.isupper() for c in p)\n            and any(c.islower() for c in p) and any(c.isdigit() for c in p))\n",
     """assert is_valid_password("Passw0rdX") is True
assert is_valid_password("short1A") is False
assert is_valid_password("alllowercase1") is False
assert is_valid_password("ALLUPPERCASE1") is False
assert is_valid_password("NoDigitsHere") is False
assert is_valid_password("Exact8Ch") is True
assert is_valid_password("") is False""", E),
    ("triangle_type", "triangle_type(a, b, c)", "classifies a triangle by its side lengths: returns \"invalid\" if any side is <= 0 or the sides violate the triangle inequality (a degenerate triangle, where two sides sum exactly to the third, is invalid), otherwise \"equilateral\", \"isosceles\" or \"scalene\"",
     "def triangle_type(a, b, c):\n    if min(a, b, c) <= 0:\n        return 'invalid'\n    x, y, z = sorted((a, b, c))\n    if x + y <= z:\n        return 'invalid'\n    if x == y == z:\n        return 'equilateral'\n    if x == y or y == z:\n        return 'isosceles'\n    return 'scalene'\n",
     """assert triangle_type(3, 3, 3) == "equilateral"
assert triangle_type(3, 3, 4) == "isosceles"
assert triangle_type(3, 4, 5) == "scalene"
assert triangle_type(1, 2, 3) == "invalid"
assert triangle_type(0, 1, 1) == "invalid"
assert triangle_type(1, 1, 5) == "invalid"
assert triangle_type(5, 3, 3) == "isosceles"
assert triangle_type(-1, 2, 2) == "invalid\"""", E),

    # ------------------------------------------------------------------ hard
    ("roman_to_int", "roman_to_int(s)", "converts a valid Roman numeral string (I, V, X, L, C, D, M with subtractive pairs like IV, IX, XL, XC, CD, CM) to an integer",
     "def roman_to_int(s):\n    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}\n    total = 0\n    for i, ch in enumerate(s):\n        v = vals[ch]\n        if i + 1 < len(s) and vals[s[i + 1]] > v:\n            total -= v\n        else:\n            total += v\n    return total\n",
     """assert roman_to_int("III") == 3
assert roman_to_int("IV") == 4
assert roman_to_int("IX") == 9
assert roman_to_int("LVIII") == 58
assert roman_to_int("MCMXCIV") == 1994
assert roman_to_int("MMMCMXCIX") == 3999
assert roman_to_int("XL") == 40
assert roman_to_int("CD") == 400""", H),
    ("int_to_roman", "int_to_roman(n)", "converts an integer 1 <= n <= 3999 to its standard Roman numeral (using subtractive notation such as IV and CM)",
     "def int_to_roman(n):\n    table = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]\n    out = []\n    for v, sym in table:\n        while n >= v:\n            out.append(sym)\n            n -= v\n    return ''.join(out)\n",
     """assert int_to_roman(3) == "III"
assert int_to_roman(4) == "IV"
assert int_to_roman(9) == "IX"
assert int_to_roman(58) == "LVIII"
assert int_to_roman(1994) == "MCMXCIV"
assert int_to_roman(3999) == "MMMCMXCIX"
assert int_to_roman(444) == "CDXLIV\"""", H),
    ("longest_common_prefix", "longest_common_prefix(strs)", "returns the longest common prefix shared by all strings in the list strs (empty string if there is none or the list is empty)",
     "def longest_common_prefix(strs):\n    if not strs:\n        return ''\n    prefix = strs[0]\n    for s in strs[1:]:\n        while not s.startswith(prefix):\n            prefix = prefix[:-1]\n    return prefix\n",
     """assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"
assert longest_common_prefix(["dog", "racecar", "car"]) == ""
assert longest_common_prefix([]) == ""
assert longest_common_prefix(["alone"]) == "alone"
assert longest_common_prefix(["abc", "abc", "abc"]) == "abc"
assert longest_common_prefix(["", "abc"]) == ""
assert longest_common_prefix(["interview", "internet", "interval"]) == "inter\"""", H),
    ("spiral_order", "spiral_order(matrix)", "returns the elements of a rectangular matrix (list of equal-length rows) in clockwise spiral order starting at the top-left corner; an empty matrix gives an empty list",
     "def spiral_order(matrix):\n    out = []\n    if not matrix:\n        return out\n    top, bottom, left, right = 0, len(matrix) - 1, 0, len(matrix[0]) - 1\n    while top <= bottom and left <= right:\n        for j in range(left, right + 1):\n            out.append(matrix[top][j])\n        for i in range(top + 1, bottom + 1):\n            out.append(matrix[i][right])\n        if top < bottom and left < right:\n            for j in range(right - 1, left - 1, -1):\n                out.append(matrix[bottom][j])\n            for i in range(bottom - 1, top, -1):\n                out.append(matrix[i][left])\n        top += 1\n        bottom -= 1\n        left += 1\n        right -= 1\n    return out\n",
     """assert spiral_order([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
assert spiral_order([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
assert spiral_order([]) == []
assert spiral_order([[1]]) == [1]
assert spiral_order([[1, 2, 3]]) == [1, 2, 3]
assert spiral_order([[1], [2], [3]]) == [1, 2, 3]
assert spiral_order([[1, 2], [3, 4]]) == [1, 2, 4, 3]""", H),
    ("is_valid_ipv4", "is_valid_ipv4(s)", "returns True if s is a valid dotted-decimal IPv4 address: exactly four numbers separated by dots, each 0-255 written without leading zeros (\"0\" is fine, \"01\" is not) and containing only digits",
     "def is_valid_ipv4(s):\n    parts = s.split('.')\n    if len(parts) != 4:\n        return False\n    for p in parts:\n        if not p.isdigit() or not p.isascii():\n            return False\n        if len(p) > 1 and p[0] == '0':\n            return False\n        if int(p) > 255:\n            return False\n    return True\n",
     """assert is_valid_ipv4("192.168.1.1") is True
assert is_valid_ipv4("255.255.255.255") is True
assert is_valid_ipv4("0.0.0.0") is True
assert is_valid_ipv4("256.1.1.1") is False
assert is_valid_ipv4("1.2.3") is False
assert is_valid_ipv4("1.2.3.4.5") is False
assert is_valid_ipv4("01.2.3.4") is False
assert is_valid_ipv4("a.b.c.d") is False
assert is_valid_ipv4("1.2.3.") is False
assert is_valid_ipv4("") is False""", H),
    ("two_sum", "two_sum(nums, target)", "returns [i, j] with i < j and nums[i] + nums[j] == target; if several pairs work, return the one with the smallest i, and for that i the smallest j; return None if no pair exists",
     "def two_sum(nums, target):\n    for i in range(len(nums)):\n        for j in range(i + 1, len(nums)):\n            if nums[i] + nums[j] == target:\n                return [i, j]\n    return None\n",
     """assert two_sum([2, 7, 11, 15], 9) == [0, 1]
assert two_sum([3, 2, 4], 6) == [1, 2]
assert two_sum([3, 3], 6) == [0, 1]
assert two_sum([1, 2, 3], 10) is None
assert two_sum([], 1) is None
assert two_sum([1, 4, 5, 6, 3], 9) == [1, 2]
assert two_sum([5], 5) is None
assert two_sum([-1, -2, -3, -4], -6) == [1, 3]""", H),
    ("merge_intervals", "merge_intervals(intervals)", "merges overlapping or touching intervals (each a [start, end] list with start <= end; [1,3] and [3,5] touch and merge) and returns the merged intervals sorted by start; the input may be unsorted",
     "def merge_intervals(intervals):\n    out = []\n    for s, e in sorted(intervals):\n        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n        else:\n            out.append([s, e])\n    return out\n",
     """assert merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
assert merge_intervals([[1, 4], [4, 5]]) == [[1, 5]]
assert merge_intervals([]) == []
assert merge_intervals([[5, 6], [1, 2]]) == [[1, 2], [5, 6]]
assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]
assert merge_intervals([[2, 3]]) == [[2, 3]]
assert merge_intervals([[1, 2], [3, 4]]) == [[1, 2], [3, 4]]""", H),
    ("max_subarray_sum", "max_subarray_sum(nums)", "returns the largest sum of a non-empty contiguous subarray of nums (0 if nums is empty); the answer may be negative if all numbers are negative",
     "def max_subarray_sum(nums):\n    if not nums:\n        return 0\n    best = cur = nums[0]\n    for x in nums[1:]:\n        cur = max(x, cur + x)\n        best = max(best, cur)\n    return best\n",
     """assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
assert max_subarray_sum([1]) == 1
assert max_subarray_sum([-3, -1, -2]) == -1
assert max_subarray_sum([]) == 0
assert max_subarray_sum([5, 4, -1, 7, 8]) == 23
assert max_subarray_sum([-1, 2]) == 2
assert max_subarray_sum([0, 0]) == 0""", H),
    ("group_anagrams", "group_anagrams(words)", "groups words that are anagrams of each other; returns a list of groups, where each group keeps input order and the groups are ordered by the first appearance of their earliest member",
     "def group_anagrams(words):\n    groups = {}\n    for w in words:\n        groups.setdefault(''.join(sorted(w)), []).append(w)\n    return list(groups.values())\n",
     """assert group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]) == [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]
assert group_anagrams([]) == []
assert group_anagrams([""]) == [[""]]
assert group_anagrams(["a", "b", "a"]) == [["a", "a"], ["b"]]
assert group_anagrams(["ab", "ba", "ab"]) == [["ab", "ba", "ab"]]
assert group_anagrams(["abc", "def"]) == [["abc"], ["def"]]""", H),
    ("evaluate_rpn", "evaluate_rpn(tokens)", "evaluates a reverse Polish notation expression given as a list of string tokens (integers and + - * /); division truncates toward zero; returns an int",
     "def evaluate_rpn(tokens):\n    st = []\n    for t in tokens:\n        if t in ('+', '-', '*', '/'):\n            b, a = st.pop(), st.pop()\n            if t == '+':\n                st.append(a + b)\n            elif t == '-':\n                st.append(a - b)\n            elif t == '*':\n                st.append(a * b)\n            else:\n                st.append(int(a / b))\n        else:\n            st.append(int(t))\n    return st[0]\n",
     """assert evaluate_rpn(["2", "1", "+", "3", "*"]) == 9
assert evaluate_rpn(["4", "13", "5", "/", "+"]) == 6
assert evaluate_rpn(["7"]) == 7
assert evaluate_rpn(["10", "6", "9", "3", "+", "-11", "*", "/", "*", "17", "+", "5", "+"]) == 22
assert evaluate_rpn(["3", "4", "-"]) == -1
assert evaluate_rpn(["-7", "2", "/"]) == -3
assert evaluate_rpn(["7", "-2", "/"]) == -3""", H),
    ("decode_string", "decode_string(s)", "decodes strings of the form k[encoded] meaning encoded repeated k times, with nesting allowed (\"3[a2[c]]\" -> \"accaccacc\"); letters outside brackets are kept; k can have several digits",
     "def decode_string(s):\n    stack = []\n    cur = ''\n    num = 0\n    for ch in s:\n        if ch.isdigit():\n            num = num * 10 + int(ch)\n        elif ch == '[':\n            stack.append((cur, num))\n            cur, num = '', 0\n        elif ch == ']':\n            prev, k = stack.pop()\n            cur = prev + cur * k\n        else:\n            cur += ch\n    return cur\n",
     """assert decode_string("3[a]2[bc]") == "aaabcbc"
assert decode_string("3[a2[c]]") == "accaccacc"
assert decode_string("2[abc]3[cd]ef") == "abcabccdcdcdef"
assert decode_string("abc") == "abc"
assert decode_string("") == ""
assert decode_string("10[x]") == "xxxxxxxxxx"
assert decode_string("a2[b]c") == "abbc\"""", H),
    ("count_islands", "count_islands(grid)", "counts the islands in a grid given as a list of strings of \"1\" (land) and \"0\" (water); an island is a maximal group of land cells connected horizontally or vertically (not diagonally)",
     "def count_islands(grid):\n    if not grid:\n        return 0\n    rows, cols = len(grid), len(grid[0])\n    seen = set()\n    count = 0\n    for r in range(rows):\n        for c in range(cols):\n            if grid[r][c] == '1' and (r, c) not in seen:\n                count += 1\n                stack = [(r, c)]\n                seen.add((r, c))\n                while stack:\n                    y, x = stack.pop()\n                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):\n                        ny, nx = y + dy, x + dx\n                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == '1' and (ny, nx) not in seen:\n                            seen.add((ny, nx))\n                            stack.append((ny, nx))\n    return count\n",
     """assert count_islands(["11000", "11000", "00100", "00011"]) == 3
assert count_islands([]) == 0
assert count_islands(["000"]) == 0
assert count_islands(["111", "111"]) == 1
assert count_islands(["101", "010", "101"]) == 5
assert count_islands(["1"]) == 1
assert count_islands(["10", "01"]) == 2""", H),
    ("min_coins", "min_coins(coins, amount)", "returns the minimum number of coins from the list coins (unlimited supply of each denomination) needed to make exactly amount, or -1 if it is impossible; amount 0 needs 0 coins",
     "def min_coins(coins, amount):\n    INF = float('inf')\n    dp = [0] + [INF] * amount\n    for a in range(1, amount + 1):\n        for c in coins:\n            if c <= a and dp[a - c] + 1 < dp[a]:\n                dp[a] = dp[a - c] + 1\n    return dp[amount] if dp[amount] != INF else -1\n",
     """assert min_coins([1, 2, 5], 11) == 3
assert min_coins([2], 3) == -1
assert min_coins([1], 0) == 0
assert min_coins([1, 3, 4], 6) == 2
assert min_coins([5, 10], 7) == -1
assert min_coins([186, 419, 83, 408], 6249) == 20
assert min_coins([], 0) == 0""", H),
    ("longest_unique_substring", "longest_unique_substring(s)", "returns the length of the longest substring of s that contains no repeated character",
     "def longest_unique_substring(s):\n    last = {}\n    start = best = 0\n    for i, ch in enumerate(s):\n        if ch in last and last[ch] >= start:\n            start = last[ch] + 1\n        last[ch] = i\n        best = max(best, i - start + 1)\n    return best\n",
     """assert longest_unique_substring("abcabcbb") == 3
assert longest_unique_substring("bbbbb") == 1
assert longest_unique_substring("pwwkew") == 3
assert longest_unique_substring("") == 0
assert longest_unique_substring("abba") == 2
assert longest_unique_substring("dvdf") == 3
assert longest_unique_substring("abcdef") == 6""", H),
    ("next_permutation", "next_permutation(xs)", "returns the lexicographically next permutation of the list xs as a NEW list; if xs is already the largest permutation, returns the smallest one (ascending order); the input is not modified",
     "def next_permutation(xs):\n    a = list(xs)\n    i = len(a) - 2\n    while i >= 0 and a[i] >= a[i + 1]:\n        i -= 1\n    if i >= 0:\n        j = len(a) - 1\n        while a[j] <= a[i]:\n            j -= 1\n        a[i], a[j] = a[j], a[i]\n    a[i + 1:] = reversed(a[i + 1:])\n    return a\n",
     """assert next_permutation([1, 2, 3]) == [1, 3, 2]
assert next_permutation([3, 2, 1]) == [1, 2, 3]
assert next_permutation([1, 1, 5]) == [1, 5, 1]
assert next_permutation([]) == []
assert next_permutation([1]) == [1]
assert next_permutation([1, 3, 2]) == [2, 1, 3]
data = [1, 2, 3]
next_permutation(data)
assert data == [1, 2, 3]
assert next_permutation([2, 3, 1]) == [3, 1, 2]""", H),
    ("pascal_row", "pascal_row(n)", "returns row n (0-indexed) of Pascal's triangle as a list of integers; pascal_row(0) is [1]",
     "def pascal_row(n):\n    row = [1]\n    for _ in range(n):\n        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]\n    return row\n",
     """assert pascal_row(0) == [1]
assert pascal_row(1) == [1, 1]
assert pascal_row(2) == [1, 2, 1]
assert pascal_row(4) == [1, 4, 6, 4, 1]
assert pascal_row(6) == [1, 6, 15, 20, 15, 6, 1]
assert sum(pascal_row(10)) == 1024""", H),
    ("word_wrap", "word_wrap(text, width)", "greedily wraps the words of text into lines of at most width characters, joining words with single spaces; a word longer than width gets its own line; returns the list of lines (empty list if there are no words)",
     "def word_wrap(text, width):\n    lines, cur = [], ''\n    for w in text.split():\n        if not cur:\n            cur = w\n        elif len(cur) + 1 + len(w) <= width:\n            cur += ' ' + w\n        else:\n            lines.append(cur)\n            cur = w\n    if cur:\n        lines.append(cur)\n    return lines\n",
     """assert word_wrap("the quick brown fox", 10) == ["the quick", "brown fox"]
assert word_wrap("", 5) == []
assert word_wrap("a b c d", 3) == ["a b", "c d"]
assert word_wrap("extraordinary day", 5) == ["extraordinary", "day"]
assert word_wrap("one", 10) == ["one"]
assert word_wrap("aa bb", 5) == ["aa bb"]
assert word_wrap("aa bb", 4) == ["aa", "bb"]""", H),
    ("lcs_length", "lcs_length(a, b)", "returns the length of the longest common SUBSEQUENCE of strings a and b (characters in order but not necessarily contiguous)",
     "def lcs_length(a, b):\n    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]\n    for i in range(1, len(a) + 1):\n        for j in range(1, len(b) + 1):\n            if a[i - 1] == b[j - 1]:\n                dp[i][j] = dp[i - 1][j - 1] + 1\n            else:\n                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])\n    return dp[-1][-1]\n",
     """assert lcs_length("abcde", "ace") == 3
assert lcs_length("abc", "abc") == 3
assert lcs_length("abc", "def") == 0
assert lcs_length("", "abc") == 0
assert lcs_length("AGGTAB", "GXTXAYB") == 4
assert lcs_length("abcbdab", "bdcaba") == 4
assert lcs_length("a", "a") == 1""", H),
    ("to_base", "to_base(n, b)", "converts the integer n (possibly negative or zero) to a string in base b, where 2 <= b <= 16, using digits 0-9 and uppercase A-F, with a leading '-' for negative numbers and no leading zeros",
     "def to_base(n, b):\n    if n == 0:\n        return '0'\n    digits = '0123456789ABCDEF'\n    sign = '-' if n < 0 else ''\n    n = abs(n)\n    out = []\n    while n:\n        out.append(digits[n % b])\n        n //= b\n    return sign + ''.join(reversed(out))\n",
     """assert to_base(10, 2) == "1010"
assert to_base(255, 16) == "FF"
assert to_base(0, 7) == "0"
assert to_base(-10, 2) == "-1010"
assert to_base(255, 8) == "377"
assert to_base(1, 2) == "1"
assert to_base(4095, 16) == "FFF"
assert to_base(35, 12) == "2B\"""", H),
    ("matrix_multiply", "matrix_multiply(a, b)", "multiplies matrix a (m x n) by matrix b (n x p), both lists of rows, and returns the m x p product as a list of rows",
     "def matrix_multiply(a, b):\n    n, p = len(b), len(b[0])\n    return [[sum(row[k] * b[k][j] for k in range(n)) for j in range(p)] for row in a]\n",
     """assert matrix_multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]
assert matrix_multiply([[1, 2, 3]], [[1], [2], [3]]) == [[14]]
assert matrix_multiply([[1], [2]], [[3, 4]]) == [[3, 4], [6, 8]]
assert matrix_multiply([[2]], [[5]]) == [[10]]
assert matrix_multiply([[1, 0], [0, 1]], [[9, 8], [7, 6]]) == [[9, 8], [7, 6]]
assert matrix_multiply([[1, 2, 3], [4, 5, 6]], [[1, 0], [0, 1], [1, 1]]) == [[4, 5], [10, 11]]""", H),
    ("find_duplicates", "find_duplicates(xs)", "returns a sorted list (ascending) of the distinct values that appear more than once in xs",
     "def find_duplicates(xs):\n    seen, dup = set(), set()\n    for x in xs:\n        if x in seen:\n            dup.add(x)\n        seen.add(x)\n    return sorted(dup)\n",
     """assert find_duplicates([1, 2, 2, 3, 3, 3]) == [2, 3]
assert find_duplicates([]) == []
assert find_duplicates([1, 2, 3]) == []
assert find_duplicates([5, 5, 5, 5]) == [5]
assert find_duplicates([9, 1, 9, 1, 4]) == [1, 9]
assert find_duplicates(["b", "a", "b"]) == ["b"]""", H),
    ("can_partition", "can_partition(nums)", "returns True if the list of positive integers nums can be split into two groups (not necessarily contiguous) with equal sums, else False; an empty list can be split (True)",
     "def can_partition(nums):\n    total = sum(nums)\n    if total % 2:\n        return False\n    target = total // 2\n    reach = {0}\n    for x in nums:\n        reach |= {r + x for r in reach if r + x <= target}\n    return target in reach\n",
     """assert can_partition([1, 5, 11, 5]) is True
assert can_partition([1, 2, 3, 5]) is False
assert can_partition([]) is True
assert can_partition([2, 2]) is True
assert can_partition([1]) is False
assert can_partition([3, 3, 3, 4, 5]) is True
assert can_partition([100, 1, 1]) is False""", H),
    ("number_to_words", "number_to_words(n)", "converts an integer 0 <= n <= 999 to English words in lowercase, e.g. 0 -> \"zero\", 21 -> \"twenty-one\", 100 -> \"one hundred\", 342 -> \"three hundred forty-two\" (no word \"and\"; hyphen only between tens and ones words from 21 to 99)",
     "def number_to_words(n):\n    ones = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen']\n    tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']\n    if n < 20:\n        return ones[n]\n    if n < 100:\n        return tens[n // 10] + ('-' + ones[n % 10] if n % 10 else '')\n    rest = n % 100\n    return ones[n // 100] + ' hundred' + (' ' + number_to_words(rest) if rest else '')\n",
     """assert number_to_words(0) == "zero"
assert number_to_words(7) == "seven"
assert number_to_words(13) == "thirteen"
assert number_to_words(21) == "twenty-one"
assert number_to_words(40) == "forty"
assert number_to_words(100) == "one hundred"
assert number_to_words(342) == "three hundred forty-two"
assert number_to_words(905) == "nine hundred five"
assert number_to_words(999) == "nine hundred ninety-nine"
assert number_to_words(710) == "seven hundred ten\"""", H),
    ("topological_order", "topological_order(n, edges)", "given n nodes numbered 0..n-1 and a list of directed edges (u, v) meaning u must come before v, returns a topological order as a list; when several nodes are available, always pick the smallest node number first; returns None if the graph has a cycle",
     "import heapq\n\n\ndef topological_order(n, edges):\n    adj = [[] for _ in range(n)]\n    indeg = [0] * n\n    for u, v in edges:\n        adj[u].append(v)\n        indeg[v] += 1\n    heap = [i for i in range(n) if indeg[i] == 0]\n    heapq.heapify(heap)\n    out = []\n    while heap:\n        u = heapq.heappop(heap)\n        out.append(u)\n        for v in adj[u]:\n            indeg[v] -= 1\n            if indeg[v] == 0:\n                heapq.heappush(heap, v)\n    return out if len(out) == n else None\n",
     """assert topological_order(4, [(0, 1), (0, 2), (1, 3), (2, 3)]) == [0, 1, 2, 3]
assert topological_order(3, []) == [0, 1, 2]
assert topological_order(2, [(0, 1), (1, 0)]) is None
assert topological_order(4, [(3, 0), (2, 0)]) == [1, 2, 3, 0]
assert topological_order(0, []) == []
assert topological_order(3, [(2, 1), (1, 0)]) == [2, 1, 0]
assert topological_order(1, [(0, 0)]) is None""", H),
    ("edit_distance", "edit_distance(a, b)", "returns the Levenshtein edit distance between strings a and b: the minimum number of single-character insertions, deletions and substitutions to turn a into b",
     "def edit_distance(a, b):\n    prev = list(range(len(b) + 1))\n    for i in range(1, len(a) + 1):\n        cur = [i] + [0] * len(b)\n        for j in range(1, len(b) + 1):\n            cost = 0 if a[i - 1] == b[j - 1] else 1\n            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)\n        prev = cur\n    return prev[-1]\n",
     """assert edit_distance("kitten", "sitting") == 3
assert edit_distance("", "abc") == 3
assert edit_distance("abc", "") == 3
assert edit_distance("same", "same") == 0
assert edit_distance("horse", "ros") == 3
assert edit_distance("intention", "execution") == 5
assert edit_distance("a", "b") == 1""", H),
]
