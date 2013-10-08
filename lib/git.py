# -*- coding: utf-8 -*-

import os, re
import subprocess
import plistlib27
import datetime
import utils

def clone(repo, directory, branch=None):
    subprocess.call('git clone --recursive %(repo)s -b %(branch)s "%(directory)s"' % locals(), shell=True)

def pull(directory):
    os.chdir(directory)
    subprocess.call('git pull', shell=True)
    subprocess.call('git submodule update --init', shell=True)

def validate(repo):
    os.chdir(repo)
    if subprocess.check_output('git status --porcelain', shell=True).strip():
        raise RuntimeError('There are uncommited changes in the project repository: %(repo)s' % locals())

def releaseNotes(repo, fromVersion=None):
    os.chdir(repo)
    if fromVersion:
        fromTag = _buildTagFromVersion(repo, fromVersion)
    else:
        fromTag = _latestBuildTag(repo)
    if not fromTag:
        return

    logLines = subprocess.check_output('git log --no-merges --date-order --no-color '+
        '--format={{%%B}} %(fromTag)s..' % locals(), shell=True)

    releaseNotes = ''
    for commit in re.findall('{{([^}]+)}}', logLines, flags=re.MULTILINE):
        for line in commit.strip().splitlines():
            line = line.strip()
            if not line.startswith('-'): continue
            line = line.lstrip('-').lstrip()
            releaseNotes += '✓ %s\n' % line
    return releaseNotes.strip()

def tagBuild(repo, version):
    versionsAndTags = _versionsAndTags(repo)
    if version in versionsAndTags: return
    tag = 'Build_%(version)s' % locals()
    os.chdir(repo)
    subprocess.call('git tag %(tag)s' % locals(), shell=True)
    subprocess.call('git push', shell=True)
    subprocess.call('git push --tags', shell=True)

def tagRelease(repo, version):
    releaseVersionsAndTags = _versionsAndTags(repo, 'Release')
    if version in releaseVersionsAndTags: return
    buildVersionsAndTags = _versionsAndTags(repo)
    buildTag = buildVersionsAndTags.get(version)
    if not buildTag:
        raise RuntimeError('No build tag found for %(version)s' % locals())

    releaseTag = 'Release_%(version)s' % locals()
    os.chdir(repo)
    subprocess.call('git tag %(releaseTag)s %(buildTag)s' % locals(), shell=True)
    subprocess.call('git push --tags', shell=True)


# Private

def _versionsAndTags(repo, startswith='Build'):
    os.chdir(repo)
    gitTag = 'git tag --list %(startswith)s_*'
    tags = subprocess.check_output(gitTag % locals(), shell=True).splitlines()
    return dict((tag.split('_')[1], tag) for tag in tags)

def _latestBuildTag(repo):
    versionsAndTags = _versionsAndTags(repo)
    if len(versionsAndTags) == 0: return None
    return versionsAndTags[sorted(versionsAndTags.iterkeys())[-1]]

def _buildTagFromVersion(repo, fromVersion):
    versionsAndTags = _versionsAndTags(repo)
    laterVersions = [version for version in versionsAndTags.iterkeys() if utils.laterOrEqualVersionStringCompare(version, fromVersion)]
    if not laterVersions:
        return
    return versionsAndTags[sorted(laterVersions)[0]]
