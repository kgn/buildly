import os, re
import shutil
import subprocess
import plistlib27
from datetime import datetime
from Cocoa import NSPropertyListSerialization, NSPropertyListBinaryFormat_v1_0
import tempfile
import time

def build(branchDirectory, target, appModifyCallback=None):
    os.chdir(branchDirectory)
    buildDirectory = tempfile.mkdtemp()
    xcodebuild = ("xcodebuild -target %(target)s -configuration Release "+
        "OBJROOT=%(buildDirectory)s CONFIGURATION_BUILD_DIR='%(buildDirectory)s'")
    if subprocess.call(xcodebuild % locals(), shell=True):
        raise RuntimeError('Build failed')

    app = os.path.join(buildDirectory, target+'.app')
    dsym = app+'.dSYM'
    if appModifyCallback:
        appModifyCallback(app)
        # make sure the identifier in the dsym matches the modifed app
        identifier = plistlib27.readPlist(os.path.join(app, 'Info.plist'))['CFBundleIdentifier']
        updateDsymIdentifier(dsym, identifier)

    # even through all the build items go into `buildDirectory`
    # an empty build directory is still created in `branchDirectory`
    projectBuild = os.path.join(branchDirectory, 'build')
    if os.path.isdir(projectBuild): shutil.rmtree(projectBuild)

    return (app, dsym)

def package(app, appModifyCallback=None):
    appBase = os.path.basename(app)
    appName = os.path.splitext(appBase)[0]
    outputDirectory = tempfile.mkdtemp()
    ipa = os.path.join(outputDirectory, appName+'.ipa')
    payload = os.path.join(outputDirectory, 'Payload')
    os.makedirs(payload)

    payloadApp = os.path.join(payload, appBase)
    shutil.copytree(app, payloadApp)
    if appModifyCallback:
        appModifyCallback(payloadApp)

    os.chdir(outputDirectory) # cd for zip
    payloadBasename = os.path.basename(payload)
    subprocess.call("zip -r -q '%(ipa)s' '%(payloadBasename)s'" % locals(), shell=True)
    shutil.rmtree(payload)
    return ipa

def archive(app, dsym, appModifyCallback=None):
    appBase = os.path.basename(app)
    appName = os.path.splitext(appBase)[0]
    date = datetime.today().strftime('%m-%d-%y %H.%M %p')
    archive = os.path.join(tempfile.mkdtemp(),
        '%(appName)s %(date)s.xcarchive' % locals())

    applications = os.path.join(archive, 'Products', 'Applications')
    archiveApp = os.path.join(applications, appBase)
    shutil.copytree(app, archiveApp)
    if appModifyCallback:
        appModifyCallback(archiveApp)

    info = plistlib27.readPlist(os.path.join(app, 'Info.plist'))
    dsyms = os.path.join(archive, 'dSYMs')
    dsymArchive = os.path.join(dsyms, os.path.basename(dsym))
    shutil.copytree(dsym, dsymArchive)
    updateDsymIdentifier(dsymArchive, info['CFBundleIdentifier'])
    icons = (os.path.join('Applications', appBase, item) for item in os.listdir(app)
        if item.startswith('Icon') and item.endswith('png'))
    plist = {
        'AppStoreFileSize': _directorySize(archiveApp),
        'ApplicationProperties': {
            'ApplicationPath': os.path.join('Applications', appBase),
            'CFBundleIdentifier': info['CFBundleIdentifier'],
            'CFBundleShortVersionString': info['CFBundleShortVersionString'],
            'CFBundleVersion': info['CFBundleVersion'],
            'SigningIdentity': _authority(archiveApp) or '',
            'IconPaths': list(icons)
        },
        'ArchiveVersion': 2,
        'CreationDate': datetime.today().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'Name': appName,
        'SchemeName': appName
    }
    plistlib27.writePlist(plist, os.path.join(archive, 'Info.plist'))
    return archive

def codesign(app, mobileprovision=None, identity=None):
    identity = identity or _authority(app)
    if not identity:
        raise RuntimeError('No valid code signing identity')

    codeSignature = os.path.join(app, '_CodeSignature')
    if os.path.isdir(codeSignature): shutil.rmtree(codeSignature)
    if mobileprovision:
        shutil.copy2(mobileprovision, os.path.join(app, 'embedded.mobileprovision'))

    entitlementsFile = None
    handle, entitlementsFile = tempfile.mkstemp()
    entitlements = _entitlements(mobileprovision)
    # set the keychain access group to the identifier,
    # there might be some corner cases where this is not correct...
    entitlements['keychain-access-groups'] = [entitlements['application-identifier']]
    plistlib27.writePlist(entitlements, entitlementsFile)

    # Needed for Mountain Lion: http://stackoverflow.com/a/11723891/239380
    os.putenv('CODESIGN_ALLOCATE', '%s/usr/bin/codesign_allocate' % XcodePath())
    codesign = 'codesign --force --sign "%(identity)s" --entitlements "%(entitlementsFile)s" "%(app)s"'
    if subprocess.call(codesign % locals(), shell=True):
        if os.path.isfile(entitlementsFile): os.remove(entitlementsFile)
        raise RuntimeError('Code signing failed')
    if os.path.isfile(entitlementsFile): os.remove(entitlementsFile)

def updateInfoPlist(app, updates):
    path = os.path.join(app, 'Info.plist')
    info = plistlib27.readPlist(path)
    info.update(updates)
    plist = NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
        info, NSPropertyListBinaryFormat_v1_0, 0, None)
    plist[0].writeToFile_atomically_(path, True)

def updateDsymIdentifier(dsym, identifier):
    path = os.path.join(dsym, 'Contents', 'Info.plist')
    info = plistlib27.readPlist(path)
    info['CFBundleIdentifier'] = 'com.apple.xcode.dsym.'+identifier
    plistlib27.writePlist(info, path)

def version(app):
    return plistlib27.readPlist(os.path.join(app, 'Info.plist'))['CFBundleVersion']

def identifier(mobileprovision):
    entitlements = _entitlements(mobileprovision)
    entitlementsIdentifier = entitlements['application-identifier']
    return '.'.join(entitlementsIdentifier.split('.')[1:])

def XcodePath():
    return subprocess.check_output('xcode-select --print-path', shell=True).strip()

# Private

def _authority(app):
    requirements = subprocess.check_output('codesign --display -r- "%(app)s"' % locals(), shell=True)
    search = re.search('= "([^"]+)"', requirements)
    if search: return search.group(1)

def _createDirectory(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)

def _buildDirectory(rootDirectory):
    buildDirectory = os.path.join(rootDirectory, 'build')
    _createDirectory(buildDirectory)
    return buildDirectory

def _directorySize(directory):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size

def _entitlements(mobileprovision):
    root = os.path.dirname(os.path.realpath(__file__))
    mobileprovisionPlist = os.path.join(root, 'mobileprovisionPlist', 'mobileprovisionPlist')
    plist = subprocess.check_output('"%(mobileprovisionPlist)s" "%(mobileprovision)s"' % locals(), shell=True)
    return plistlib27.readPlistFromString(plist)['Entitlements']
