#!/usr/bin/env python3

import collections
import os
import bisect
import pickle
import unicodedata
import sys

INDEX_FILE_NAME = os.path.expanduser(
    '~/Library/Caches/emoji_names.{0}.cache'.format('.'.join(map(str, sys.version_info)))
)

VERSION = 2


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
        res.append('\t</item>')
    res += ['</items>']
    return '\n'.join(res)


def build_index():
    index = []
    for rng in ((0x1F300, 0x1F640), (0x1F680, 0x1F700), (0x1F900, 0x1FA00)):
        for offset in range(*rng):
            char = chr(offset)
            try:
                name = unicodedata.name(char)
            except ValueError:
                continue
            prefixes = []
            for word in name.lower().split():
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
        with open(INDEX_FILE_NAME, 'r') as f:
            version, index = pickle.load(f)
            if version < VERSION:
                raise ValueError('Too Old!')
    except Exception:
        index = build_index()
        with open(INDEX_FILE_NAME, 'wb') as f:
            pickle.dump((VERSION, index), f, protocol=pickle.HIGHEST_PROTOCOL)
    matches = collections.Counter()
    for word in query.lower().split():
        idx = bisect.bisect_left(index, (word, []))
        while idx < len(index) and index[idx][0].startswith(word):
            for name, char in index[idx][1]:
                matches[(name, char)] += 1
            idx += 1
    results = []
    for (name, char), count in sorted(matches.items(), key=output_key, reverse=True):
        results.append({
            'title': char,
            'subtitle': name,
            'type': 'default',
            'arg': char,
            'text': {
                'copy': char,
                'largetype': '{0} {1}'.format(char, name)
            }
        })
    sys.stdout.write(alfred_xml_list(results))
    sys.stdout.flush()
    # when Alfred 3 is out...
    #print(json.dumps({'items': results}))

main()