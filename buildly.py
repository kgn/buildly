#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
import lib as buildly
import subprocess
import time

def build(branchDirectory):
    icon_directory = configData['configurations'].get('release', {}).get('icon_directory')
    replacementIconsDirectory = os.path.join(projectDirectory, icon_directory) if icon_directory else None
    mobileprovision = configData['configurations'].get('release', {}).get('mobileprovision')
    mobileprovision = os.path.join(projectDirectory, mobileprovision) if mobileprovision else None
    displayName = configData['configurations'].get('release', {}).get('display_name')
    identity = configData['configurations'].get('release', {}).get('identity')
    return buildly.buildPublish(branchDirectory, target, output, displayName, mobileprovision, replacementIconsDirectory, identity)

def distribute(app, dsym, branchDirectory, config):
    icon_directory = configData['configurations'][config].get('icon_directory')
    replacementIconsDirectory = os.path.join(projectDirectory, icon_directory) if icon_directory else None
    ipaPackageHook = configData['configurations'][config].get('ipa_package_hook')
    if ipaPackageHook: ipaPackageHook = os.path.join(projectDirectory, ipaPackageHook)
    mobileprovision = configData['configurations'][config].get('mobileprovision')
    mobileprovision = os.path.join(projectDirectory, mobileprovision) if mobileprovision else None
    hockeyapp_identifier = configData['configurations'][config]['hockeyapp_identifier']
    display_name = configData['configurations'][config].get('display_name')
    identity = configData['configurations'][config].get('identity')

    release_notes = buildly.releaseNotes(branchDirectory, hockey_token, hockeyapp_identifier)
    additional_release_notes = configData['configurations'][config].get('additional_release_notes')
    if additional_release_notes:
        release_notes += '\n\n'+additional_release_notes

    hockeyapp_additions = {'notes': release_notes}
    hockeyapp_additions['notify'] = configData['configurations'][config].get('hockeyapp_notify', False)
    if configData['configurations'][config].get('hockeyapp_status') == 'available':
        hockeyapp_additions['status'] = buildly.hockeyapp.available

    if config == 'release':
        buildly.releaseBuild(app, dsym, branchDirectory, target, output, hockey_token, hockeyapp_identifier, ipaPackageHook, **hockeyapp_additions)
    else:
        buildly.hockeyappUpload(app, dsym, display_name, replacementIconsDirectory, mobileprovision,
            identity, hockey_token, hockeyapp_identifier, ipaPackageHook, **hockeyapp_additions)
    print '%(config)s build complete!' % locals()
    if release_notes:
        print release_notes

def runConfig(config):
    postBuildHook = configData['configurations'][config].get('post_build_hook')
    if postBuildHook: postBuildHook = os.path.join(projectDirectory, postBuildHook)
    branchName = configData['configurations'][config]['git_branch']
    branchDirectory = os.path.join(branchesDirectory, branchName)
    if not os.path.isdir(branchDirectory):
        buildly.git.clone(configData['git_repo'], branchDirectory, branchName)
    else:
        buildly.git.pull(branchDirectory)

    lastVersion = None
    version = buildly.projectVersion(branchDirectory, target)
    versionFilepath = os.path.join(branchesDirectory, branchName+'.version')
    if os.path.isfile(versionFilepath):
        with open(versionFilepath, 'r') as versionFile:
            lastVersion = versionFile.read().strip()

    if version == lastVersion:
        print 'Nothing new to build: %(config)s %(version)s from %(branchName)s' % locals()
        return

    print 'Buildling: %(config)s %(version)s from %(branchName)s' % locals()

    app, dsym = build(branchDirectory)
    distribute(app, dsym, branchDirectory, config)

    with open(versionFilepath, 'w') as versionFile:
        versionFile.write(version)

    buildly.git.tagBuild(branchDirectory, version)

    if config == 'release':
        buildly.git.tagRelease(branchDirectory, version)

    if os.path.isfile(postBuildHook):
        shortVersion = buildly.projectShortVersion(branchDirectory, target)
        subprocess.call('python "%(postBuildHook)s" "%(shortVersion)s"' % locals(), shell=True)

def readConfig(configFile):
    if not configFile: raise RuntimeError('No config plist specified')
    if not os.path.isfile(configFile): raise RuntimeError('Config plist does not exist: %s' % configFile)

    projectDirectory = os.path.abspath(os.path.dirname(configFile))
    buildly.git.pull(projectDirectory)

    configData = buildly.plistlib27.readPlist(configFile)

    target = configData['target']
    hockey_token = configData['hockeyapp_token']
    output = os.path.expanduser(configData['output_directory'])

    branchesDirectory = os.path.join(projectDirectory, 'branches')
    if not os.path.isdir(branchesDirectory):
        os.makedirs(branchesDirectory)

    for config in configData['configurations']:
        runConfig(config)

while(1):
    configFile = None
    if len(sys.argv) > 0:
        configFile = sys.argv[1]
    readConfig(configFile)
    time.sleep(10*60)
