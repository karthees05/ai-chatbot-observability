"""Illustrative configured Python criterion: a response must stay within a word limit."""


# Purpose: score a stated response-length constraint without executing dataset code.
def grade(case):
    limit = int(case.get('max_response_words', 100))
    if limit < 1:
        raise ValueError('max_response_words must be positive')
    count = len(case['response'].split())
    return {'score': float(0 < count <= limit), 'reason': f'{count} words; limit {limit}'}
