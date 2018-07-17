import os
import argparse

# define CLI args
argparser = argparse.ArgumentParser(description='Takes a word as param, calculates the number of times this word was introducted in, or removed from the repo by every commiter.')
argparser.add_argument('word', metavar='W', type=str, help='The word to search')
argparser.add_argument('-i', '--case-insensitive', dest='ignore_case', action='store_true', default=False, help='Flag that the search should be case-insensitive')

args = argparser.parse_args()



""" commit generator

Takes a raw string using git log format, and for each commit, yields a dictionary
whose structure is: {'author': $commit_author, 'diffs': commit_diffs}
"""
def getCommits(raw):
    curAuthor = ''
    curSha = ''

    for line in raw:
        if line[:7] == 'commit ':
            curSha = line[7:]
        elif line[:8] == 'Author: ':
            curAuthor = line[8:]

        if curSha and curAuthor:
            commitContent = 4 # git diff curSĥa^ curSha
            yield {'author': curAuthor, 'diffs': commitContent}



""" get the raw logs from git for a list of words
"""
def getRawLogsForRegex(regex):
    os.system('echo "" > /tmp/gitWordScorerResults')
    for word in words:
        os.system('git log -S "' + regex + '" --pickaxe-regex --source --all >> /tmp/gitwordscorerRawLog')

    rawlog = open('/tmp/gitwordscorerRawLog', 'r')

    content = rawlog.read()
    rawlog.close()
    os.system('rm /tmp/gitwordscorerRawLog')

    return content



if __name__ == '__main__':
    scores = {}

    raw = getRawLogsForRegex(word + )

    for commit in getCommits(raw):
        git diff COMMIT^ COMMIT


    print('on a ' + str(len(raw)) + ' lignes de résultat')