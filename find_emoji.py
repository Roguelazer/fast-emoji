#!/usr/bin/env python3

import collections
import os
import json
import bisect
import pickle
import sys
import re

INDEX_FILE_NAME = os.path.expanduser(
    '~/Library/Caches/emoji_names.{0}.cache'.format('.'.join(map(str, sys.version_info)))
)
IGNORED_WORDS = ('of', 'in', 'to', 'a', 'with', 'for')

VERSION = 6

if sys.version_info > (3, 0):
    unichr = chr


def ngrams(word_list, n):
    if n > len(word_list):
        return
    args = []
    for i in range(n):
        args.append(word_list[i:])
    for tpl in zip(*args):
        yield ' '.join(tpl)


def tokenize(string):
    # tokenize into words
    words = re.split('[\s_-]+', string.lower())
    # delete filler words
    for word in IGNORED_WORDS:
        if word in words:
            words.remove(word)
    return words


def tokenize_and_ngram(string, max_ngram=3):
    words = tokenize(string)
    # break into ngrams
    for i in range(max_ngram):
        for ngram in ngrams(words, i):
            yield ngram


def overlap(string1, string2):
    bag1 = sorted(tokenize(string1))
    bag2 = sorted(tokenize(string2))
    i = 0
    overlap = []
    for w1 in bag1:
        while i < len(bag2) and bag2[i] < w1:
            i += 1
        if i == len(bag2):
            break
        if bag2[i] == w1:
            overlap.append(w1)
            i += 1
    return len(overlap) / float(max(len(bag1), len(bag2)))


class Range(object):
    def __init__(self, min_c, max_c):
        self.min = min_c
        self.max = max_c

    def __contains__(self, other):
        return other >= self.min and other <= self.max


class Or(object):
    def __init__(self, *clauses):
        self.clauses = clauses

    def __contains__(self, obj):
        return any(obj in clause for clause in self.clauses)


def build_index():
    index = []
    ranges = Or(
        Range(0x1F300, 0x1F640),
        Range(0x1F680, 0x1F700),
        Range(0x1F900, 0x1FA00),
        Range(0x2600, 0x27c0)
    )
    with open('UnicodeData.txt', 'r') as f:
        for line in f:
            codepoint, name = line.split(';', 3)[:2]
            codepoint = int(codepoint, 16)
            if codepoint not in ranges:
                continue
            char = unichr(codepoint)
            for index_key in tokenize_and_ngram(name, 3):
                idx = bisect.bisect_left(index, (index_key, []))
                if idx < len(index) and index[idx][0] == index_key:
                    inner_idx = bisect.bisect_left(index[idx][1], (name, char))
                    index[idx][1].insert(inner_idx, (name, char))
                else:
                    index.insert(idx, (index_key, [(name, char)]))
    return index


def output_key(kc):
    ((name, char), count) = kc
    return (-count, name)


def main():
    query = ' '.join(sys.argv[1:])
    try:
        with open(INDEX_FILE_NAME, 'rb') as f:
            version, index = pickle.load(f)
            if version < VERSION:
                raise ValueError('Too Old!')
    except Exception:
        index = build_index()
        with open(INDEX_FILE_NAME, 'wb') as f:
            pickle.dump((VERSION, index), f, protocol=pickle.HIGHEST_PROTOCOL)
    matches = collections.Counter()
    # I don't really want to use TF-IDF here, these really are not documents
    for index_key in tokenize_and_ngram(query, 3):
        idx = bisect.bisect_left(index, (index_key, []))
        while idx < len(index) and index[idx][0].startswith(index_key):
            for name, char in index[idx][1]:
                score = overlap(name, index_key)
                matches[(name, char)] += score
            idx += 1
    results = []
    for (name, char), count in sorted(matches.items(), key=output_key):
        subtitle = 'U+{0} {1}'.format(hex(ord(char))[2:].upper(), name)
        results.append({
            'title': char,
            'subtitle': subtitle,
            'autocomplete': name,
            'type': 'default',
            'arg': char,
            '_score': count,
            'mods': {
                'shift': {
                    'arg': subtitle,
                },
                'cmd': {
                    'arg': subtitle,
                },
            },
            'text': {
                'copy': char,
                'largetype': '{0} {1}'.format(char, name)
            }
        })
    print(json.dumps({'items': results}))

main()
