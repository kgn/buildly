__all__ = ('projectVersion', 'buildPublish', 'hockeyappUpload', 'releaseBuild', 'releaseNotes', 'outputAppDsym')

import os
import shutil
import xcode
import hockeyapp
import git
import webbrowser
import subprocess
import time
import plistlib27

def projectVersion(branchDirectory, target):
    return plistlib27.readPlist(os.path.join(branchDirectory, target+'-Info.plist'))['CFBundleVersion']

def buildPublish(branchDirectory, target, output, displayName=None, mobileprovision=None, replacementIconsDirectory=None, identity=None):
    version = projectVersion(branchDirectory, target)
    outputDirectory = _outputDirectory(output, version)
    if os.path.isdir(outputDirectory):
        print 'A build for %(version)s already exists' % locals()
        return outputAppDsym(output, target, version)

    if displayName or mobileprovision or replacementIconsDirectory or identity:
        def modify(app):
            _replaceIcons(app, replacementIconsDirectory)
            _updateAppInfo(app, displayName, xcode.identifier(mobileprovision))
            xcode.codesign(app, mobileprovision, identity)
        app, dsym = xcode.build(branchDirectory, target)
    else:
        app, dsym = xcode.build(branchDirectory, target)

    outputApp = os.path.join(outputDirectory, os.path.basename(app))
    outputDsym = os.path.join(outputDirectory, os.path.basename(dsym))
    shutil.copytree(app, outputApp)
    shutil.copytree(dsym, outputDsym)
    shutil.rmtree(os.path.dirname(app))

    return outputApp, outputDsym

def hockeyappUpload(app, dsym, displayName, replacementIconsDirectory, mobileprovision,
        identity, hockey_token, hockeyapp_identifier, **hockeyArgs):

    appVersion = xcode.version(app)
    identifier = xcode.identifier(mobileprovision)
    if xcode.version(app) in hockeyapp.versions(hockey_token, hockeyapp_identifier):
        print '%(appVersion)s has already been uploaded to HockeyApp' % locals()
        return

    def modify(ipaApp):
        _replaceIcons(ipaApp, replacementIconsDirectory)
        _updateAppInfo(ipaApp, displayName, identifier)
        xcode.codesign(ipaApp, mobileprovision, identity)
    ipa = xcode.package(app, modify)

    tempdir = os.path.dirname(ipa)
    tempDsym = os.path.join(tempdir, os.path.basename(dsym))
    shutil.copytree(dsym, tempDsym)
    xcode.updateDsymIdentifier(tempDsym, identifier)

    hockeyArgs['dsym'] = tempDsym
    hockeyOutput = hockeyapp.upload(hockey_token, hockeyapp_identifier, ipa, **hockeyArgs)
    webbrowser.open_new_tab(hockeyOutput['config_url'])
    shutil.rmtree(tempdir)

def releaseBuild(app, dsym, hockey_token, hockeyapp_identifier, **hockeyArgs):
    ipa = xcode.package(app)

    hockeyArgs['dsym'] = dsym
    hockeyOutput = hockeyapp.upload(hockey_token, hockeyapp_identifier, ipa, **hockeyArgs)
    webbrowser.open_new_tab(hockeyOutput['config_url'])
    shutil.rmtree(os.path.dirname(ipa))

    archive = xcode.archive(app, dsym)
    subprocess.call('open "%(archive)s"' % locals(), shell=True)
    time.sleep(2) # sleep to give xcode time to launch

    shutil.rmtree(os.path.dirname(archive))

def releaseNotes(branchDirectory, hockey_token, hockeyapp_identifier):
    return git.releaseNotes(branchDirectory, hockeyapp.latestVersion(hockey_token, hockeyapp_identifier))

def outputAppDsym(outputRoot, target, version):
    directory = _outputDirectory(outputRoot, version)
    if not os.path.isdir(directory):
        raise RuntimeError('No build found for %(version)s' % locals())
    app = os.path.join(directory, target+'.app')
    return (app, app+'.dSYM')

# Private

def _outputDirectory(outputRoot, version):
    return os.path.join(outputRoot, version)

def _replaceIcons(app, iconDirectory):
    if not iconDirectory:
        return
    for icon in os.listdir(iconDirectory):
        if not icon.endswith('png'): continue
        shutil.copy2(os.path.join(icon_directory, icon), os.path.join(app, icon))

def _updateAppInfo(app, displayName, identifier):
    data = {}
    if displayName:
        data['CFBundleDisplayName'] = displayName
    if identifier:
        data['CFBundleIdentifier'] = identifier
    xcode.updateInfoPlist(app, data)
