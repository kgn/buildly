import os
import json
import subprocess
import utils

# notes_type
textile = 0
markdown = 1

# status
unavailable = 1
available = 2

def upload(teamToken, appIdentifier, ipa, dsym=None, dsymIdentifier=None, notes='',
    notesType=textile, notify=False, status=unavailable, mandatory=False, tags=None):

    tags = '' if not tags else ','.join(tags)
    #TODO: properly escape '
    notes = '' if not notes else notes.replace("'", '`')
    releaseNotesMaxLength = 5000
    if len(notes) > releaseNotesMaxLength:
        notes = notes[:releaseNotesMaxLength]
        print 'HockeyApp release notes max length is %d characters, release notes will be truncated' % releaseNotesMaxLength

    dsymCurl = ''
    if dsym:
        dsymZip = dsym+'.zip'
        dsymRoot, dsymFile = os.path.split(dsym)
        os.chdir(dsymRoot) # cd for zip
        subprocess.call('zip -r -q "%(dsymZip)s" "%(dsymFile)s"' % locals(), shell=True)
        dsymCurl = '-F dsym=@"%(dsymZip)s"' % locals()

    curl = ('curl -F status=%(status)d -F notify=%(notify)d '+
        "-F notes='%(notes)s' -F mandatory=%(mandatory)d "+
        '-F notes_type=%(notesType)d -F ipa=@"%(ipa)s" '+
        '%(dsymCurl)s -F tags="%(tags)s" -H X-HockeyAppToken:%(teamToken)s '+
        'https://rink.hockeyapp.net/api/2/apps/%(appIdentifier)s/app_versions')

    output = json.loads(subprocess.check_output(curl % locals(), shell=True))
    if dsymCurl: os.remove(dsymZip)

    if 'errors' in output:
        raise RuntimeError('HockeyApp errors: %r' % output)

    return output

def versions(teamToken, appIdentifier):
    curl = ('curl -H "X-HockeyAppToken:%(teamToken)s" '+
        'https://rink.hockeyapp.net/api/2/apps/%(appIdentifier)s/app_versions')
    responce = json.loads(subprocess.check_output(curl % locals(), shell=True))
    if 'app_versions' not in responce:
        return set()
    return set(version['version'] for version in responce['app_versions'])

def latestVersion(teamToken, appIdentifier):
    lastVersion = ''
    for version in versions(teamToken, appIdentifier):
        if utils.laterOrEqualVersionStringCompare(version, lastVersion):
            lastVersion = version
    return lastVersion
