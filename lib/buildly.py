__all__ = ('projectVersion', 'projectShortVersion', 'buildPublish', 'hockeyappUpload', 'releaseBuild', 'releaseNotes', 'outputAppDsym', 'runScript')

import os
import shutil
import xcode
import hockeyapp
import git
import subprocess
import time
import plistlib27

def projectVersion(branchDirectory, target):
    return plistlib27.readPlist(os.path.join(branchDirectory, target+'-Info.plist'))['CFBundleVersion']

def projectShortVersion(branchDirectory, target):
    return plistlib27.readPlist(os.path.join(branchDirectory, target+'-Info.plist'))['CFBundleShortVersionString']

def buildPublish(branchDirectory, target, output, displayName=None, mobileprovision=None, replacementIconsDirectory=None, identity=None):
    version = projectVersion(branchDirectory, target)
    outputDirectory = _outputDirectory(output, version)
    if os.path.isdir(outputDirectory):
        print 'A build for %(version)s already exists' % locals()
        return outputAppDsym(output, target, version)

    if displayName or mobileprovision or replacementIconsDirectory or identity:
        def modify(payloadApp):
            _replaceIcons(payloadApp, replacementIconsDirectory)
            _updateAppInfo(payloadApp, displayName, xcode.identifier(mobileprovision))
            xcode.codesign(payloadApp, mobileprovision, identity)
        app, dsym = xcode.build(branchDirectory, target, modify)
    else:
        app, dsym = xcode.build(branchDirectory, target)

    outputApp = os.path.join(outputDirectory, os.path.basename(app))
    outputDsym = os.path.join(outputDirectory, os.path.basename(dsym))
    shutil.copytree(app, outputApp)
    shutil.copytree(dsym, outputDsym)
    shutil.rmtree(os.path.dirname(app))

    return outputApp, outputDsym

def hockeyappUpload(app, dsym, displayName, replacementIconsDirectory,
    mobileprovision, identity, ipaPackageHook=None, **hockeyArgs):

    appVersion = xcode.version(app)
    identifier = xcode.identifier(mobileprovision)
    if xcode.version(app) in hockeyapp.versions(hockeyArgs['teamToken'], hockeyArgs['appIdentifier']):
        print '%(appVersion)s has already been uploaded to HockeyApp' % locals()
        return

    def modify(payloadApp):
        _replaceIcons(payloadApp, replacementIconsDirectory)
        _updateAppInfo(payloadApp, displayName, identifier)
        runScript(ipaPackageHook, payloadApp)
        xcode.codesign(payloadApp, mobileprovision, identity)
    ipa = xcode.package(app, modify)

    tempdir = os.path.dirname(ipa)
    tempDsym = os.path.join(tempdir, os.path.basename(dsym))
    shutil.copytree(dsym, tempDsym)
    xcode.updateDsymIdentifier(tempDsym, identifier)

    hockeyArgs['dsym'] = tempDsym
    hockeyOutput = hockeyapp.upload(ipa, **hockeyArgs)
    shutil.rmtree(tempdir)

def releaseBuild(app, dsym, branchDirectory, target, output, ipaPackageHook, **hockeyArgs):
    def modify(payloadApp):
        runScript(ipaPackageHook, payloadApp)

    ipa = xcode.package(app, modify)
    hockeyArgs['dsym'] = dsym
    hockeyOutput = hockeyapp.upload(ipa, **hockeyArgs)
    shutil.rmtree(os.path.dirname(ipa))

    archive = xcode.archive(app, dsym, modify)
    version = projectVersion(branchDirectory, target)
    outputDirectory = _outputDirectory(output, version)
    outputArchive = os.path.join(outputDirectory, os.path.basename(archive))
    shutil.copytree(archive, outputArchive)
    shutil.rmtree(os.path.dirname(archive))

def releaseNotes(branchDirectory, **hockeyArgs):
    return git.releaseNotes(branchDirectory, hockeyapp.latestVersion(hockeyArgs['teamToken'], hockeyArgs['appIdentifier']))

def outputAppDsym(outputRoot, target, version):
    directory = _outputDirectory(outputRoot, version)
    if not os.path.isdir(directory):
        raise RuntimeError('No build found for %(version)s' % locals())
    app = os.path.join(directory, target+'.app')
    return (app, app+'.dSYM')

def runScript(script, *args):
    if not os.path.isfile(script): return
    argsString = '"'+'" "'.join(args)+'"'
    interpreter = 'sh'
    if os.path.splitext(script)[1] == '.py':
        interpreter = 'python'
    elif os.path.splitext(script)[1] == '.rb':
        interpreter = 'ruby'
    subprocess.call('%(interpreter)s "%(script)s" %(argsString)s' % locals(), shell=True)

# Private

def _outputDirectory(outputRoot, version):
    return os.path.join(outputRoot, version)

def _replaceIcons(app, iconDirectory):
    if not iconDirectory:
        return
    for icon in os.listdir(iconDirectory):
        if not icon.endswith('png'): continue
        shutil.copy2(os.path.join(iconDirectory, icon), os.path.join(app, icon))

def _updateAppInfo(app, displayName, identifier):
    data = {}
    if displayName:
        data['CFBundleDisplayName'] = displayName
    if identifier:
        data['CFBundleIdentifier'] = identifier
    xcode.updateInfoPlist(app, data)
