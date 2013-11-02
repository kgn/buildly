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

def upload(ipa, teamToken, appIdentifier, dsym=None, dsymIdentifier=None, notes='', additionalNotes='',
    notesType=textile, notify=False, status=unavailable, mandatory=False, tags=None):

    status = _status(status)
    notesType = _notesType(notesType)
    if isinstance(tags, basestring): tags = tags.lower()
    else: tags = '' if not tags else ','.join(t.lower() for t in tags)
    notes = '' if not notes else notes.replace("'", '`') #TODO: properly escape '

    releaseNotesMaxLength = 5000
    if len(notes)+len(additionalNotes) > releaseNotesMaxLength:
        notes = notes[:releaseNotesMaxLength-len(additionalNotes)]
        print 'HockeyApp release notes max length is %d characters, release notes will be truncated' % releaseNotesMaxLength
    if additionalNotes: notes += '\n\n' + additionalNotes

    if notes:
        print notes

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
    if output.get('status') == 'error':
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

def _notesType(notesType):
    if isinstance(notesType, basestring) and notesType.lower() == 'markdown': notesType = 1
    if notesType == 1: return 1
    return 0

def _status(status):
    if isinstance(status, basestring) and status.lower() == 'available': status = 2
    if status == 2: return 2
    return 1
