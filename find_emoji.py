#!/usr/bin/env python3

import collections
import os
import bisect
import pickle
import unicodedata
import sys
import re

INDEX_FILE_NAME = os.path.expanduser(
    '~/Library/Caches/emoji_names.{0}.cache'.format('.'.join(map(str, sys.version_info)))
)

VERSION = 3


def tokenize(string):
    words = re.split('[\s_-]+', string.lower())
    return words


def alfred_xml_list(results):
    res = ['<?xml version="1.0"?>', '<items>']
    for item in results:
        if 'uid' in item:
            res.append('\t<item uid="uid">'.format(item=item, uid=item['uid']))
        else:
            res.append('\t<item>'.format(item=item))
        for attr in ('subtitle', 'title', 'type', 'arg'):
            if attr in item:
                res.append('\t\t<{attr}>{value}</{attr}>'.format(attr=attr, value=item[attr]))
        res.append('\t\t<text type="copy">{copy}</text>'.format(copy=item['text']['copy']))
        res.append('\t\t<text type="largetype">{largetype}</text>'.format(largetype=item['text']['largetype']))
        for mod_key, mod_actions in item.get('mods', {}).items():
            mod_thing = '\t\t<mod key="{key}"'.format(key=mod_key)
            for action, value in mod_actions.items():
                mod_thing += ' {action}="{value}"'.format(action=action, value=value)
            mod_thing += '/>'
            res.append(mod_thing)
        res.append('\t</item>')
    res += ['</items>']
    return '\n'.join(res)


def build_index():
    index = []
    for rng in ((0x1F300, 0x1F640), (0x1F680, 0x1F700), (0x1F900, 0x1FA00), (0x2600, 0x27c0)):
        for offset in range(*rng):
            char = chr(offset)
            try:
                name = unicodedata.name(char)
            except ValueError:
                continue
            prefixes = []
            for word in tokenize(name):
                prefixes.append(word)
                for index_key in (word, ' '.join(prefixes)):
                    idx = bisect.bisect_left(index, (index_key, []))
                    if idx < len(index) and index[idx][0] == index_key:
                        index[idx][1].append((name, char))
                    else:
                        index.insert(idx, (index_key, [(name, char)]))
    return index


def output_key(kc):
    ((name, char), count) = kc
    return (count, name)


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
    prefix = []
    for word in tokenize(query):
        prefix.append(word)
        for index_key in (word, ' '.join(prefix)):
            idx = bisect.bisect_left(index, (index_key, []))
            while idx < len(index) and index[idx][0].startswith(index_key):
                for name, char in index[idx][1]:
                    matches[(name, char)] += 1
                idx += 1
    results = []
    for (name, char), count in sorted(matches.items(), key=output_key, reverse=True):
        subtitle = 'U+{0} {1}'.format(hex(ord(char))[2:].upper(), name)
        results.append({
            'title': char,
            'subtitle': subtitle,
            'type': 'default',
            'arg': char,
            'mods': {
                'shift': {
                    'arg': subtitle,
                },
            },
            'text': {
                'copy': char,
                'largetype': '{0} {1}'.format(char, name)
            }
        })
    sys.stdout.write(alfred_xml_list(results))
    sys.stdout.flush()

main()
